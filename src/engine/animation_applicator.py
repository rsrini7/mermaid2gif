"""
Animation Applicator for Mermaid.js SVG
Injects CSS animations into rendered Mermaid diagrams
"""

from playwright.async_api import async_playwright
from ..core.config import get_config
from ..utils.logger import get_logger
from typing import Dict, Any
import asyncio
import nest_asyncio

# Allow nested event loops for LangGraph compatibility
nest_asyncio.apply()

logger = get_logger("animation_applicator")


def apply_animation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper for async animation application.
    Required for LangGraph compatibility.
    """
    return asyncio.run(_apply_animation_async(state))


async def _apply_animation_async(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply CSS animations to rendered Mermaid SVG.
    
    Args:
        state: Graph state containing render_html artifact
        
    Returns:
        Updated state with animated_html artifact
    """
    render_html = state.get("artifacts", {}).get("render_html")
    
    if not render_html:
        raise ValueError("No render_html found in state artifacts")
    
    logger.info("Starting animation application")
    
    applicator = AnimationApplicator()
    try:
        animated_html = await applicator.apply_animations(render_html)
        
        # Store in artifacts
        state["artifacts"]["animated_html"] = animated_html
        
        logger.info("Animation application completed", metadata={
            "html_size": len(animated_html)
        })
        
        return state
        
    except Exception as e:
        logger.error(state, e, metadata={
            "component": "animation_applicator"
        })
        raise


class AnimationApplicator:
    """Applies CSS animations to Mermaid SVG diagrams"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("animation_applicator")
    
    async def apply_animations(self, render_html: str) -> str:
        """
        Inject CSS animations into rendered HTML.
        
        Args:
            render_html: HTML with rendered Mermaid SVG
            
        Returns:
            HTML with CSS animations injected
        """
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            try:
                page = await browser.new_page()
                
                self.logger.info("Loading rendered HTML")
                await page.set_content(render_html)
                
                # Inject CSS animation styles
                self.logger.info("Injecting CSS animations")
                
                animation_css = """
                <style id="mermaid-animations">
                    /* Animate edge paths with flowing dashed lines */
                    .edgePath .path,
                    .flowchart-link {
                        stroke-dasharray: 8 4;
                        animation: flow 3s linear infinite;
                    }
                    
                    /* Keyframe animation for flowing effect */
                    @keyframes flow {
                        0% { stroke-dashoffset: 0;
                        }
                        100% { stroke-dashoffset: -12;
                        }
                    }
                    
                    /* Optional: Pulse animation for nodes */
                    .node rect,
                    .node circle,
                    .node polygon {
                        animation: pulse 4s ease-in-out infinite;
                    }
                    
                    @keyframes pulse {
                        0%, 100% {
                            opacity: 1; transform: scale(1);
                        }
                        50% {
                            opacity: 0.95; transform: scale(1.02);
                        }
                    }
                </style>
                """
                
                await page.evaluate(f"""
                    (css) => {{
                        // Find the SVG element
                        const svg = document.querySelector('svg');
                        if (!svg) {{
                            throw new Error('No SVG found in document');
                        }}
                        
                        // Create style element
                        const styleElement = document.createElement('style');
                        styleElement.id = 'mermaid-animations';
                        styleElement.textContent = css;
                        
                        // Insert into SVG or head
                        if (svg.querySelector('defs')) {{
                            svg.querySelector('defs').appendChild(styleElement);
                        }} else {{
                            const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
                            defs.appendChild(styleElement);
                            svg.insertBefore(defs, svg.firstChild);
                        }}
                        
                        return {{ success: true }};
                    }}
                """, animation_css)
                
                self.logger.info("CSS animations injected successfully")
                
                # Get the updated HTML
                animated_html = await page.content()
                
                return animated_html
                
            finally:
                await browser.close()

