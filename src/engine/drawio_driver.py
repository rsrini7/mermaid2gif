"""
Draw.io driver for rendering Mermaid diagrams.

This module controls a headless browser to interact with Draw.io's embed mode.
It handles the critical task of converting Mermaid text into a rendered diagram
by driving the web application directly.

CRITICAL FEATURES:
- Uses embed.diagrams.net (remote) per REQUIREMENTS.md
- Protocol: 'proto=json' with postMessage workflow
- Captures mxGraph instance for downstream animation
"""

import asyncio
import json
from typing import Dict, Any, Optional

from playwright.async_api import Page, async_playwright, TimeoutError as PlaywrightTimeoutError

from ..core.config import get_config
from ..core.exceptions import DrawIOImportError
from ..core.state import GraphState
from ..utils.logger import get_logger
from .drawio_utils import (
    DRAWIO_URL,
    PATCH_MXGRAPH_JS,
    WAIT_FOR_INIT_JS,
    SEND_CONFIGURE_JS,
    SEND_LOAD_JS,
    CHECK_RENDER_JS,
)

logger = get_logger("drawio_driver")


class DrawIODriver:
    """
    Driver for controlling Draw.io via Playwright.
    
    This class manages the browser page interaction to:
    1. Load the Draw.io embed application
    2. Inject Mermaid code via postMessage
    3. Verify successful rendering
    """
    
    def __init__(self, page: Page):
        """
        Initialize the driver.
        
        Args:
            page: Playwright Page instance
        """
        self.page = page
        self.config = get_config()

    async def render_mermaid(self, mermaid_code: str) -> None:
        """
        Render Mermaid code in Draw.io.
        
        This method executes the complex initialization sequence:
        1. Navigates to embed URL
        2. Patches mxGraph to capture instance
        3. Waits for init handshake
        4. Sends configuration
        5. Sends Mermaid code via 'load' action
        
        Args:
            mermaid_code: The Mermaid diagram definition
            
        Raises:
            DrawIOImportError: If rendering fails
        """
        try:
            # 1. Navigate
            logger.info(f"Navigating to {DRAWIO_URL}")
            await self.page.goto(DRAWIO_URL, wait_until="networkidle", timeout=self.config.browser_timeout_ms)
            
            # 2. Setup (Patching & Init Listener)
            # We patch BEFORE the graph is created to ensure we capture it
            await self.page.evaluate(PATCH_MXGRAPH_JS)
            
            # 3. Wait for Init
            # We inject the listener and wait for the promise to resolve
            logger.info("Waiting for Draw.io initialization...")
            init_success = await self.page.evaluate(WAIT_FOR_INIT_JS)
            
            if not init_success:
                logger.warning("Draw.io 'init' message timed out. Attempting to proceed...")
            
            # 4. Configure
            logger.info("Configuring Draw.io...")
            await self.page.evaluate(SEND_CONFIGURE_JS)
            
            # Small buffer for config to process
            await asyncio.sleep(0.5)
            
            # 5. Load Mermaid
            logger.info("Sending Mermaid code...")
            await self.page.evaluate(SEND_LOAD_JS, mermaid_code)
            
            # 6. Verify Render
            # Wait for SVG to appear and graph to be captured
            logger.info("Waiting for render...")
            for attempt in range(10): # 5 seconds max
                status = await self.page.evaluate(CHECK_RENDER_JS)
                if status.get("hasSvg") and status.get("hasCapturedGraph"):
                    logger.info("Render verified and graph captured!")
                    return
                await asyncio.sleep(0.5)
            
            # If we get here, check one last time strictly for SVG (maybe capture failed?)
            status = await self.page.evaluate(CHECK_RENDER_JS)
            if status.get("hasSvg"):
                logger.warning("Render succeeded but graph capture failed. Animation might fail.")
                return
                
            raise DrawIOImportError("Render validation failed: SVG not found in DOM")

        except Exception as e:
            if isinstance(e, DrawIOImportError):
                raise
            raise DrawIOImportError(f"Failed to import Mermaid data: {str(e)}")


async def _render_diagram_node_async(state: GraphState) -> GraphState:
    """
    Async wrapper for LangGraph.
    
    This node manages the browser lifecycle for the driver.
    """
    logger.start(state)
    try:
        mermaid_code = state.get("mermaid_code")
        if not mermaid_code:
            raise DrawIOImportError("No Mermaid code in state")
            
        # Launch browser just for this validation step
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, 
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            page = await browser.new_page()
            
            driver = DrawIODriver(page)
            await driver.render_mermaid(mermaid_code)
            
            await browser.close()
            
        state["diagram_rendered"] = True
        logger.end(state, {"status": "success"})
        return state
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"Rendering failed: {str(e)}")
        raise

def render_diagram_node(state: GraphState) -> GraphState:
    """Synchronous wrapper for LangGraph."""
    return asyncio.run(_render_diagram_node_async(state))
