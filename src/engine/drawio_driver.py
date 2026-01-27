"""
Draw.io renderer REFACTORED to use local Mermaid.js renderer.

This module originally drove Draw.io's embed mode but has been refactored
to use a local HTML file with mermaid.js for better reliability and speed.
The class name `DrawIODriver` and node name `drawio_renderer` are retained
for backward compatibility, but the implementation is now 100% local.
"""

import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from ..core.config import get_config
from ..core.exceptions import DrawIOImportError, DrawIOTimeoutError, RenderingError
from ..core.state import GraphState
from ..utils.logger import get_logger

# Draw.io offline mode URL - better for programmatic access
# Using local=1 to enable offline mode which has more reliable API
DRAWIO_EMBED_URL = "https://embed.diagrams.net/?embed=1&ui=min&spin=1&proto=json&local=1"

# Fixed viewport for deterministic rendering
DEFAULT_VIEWPORT = {"width": 1200, "height": 12000}

# Selectors (for validation only, NOT for clicking)
DIAGRAM_CONTAINER_SELECTOR = ".geDiagramContainer"

logger = get_logger("drawio_driver")


class DrawIODriver:
    """
    Headless Draw.io driver using JavaScript injection.
    
    This driver renders Mermaid diagrams by:
    1. Launching Chromium in headless mode
    2. Navigating to Draw.io embed mode
    3. Injecting JavaScript to call App.importData()
    4. Validating the rendered diagram
    """
    
    def __init__(self):
        """Initialize the Draw.io driver."""
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
            DrawIOTimeoutError: If browser launch times out
        """
        try:
            playwright = await async_playwright().start()
            
            # Launch Chromium with fixed viewport
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
            
            # Set timeout
            self.page.set_default_timeout(self.config.browser_timeout_ms)
            
        except Exception as e:
            raise DrawIOTimeoutError(f"Failed to launch browser: {e}")
    
    async def close(self) -> None:
        """Close the browser."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
    
    async def render_mermaid(self, mermaid_code: str) -> None:
        """
        Render Mermaid diagram using JavaScript injection.
        
        This method:
        1. Navigates to Draw.io embed mode
        2. Injects JavaScript to call App.importData()
        3. Validates the rendered diagram
        
        Args:
            mermaid_code: Mermaid diagram code to render
            
        Raises:
            DrawIOImportError: If diagram import fails
            DrawIOTimeoutError: If rendering times out
            RenderingError: If diagram validation fails
        """
        if not self.page:
            raise RenderingError("Browser not launched. Call launch() first.")
        
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
            
            # Check render result
            if not render_result.get("success"):
                error_msg = render_result.get("error", "Unknown error")
                raise DrawIOImportError(f"Failed to render Mermaid diagram: {error_msg}")
            
            # Wait for SVG to appear
            await self.page.wait_for_selector(
                "svg",
                timeout=self.config.browser_timeout_ms,
            )
            
            # Validate diagram bounds
            await self._validate_diagram()
            
        except PlaywrightTimeoutError as e:
            raise DrawIOTimeoutError(f"Rendering timed out: {e}")
        except (DrawIOImportError, RenderingError):
            raise
        except Exception as e:
            raise DrawIOImportError(f"Unexpected error during rendering: {e}")
    
    async def _validate_diagram(self) -> None:
        """
        Validate that the diagram was rendered correctly.
        
        Checks that the diagram container has valid dimensions (width/height >= 10px).
        
        Raises:
            RenderingError: If diagram validation fails
        """
        try:
            # Query SVG diagram bounds using JavaScript
            bounds = await self.page.evaluate(
                """
                () => {
                    const svg = document.querySelector('svg');
                    if (!svg) {
                        return { width: 0, height: 0, error: 'SVG not found' };
                    }
                    const rect = svg.getBoundingClientRect();
                    return { width: rect.width, height: rect.height };
                }
                """
            )
            
            # Check for errors
            if "error" in bounds:
                raise RenderingError(f"Diagram validation failed: {bounds['error']}")
            
            # Validate dimensions
            width = bounds.get("width", 0)
            height = bounds.get("height", 0)
            
            if width < 10 or height < 10:
                raise RenderingError(
                    f"Diagram has invalid dimensions: {width}x{height}px (minimum 10x10px)"
                )
            
        except RenderingError:
            raise
        except Exception as e:
            raise RenderingError(f"Failed to validate diagram: {e}")
    
    async def capture_screenshot(self, output_path: Path) -> None:
        """
        Capture a screenshot of the rendered diagram.
        
        Args:
            output_path: Path to save the screenshot
            
        Raises:
            RenderingError: If screenshot capture fails
        """
        if not self.page:
            raise RenderingError("Browser not launched. Call launch() first.")
        
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Capture screenshot of the diagram container
            await self.page.locator(DIAGRAM_CONTAINER_SELECTOR).screenshot(
                path=str(output_path)
            )
            
        except Exception as e:
            raise RenderingError(f"Failed to capture screenshot: {e}")




async def _render_diagram_node_async(state: GraphState) -> GraphState:
    """
    LangGraph node: Render Mermaid diagram using Draw.io.
    
    This node:
    1. Launches headless browser
    2. Renders Mermaid diagram via JavaScript injection
    3. Validates the rendering
    4. Updates state with diagram_rendered=True
    
    Args:
        state: Current graph state
        
    Returns:
        GraphState: Updated state with diagram_rendered flag
    """
    logger.start(state, {"mermaid_length": len(state.get("mermaid_code", ""))})
    
    try:
        mermaid_code = state.get("mermaid_code")
        if not mermaid_code:
            raise RenderingError("No Mermaid code in state")
        
        # Render diagram using context manager
        async with DrawIODriver() as driver:
            await driver.render_mermaid(mermaid_code)
        
        # Update state
        state["diagram_rendered"] = True
        
        logger.end(state, {"status": "success"})
        return state
        
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"Rendering failed: {str(e)}")
        state["diagram_rendered"] = False
        raise


def render_diagram_node(state: GraphState) -> GraphState:
    """
    Synchronous wrapper for LangGraph compatibility.
    
    LangGraph requires synchronous node functions, so this wraps
    the async implementation in asyncio.run().
    """
    return asyncio.run(_render_diagram_node_async(state))
