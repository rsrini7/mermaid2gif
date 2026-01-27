"""
Animation applicator using JavaScript injection to apply flow animations.

This module injects JavaScript into the Draw.io page to apply the "Flow Animation"
style to diagram edges, creating the animated effect.

CRITICAL FEATURES:
- JavaScript injection only (NO UI automation)
- Access to internal mxGraph API via captured instance
- Style application to edges
- Graph refresh for immediate effect
"""

import asyncio
from typing import Optional, Dict, Any

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from ..core.config import get_config
from ..core.exceptions import AnimationError, RenderingError
from ..core.state import GraphState
from ..utils.logger import get_logger
from .drawio_utils import (
    DRAWIO_URL,
    PATCH_MXGRAPH_JS,
    WAIT_FOR_INIT_JS,
    SEND_CONFIGURE_JS,
    SEND_LOAD_JS,
    CHECK_RENDER_JS,
    APPLY_ANIMATION_JS
)

logger = get_logger("animation_applicator")


class AnimationApplicator:
    """
    Animation applicator using JavaScript injection.
    
    This applicator:
    1. Replicates the Draw.io renderings state
    2. Accesses the internal mxGraph instance via capture
    3. Applies flow animation styles to edges
    """
    
    def __init__(self):
        """Initialize the animation applicator."""
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
        
        # Use standard viewport
        self.page = await self.browser.new_page()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def apply_flow_animation(
        self,
        mermaid_code: str,
        animation_manifest: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Apply flow animation to diagram edges.
        
        This method fully re-renders the diagram to ensure it has a handle
        on the mxGraph instance, then applies the animation styles.
        """
        if not self.page:
            raise AnimationError("Browser not initialized")
        
        try:
            # --- PHASE 1: RE-RENDER (Identical to DrawIODriver) ---
            logger.info("Initializing Draw.io for animation...")
            await self.page.goto(DRAWIO_URL, wait_until="networkidle", timeout=self.config.browser_timeout_ms)
            
            # Setup (Patching & Init)
            await self.page.evaluate(PATCH_MXGRAPH_JS)
            init_success = await self.page.evaluate(WAIT_FOR_INIT_JS)
            if not init_success:
                logger.warning("Draw.io 'init' message timed out")
            
            # Configure & Load
            await self.page.evaluate(SEND_CONFIGURE_JS)
            await asyncio.sleep(0.5)
            await self.page.evaluate(SEND_LOAD_JS, mermaid_code)
            
            # Verify Render & Capture
            logger.info("Waiting for graph to be captured...")
            graph_captured = False
            for _ in range(10):
                status = await self.page.evaluate(CHECK_RENDER_JS)
                if status.get("hasSvg") and status.get("hasCapturedGraph"):
                    graph_captured = True
                    break
                await asyncio.sleep(0.5)
                
            if not graph_captured:
                raise RenderingError("Failed to capture mxGraph instance for animation")
                
            # --- PHASE 2: APPLY ANIMATION ---
            logger.info("Applying animation styles...")
            result = await self.page.evaluate(APPLY_ANIMATION_JS)
            
            if not result.get("success"):
                raise AnimationError(f"Failed to apply animation: {result.get('error')}")
            
            edge_count = result.get("edgeCount", 0)
            if edge_count == 0:
                logger.warning("No edges found to animate")
            else:
                logger.info(f"Applied animation to {edge_count} edges")
            
            # Stabilize
            await asyncio.sleep(0.5)
            
        except Exception as e:
            if isinstance(e, (AnimationError, RenderingError)):
                raise
            raise AnimationError(f"Unexpected error applying animation: {str(e)}")


async def _apply_animation_async(state: GraphState) -> GraphState:
    """Async implementation of animation application node."""
    logger.start(state)
    
    try:
        mermaid_code = state.get("mermaid_code")
        if not mermaid_code:
            raise AnimationError("No Mermaid code in state")
            
        async with AnimationApplicator() as applicator:
            await applicator.apply_flow_animation(mermaid_code, state.get("animation_manifest"))
            
        state["animation_applied"] = True
        logger.end(state, {"status": "success"})
        return state
        
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"Animation failed: {str(e)}")
        # We don't necessarily fail the pipeline, as static diagram might still be valid
        # But for verification we might want to know
        state["animation_applied"] = False
        raise


def animation_applicator(state: GraphState) -> GraphState:
    """Synchronous wrapper for LangGraph."""
    return asyncio.run(_apply_animation_async(state))
