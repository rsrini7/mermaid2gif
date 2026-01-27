"""
Draw.io renderer using headless browser with JavaScript injection.

This module drives the headless browser to render Mermaid diagrams using Draw.io's
embed mode. It uses JavaScript injection via page.evaluate() to call internal APIs,
avoiding all UI automation.

CRITICAL CONSTRAINTS:
- NO UI clicks or selectors
- JavaScript injection only via page.evaluate()
- Embed mode URL required
- Headless execution only
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from ..core.config import get_config
from ..core.exceptions import DrawIOImportError, DrawIOTimeoutError, RenderingError
from ..core.state import GraphState
from ..utils.logger import get_logger

# Draw.io embed mode URL - strictly per REQUIREMENTS.md
DRAWIO_EMBED_URL = "https://embed.diagrams.net/?ui=min&spin=1&proto=json&configure=1"

# Fixed viewport for deterministic rendering
DEFAULT_VIEWPORT = {"width": 1200, "height": 12000}

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
        self.playwright = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        
        launch_args = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        }
        
        if self.config.chromium_executable_path:
            launch_args["executable_path"] = str(self.config.chromium_executable_path)
            
        self.browser = await self.playwright.chromium.launch(**launch_args)
        
        context = await self.browser.new_context(viewport=DEFAULT_VIEWPORT)
        self.page = await context.new_page()
        
        # Navigate to Draw.io embed mode
        logger.info(f"Navigating to {DRAWIO_EMBED_URL}")
        try:
            await self.page.goto(DRAWIO_EMBED_URL, wait_until="networkidle", timeout=self.config.browser_timeout_ms)
        except PlaywrightTimeoutError:
            raise DrawIOTimeoutError(f"Timeout navigating to {DRAWIO_EMBED_URL}")
            
        # Wait for App object to be available - Critical for reliability
        try:
            await self.page.wait_for_function("typeof App !== 'undefined'", timeout=30000)
        except PlaywrightTimeoutError:
            raise DrawIOImportError("Draw.io App object not initialized within timeout")
            
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def render_mermaid(self, mermaid_code: str) -> bool:
        """
        Render Mermaid code using Draw.io's internal API.
        
        Args:
            mermaid_code: The Mermaid diagram code to render
            
        Returns:
            True if rendering was successful
            
        Raises:
            DrawIOImportError: If import fails
            RenderingError: If validation fails
        """
        if not self.page:
            raise RenderingError("Driver not initialized. Use 'async with' context.")
            
        logger.info("Importing Mermaid code via App.importData()")
        
        try:
            # Inject JavaScript to call App.importData(mermaid_code, true)
            # This is the core requirement - NO UI automation
            import_result = await self.page.evaluate(
                """
                async (mermaidCode) => {
                    try {
                        if (typeof App === 'undefined' || !App.importData) {
                             return { success: false, error: 'App.importData not available' };
                        }
                        App.importData(mermaidCode, true);
                        return { success: true };
                    } catch (error) {
                        return { success: false, error: error.message };
                    }
                }
                """,
                mermaid_code,
            )
            
            if not import_result.get("success"):
                error_msg = import_result.get("error", "Unknown error")
                raise DrawIOImportError(f"Failed to import Mermaid data: {error_msg}")
            
            # Allow some time for rendering to complete
            await asyncio.sleep(2.0)
            
            # Validate diagram exists
            return await self._validate_diagram()
            
        except Exception as e:
            if isinstance(e, (DrawIOImportError, RenderingError)):
                raise
            raise RenderingError(f"Unexpected error during rendering: {str(e)}")

    async def _validate_diagram(self) -> bool:
        """
        Validate that a diagram was actually rendered.
        
        Checks if the diagram container has content with non-zero dimensions.
        """
        try:
            # Check for geDiagramContainer which Draw.io uses
            bounds = await self.page.evaluate(
                """
                () => {
                    const container = document.querySelector('.geDiagramContainer');
                    if (!container) {
                        // Fallback for some view modes
                        const svg = document.querySelector('svg');
                        if (svg) {
                             const rect = svg.getBoundingClientRect();
                             return { width: rect.width, height: rect.height };
                        }
                        return { width: 0, height: 0, error: 'Container not found' };
                    }
                    // Check first child (usually svg or canvas)
                    const content = container.firstElementChild;
                    if (!content) return { width: 0, height: 0 };
                    
                    const rect = content.getBoundingClientRect();
                    return { width: rect.width, height: rect.height };
                }
                """
            )
            
            width = bounds.get("width", 0)
            height = bounds.get("height", 0)
            
            if width < 10 or height < 10:
                logger.warning(f"Rendered diagram is too small: {width}x{height}")
                raise RenderingError(f"Rendered diagram is empty or too small ({width}x{height})")
                
            logger.info(f"Diagram rendered successfully: {width}x{height}")
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise RenderingError(f"Failed to validate diagram: {str(e)}")

    async def capture_screenshot(self, output_path: Path) -> Path:
        """Capture a screenshot of the current page."""
        if not self.page:
            raise RenderingError("Driver not initialized")
            
        await self.page.screenshot(path=str(output_path), full_page=True)
        return output_path


async def _render_diagram_node_async(state: GraphState) -> GraphState:
    """
    LangGraph node: Render Mermaid diagram using Draw.io.
    """
    logger.start(state)
    
    try:
        mermaid_code = state.get("mermaid_code")
        if not mermaid_code:
            raise RenderingError("No Mermaid code in state")
            
        async with DrawIODriver() as driver:
            await driver.render_mermaid(mermaid_code)
            
        state["diagram_rendered"] = True
        # Note: We don't keep the browser open between nodes in this architecture
        # The AnimationApplicator will need to re-render or re-open.
        # Ideally, we should pass the browser context, but LangGraph state is serializable.
        # For this design, we might need to combine render and animate, 
        # OR re-open in each step.
        # But wait, REQUIREMENTS say: "Renderer volatility must be isolated".
        # If we close the browser, we lose the state.
        # 
        # However, looking at the graph: Draw.io Renderer -> Animation Applicator -> Capture Controller.
        # If they are separate nodes, they run separately.
        # 
        # The CaptureController needs to launch the browser, render, animate, and capture.
        # The 'render_diagram_node' here might just be a validation step or 
        # it might produce an artifact (HTML/XML) that is passed on?
        # A headless browser *cannot* be passed in state (not serializable).
        #
        # Re-reading Requirements:
        # "Capture Controller Node... Force animation duration... Capture exact duration"
        
        # Strategy:
        # 1. This node (render_diagram_node) validates that Draw.io CAN render it.
        # 2. CaptureController will re-run the full pipeline (render -> animate -> record) 
        #    to ensure continuity in a single browser session.
        # OR
        # We assume this node is just for "Can it render?" check.
        
        logger.end(state, {"status": "success"})
        return state
        
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"Rendering failed: {str(e)}")
        # Check if it's an import error to potentially retry or fix
        if "App.importData" in str(e) or "Parse error" in str(e):
             # Let the graph routing decide (retry or fix)
             pass
        raise


def render_diagram_node(state: GraphState) -> GraphState:
    """
    Synchronous wrapper for LangGraph compatibility.
    
    LangGraph requires synchronous node functions, so this wraps
    the async implementation in asyncio.run().
    """
    return asyncio.run(_render_diagram_node_async(state))
