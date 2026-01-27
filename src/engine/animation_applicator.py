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
from typing import Optional, Dict, Any

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from ..core.config import get_config
from ..core.exceptions import AnimationError, RenderingError
from ..core.state import GraphState
from ..utils.logger import get_logger

# Draw.io embed mode URL (MANDATORY)
DRAWIO_EMBED_URL = "https://embed.diagrams.net/?ui=min&spin=1&proto=json&configure=1"

# Fixed viewport for deterministic rendering
DEFAULT_VIEWPORT = {"width": 1200, "height": 1200}

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
        self.playwright = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        
        launch_args = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        }
        
        if self.config.chromium_path:
            launch_args["executable_path"] = self.config.chromium_path
            
        self.browser = await self.playwright.chromium.launch(**launch_args)
        
        context = await self.browser.new_context(viewport=DEFAULT_VIEWPORT)
        self.page = await context.new_page()
        
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
            raise AnimationError("Browser not initialized")
        
        try:
            # 1. Navigate to Draw.io
            await self.page.goto(DRAWIO_EMBED_URL, wait_until="networkidle", timeout=self.config.browser_timeout_ms)
            
            # 2. Wait for App
            try:
                await self.page.wait_for_function("typeof App !== 'undefined'", timeout=30000)
            except PlaywrightTimeoutError:
                raise RenderingError("Draw.io App object not initialized")
            
            # 3. Import Mermaid
            import_result = await self.page.evaluate(
                """
                async (mermaidCode) => {
                    try {
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
                raise RenderingError(f"Import failed: {import_result.get('error')}")
            
            # 4. Apply Animation via mxGraph API
            # This is the core logic from REQUIREMENTS.md
            animation_result = await self.page.evaluate(
                """
                () => {
                    try {
                        // Access the mxGraph instance
                        // In embed mode with UI, it's usually at window.EditorUi.editor.graph
                        // But we need to find the instance safely
                        
                        // We can look for the EditorUi instance
                        // Usually accessible via the frames or the App object wrapper?
                        // Actually, in the configured UI, App.mainUi usually holds the EditorUi
                        
                        let graph = null;
                        if (App && App.mainUi && App.mainUi.editor) {
                            graph = App.mainUi.editor.graph;
                        }
                        
                        if (!graph) {
                            return { success: false, error: "Cloud not find mxGraph instance" };
                        }
                        
                        // Transaction for updates
                        graph.getModel().beginUpdate();
                        let edgeCount = 0;
                        try {
                            const parent = graph.getDefaultParent();
                            const children = graph.getChildCells(parent);
                            
                            for (let i = 0; i < children.length; i++) {
                                const cell = children[i];
                                if (cell.isEdge()) {
                                    // Set flowAnimation=1
                                    // We need to preserve existing styles
                                    let style = cell.getStyle();
                                    if (!style.includes('flowAnimation=1')) {
                                        if (style && style[style.length - 1] !== ';') style += ';';
                                        style += 'flowAnimation=1;';
                                        graph.getModel().setStyle(cell, style);
                                        edgeCount++;
                                    }
                                }
                            }
                        } finally {
                            graph.getModel().endUpdate();
                        }
                        
                        // Force refresh
                        graph.refresh();
                        
                        return { success: true, edgeCount: edgeCount };
                    } catch (error) {
                        return { success: false, error: error.message };
                    }
                }
                """
            )
            
            if not animation_result.get("success"):
                # Warning only, don't fail hard if animation is tricky, but log it
                # REQUIREMENTS say "Application Node... Idempotent execution"
                # If it fails, we might want to know
                raise AnimationError(f"Failed to apply animation: {animation_result.get('error')}")
            
            edge_count = animation_result.get("edgeCount", 0)
            if edge_count == 0:
                logger.warning("No edges found to animate")
            else:
                logger.info(f"Applied animation to {edge_count} edges")
            
            # Wait a bit to ensure stability
            await asyncio.sleep(0.5)
            
        except Exception as e:
            if isinstance(e, (AnimationError, RenderingError)):
                raise
            raise AnimationError(f"Unexpected error: {str(e)}")


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
        state["animation_applied"] = False
        raise


def animation_applicator(state: GraphState) -> GraphState:
    """Synchronous wrapper for LangGraph."""
    return asyncio.run(_apply_animation_async(state))
