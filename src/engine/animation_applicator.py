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
        
        # Set flag to indicate successful animation application
        state["animation_applied"] = True
        
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
                        // Find all paths that represent connections/arrows across different diagram types
                        // Flowcharts: .edgePath path, .flowchart-link
                        // Sequence diagrams: .messageLine0, .messageLine1, line[class*="messageLine"]
                        // Class diagrams: .relation line, path[class*="relation"]
                        // State diagrams: .transition path, path.transition, g.transition path, path[id*="transition"]
                        // ER diagrams: .er.relationshipLine path
                        const edgePaths = document.querySelectorAll(`
                            .edgePath path, 
                            .flowchart-link,
                            line[class*="messageLine"],
                            .messageLine0,
                            .messageLine1,
                            .relation line,
                            path[class*="relation"],
                            .transition path,
                            path.transition,
                            g.transition path,
                            path[id*="transition"],
                            path[id*="edge"],
                            .er.relationshipLine path
                        `);
                        
                        let animatedCount = 0;
                        
                        edgePaths.forEach((path, index) => {
                            // Get the total length of the path/line
                            let pathLength;
                            try {
                                pathLength = path.getTotalLength();
                            } catch (e) {
                                // For <line> elements, calculate length manually
                                if (path.tagName === 'line') {
                                    const x1 = parseFloat(path.getAttribute('x1') || 0);
                                    const y1 = parseFloat(path.getAttribute('y1') || 0);
                                    const x2 = parseFloat(path.getAttribute('x2') || 0);
                                    const y2 = parseFloat(path.getAttribute('y2') || 0);
                                    pathLength = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
                                } else {
                                    return; // Skip if we can't get length
                                }
                            }
                            
                            if (pathLength <= 0) return;
                            
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
                            
                            animatedCount++;
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
                            .node rect, .node circle, .node polygon,
                            .actor rect, .actor circle,
                            .classGroup rect {
                                animation: nodePulse ${duration * 1.5}s ease-in-out infinite;
                                transform-origin: center;
                            }
                        `;
                        document.head.appendChild(pulseStyle);
                        
                        return { 
                            success: true, 
                            pathsAnimated: animatedCount,
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
