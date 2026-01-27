"""
Animation applicator using JavaScript injection to apply flow animations.

This module injects JavaScript into the Draw.io page to apply the "Flow Animation"
style to diagram edges, creating the animated effect.

CRITICAL FEATURES:
- JavaScript injection only (NO UI automation)
- Access to internal mxGraph API
- Style application to edges
- Graph refresh for immediate effect
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from playwright.async_api import async_playwright, Browser, Page

from ..core.config import get_config
from ..core.exceptions import AnimationError, RenderingError
from ..core.state import GraphState
from ..utils.logger import get_logger

# Draw.io embed mode URL (MANDATORY)
DRAWIO_EMBED_URL = "https://embed.diagrams.net/?ui=min&spin=1&proto=json&configure=1"

# Fixed viewport for deterministic rendering
DEFAULT_VIEWPORT = {"width": 1200, "height": 1200}

# Selectors
DIAGRAM_CONTAINER_SELECTOR = ".geDiagramContainer"

logger = get_logger("animation_applicator")


class AnimationApplicator:
    """
    Animation applicator using JavaScript injection.
    
    This applicator:
    1. Accesses the internal mxGraph instance
    2. Applies flow animation styles to edges
    3. Refreshes the graph to show animations
    """
    
    def __init__(self):
        """Initialize the animation applicator."""
        self.config = get_config()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.launch()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def launch(self) -> None:
        """
        Launch the headless browser.
        
        Raises:
            AnimationError: If browser launch fails
        """
        try:
            playwright = await async_playwright().start()
            
            # Launch Chromium
            launch_options = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                ],
            }
            
            # Use custom Chromium path if specified
            if self.config.chromium_executable_path:
                launch_options["executable_path"] = str(self.config.chromium_executable_path)
            
            self.browser = await playwright.chromium.launch(**launch_options)
            
            # Create page with fixed viewport
            self.page = await self.browser.new_page(viewport=DEFAULT_VIEWPORT)
            self.page.set_default_timeout(self.config.browser_timeout_ms)
            
        except Exception as e:
            raise AnimationError(f"Failed to launch browser: {e}")
    
    async def close(self) -> None:
        """Close the browser."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
    
    async def apply_flow_animation(
        self,
        mermaid_code: str,
        animation_manifest: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Apply flow animation to diagram edges.
        
        This method:
        1. Navigates to Draw.io and imports the diagram
        2. Accesses the internal mxGraph instance
        3. Applies flowAnimation=1 style to all edges
        4. Refreshes the graph
        
        Args:
            mermaid_code: Mermaid diagram code
            animation_manifest: Optional animation configuration
            
        Raises:
            AnimationError: If animation application fails
            RenderingError: If diagram rendering fails
        """
        if not self.page:
            raise AnimationError("Browser not launched. Call launch() first.")
        
        try:
            # Get path to local mermaid renderer HTML
            from pathlib import Path
            renderer_path = Path(__file__).parent / "mermaid_renderer.html"
            renderer_url = f"file:///{renderer_path.as_posix()}"
            
            # Navigate to local HTML renderer
            await self.page.goto(renderer_url, wait_until="networkidle")
            
            # Wait for mermaid.js to be ready
            await self.page.wait_for_function(
                "typeof window.mermaidReady !== 'undefined' && window.mermaidReady === true",
                timeout=self.config.browser_timeout_ms,
            )
            
            # Render the Mermaid diagram
            render_result = await self.page.evaluate(
                """
                async (mermaidCode) => {
                    return await window.renderMermaid(mermaidCode);
                }
                """,
                mermaid_code,
            )
            
            if not render_result.get("success"):
                error_msg = render_result.get("error", "Unknown error")
                raise RenderingError(f"Failed to render diagram: {error_msg}")
            
            # Wait for SVG to appear
            await self.page.wait_for_selector(
                "svg",
                timeout=self.config.browser_timeout_ms,
            )
            
            # Apply CSS animation to edges (paths in SVG)
            animation_result = await self.page.evaluate(
                """
                () => {
                    try {
                        // Add CSS animation to all paths (edges) in the SVG
                        const style = document.createElement('style');
                        style.textContent = `
                            @keyframes flowAnimation {
                                0% { stroke-dashoffset: var(--path-length); }
                                100% { stroke-dashoffset: 0; }
                            }
                            svg path.flowable {
                                stroke-dasharray: var(--path-length);
                                animation: flowAnimation 2s linear infinite;
                            }
                        `;
                        document.head.appendChild(style);
                        
                        // Add flowable class to all paths (edges) and set their length
                        const paths = document.querySelectorAll('svg path');
                        let edgeCount = 0;
                        paths.forEach(path => {
                            // Only animate paths that look like edges (have stroke)
                            const stroke = window.getComputedStyle(path).stroke;
                            if (stroke && stroke !== 'none' && stroke !== 'rgb(0, 0, 0)') {
                                // Calculate path length for smooth animation
                                const pathLength = path.getTotalLength();
                                path.style.setProperty('--path-length', pathLength);
                                path.style.strokeDasharray = pathLength;
                                path.style.strokeDashoffset = pathLength;
                                path.classList.add('flowable');
                                edgeCount++;
                            }
                        });
                        
                        return { success: true, edgeCount: edgeCount };
                    } catch (error) {
                        return { success: false, error: error.message };
                    }
                }
                """
            )
            
            if not animation_result.get("success"):
                error_msg = animation_result.get("error", "Unknown error")
                raise AnimationError(f"Failed to apply animation: {error_msg}")
            
            # Wait for animation to settle
            await asyncio.sleep(0.5)
            
        except (AnimationError, RenderingError):
            raise
        except Exception as e:
            raise AnimationError(f"Unexpected error during animation application: {e}")


async def _apply_animation_async(state: GraphState) -> GraphState:
    """
    Async implementation of animation application node.
    
    Args:
        state: Current graph state
        
    Returns:
        GraphState: Updated state with animation_applied flag
    """
    logger.start(state, {
        "diagram_rendered": state.get("diagram_rendered"),
        "has_manifest": state.get("animation_manifest") is not None,
    })
    
    try:
        # Validate prerequisites
        if not state.get("diagram_rendered"):
            raise AnimationError("Diagram must be rendered before applying animation")
        
        mermaid_code = state.get("mermaid_code")
        if not mermaid_code:
            raise AnimationError("No Mermaid code in state")
        
        animation_manifest = state.get("animation_manifest")
        
        # Apply animation
        async with AnimationApplicator() as applicator:
            await applicator.apply_flow_animation(mermaid_code, animation_manifest)
        
        # Update state
        state["animation_applied"] = True
        
        logger.end(state, {"status": "success"})
        
        return state
        
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"Animation application failed: {str(e)}")
        state["animation_applied"] = False
        raise


def animation_applicator(state: GraphState) -> GraphState:
    """
    Synchronous wrapper for LangGraph compatibility.
    
    LangGraph requires synchronous node functions, so this wraps
    the async implementation in asyncio.run().
    """
    return asyncio.run(_apply_animation_async(state))
