"""
Animation Applicator for Mermaid.js SVG
Injects path-based animations into rendered Mermaid diagrams with seamless looping
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
    Apply path-based animations to rendered Mermaid SVG.
    
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
        # Get duration from state for seamless looping
        duration = state.get("duration", 5.0)
        animated_html = await applicator.apply_animations(render_html, duration)
        
        # Store in artifacts
        state["artifacts"]["animated_html"] = animated_html
        
        logger.info("Animation application completed", metadata={
            "html_size": len(animated_html),
            "animation_duration": duration
        })
        
        return state
        
    except Exception as e:
        logger.error(state, e, metadata={
            "component": "animation_applicator"
        })
        raise


class AnimationApplicator:
    """Applies path-based animations to Mermaid SVG diagrams"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("animation_applicator")
    
    async def apply_animations(self, render_html: str, duration: float = 5.0) -> str:
        """
        Inject path-based animations into rendered HTML with seamless looping.
        
        Args:
            render_html: HTML with rendered Mermaid SVG
            duration: Animation duration in seconds (matches video duration for seamless loop)
            
        Returns:
            HTML with animations injected
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
                
                # Inject JavaScript-based path animation for flowing arrows
                self.logger.info("Injecting path-based animations", metadata={
                    "duration_seconds": duration
                })
                
                result = await page.evaluate("""
                    (duration) => {
                        // Find all edge paths
                        const edgePaths = document.querySelectorAll('.edgePath path, .flowchart-link');
                        
                        edgePaths.forEach((path, index) => {
                            // Get the total length of the path
                            const pathLength = path.getTotalLength();
                            
                            // Set up stroke-dasharray: 15% of path length for dash, 5% for gap
                            const dashLength = pathLength * 0.15;
                            const gapLength = pathLength * 0.05;
                            path.style.strokeDasharray = `${dashLength} ${gapLength}`;
                            
                            // Start with offset at full path length (invisible)
                            path.style.strokeDashoffset = pathLength;
                            
                            // Create unique animation for this path
                            const animationName = `flow-${index}`;
                            const styleSheet = document.createElement('style');
                            styleSheet.textContent = `
                                @keyframes ${animationName} {
                                    to {
                                        stroke-dashoffset: 0;
                                    }
                                }
                            `;
                            document.head.appendChild(styleSheet);
                            
                            // Apply animation with duration matching video length for seamless loop
                            path.style.animation = `${animationName} ${duration}s linear infinite`;
                        });
                        
                        // Add subtle pulse to nodes with matching duration
                        const pulseStyle = document.createElement('style');
                        pulseStyle.textContent = `
                            @keyframes nodePulse {
                                0%, 100% {
                                    opacity: 1;
                                }
                                50% {
                                    opacity: 0.95;
                                }
                            }
                            .node rect, .node circle, .node polygon {
                                animation: nodePulse ${duration * 1.5}s ease-in-out infinite;
                                transform-origin: center;
                            }
                        `;
                        document.head.appendChild(pulseStyle);
                        
                        return { 
                            success: true, 
                            pathsAnimated: edgePaths.length,
                            animationDuration: duration
                        };
                    }
                """, duration)
                
                self.logger.info("Path animations injected successfully", metadata={
                    "paths_animated": result.get("pathsAnimated", 0),
                    "animation_duration": result.get("animationDuration", duration)
                })
                
                # Get the updated HTML
                animated_html = await page.content()
                
                return animated_html
                
            finally:
                await browser.close()
