"""
Video capture controller using Playwright's built-in recording.

This module captures the animated diagram as a video file using Playwright's
video recording capabilities. It ensures the recording duration matches the
animation duration for perfect looping.

CRITICAL FEATURES:
- Exact duration matching for seamless loops
- High-quality video capture
- Automatic cleanup of browser resources
- Uses verified Draw.io postMessage workflow
"""

import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page, BrowserContext, TimeoutError as PlaywrightTimeoutError

from ..core.config import get_config
from ..core.exceptions import CaptureError, RenderingError
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

# Fixed viewport for deterministic rendering
DEFAULT_VIEWPORT = {"width": 1200, "height": 1200}

logger = get_logger("capture_controller")


class CaptureController:
    """
    Video capture controller using Playwright.
    
    This controller:
    1. Launches a browser with video recording enabled
    2. Renders the diagram with animations (replicating robust setup)
    3. Records for the exact animation duration
    4. Saves the video file
    """
    
    def __init__(self):
        """Initialize the capture controller."""
        self.config = get_config()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._temp_dir = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Create temporary directory for video
        import tempfile
        self._temp_dir = Path(tempfile.mkdtemp(prefix="mermaid_gif_"))
        await self.launch(self._temp_dir)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def launch(self, record_video_dir: Path) -> None:
        """
        Launch the browser with video recording enabled.
        
        Args:
            record_video_dir: Directory to save video recordings
            
        Raises:
            CaptureError: If browser launch fails
        """
        try:
            playwright = await async_playwright().start()
            
            # Launch Chromium with video recording
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
            
            # Create context with video recording
            self.context = await self.browser.new_context(
                viewport=DEFAULT_VIEWPORT,
                record_video_dir=str(record_video_dir),
                record_video_size=DEFAULT_VIEWPORT,
            )
            
            # Create page
            self.page = await self.context.new_page()
            self.page.set_default_timeout(self.config.browser_timeout_ms)
            
        except Exception as e:
            raise CaptureError(f"Failed to launch browser for capture: {e}")
    
    async def close(self) -> Optional[Path]:
        """
        Close the browser and return the video path.
        
        Returns:
            Path to the recorded video file, or None if no video was recorded
        """
        video_path = None
        
        try:
            if self.page:
                # Get video path before closing
                video = self.page.video
                if video:
                    # Close page to finalize video
                    await self.page.close()
                    # Get the video path
                    video_path = await video.path()
                else:
                    await self.page.close()
            
            if self.context:
                await self.context.close()
            
            if self.browser:
                await self.browser.close()
            
            return Path(video_path) if video_path else None
            
        except Exception as e:
            logger.error(None, e)
            return None
    
    async def capture_animation(
        self,
        mermaid_code: str,
        duration: float,
    ) -> None:
        """
        Capture the animated diagram as video.
        
        This method:
        1. Fully re-renders the diagram using robust Draw.io flow
        2. Applies flow animation
        3. Waits for the exact animation duration
        """
        if not self.page:
            raise CaptureError("Browser not launched. Call launch() first.")
        
        try:
            # --- PHASE 1: RE-RENDER ---
            logger.info("Initializing Draw.io for capture...")
            await self.page.goto(DRAWIO_URL, wait_until="networkidle", timeout=self.config.browser_timeout_ms)
            
            # Setup
            await self.page.evaluate(PATCH_MXGRAPH_JS)
            
            # Init & Heartbeat Handshake
            logger.info("Waiting for Draw.io initialization & handshake...")
            init_success = await self.page.evaluate(WAIT_FOR_INIT_JS)
            if not init_success:
                logger.warning("Draw.io 'init' handshake timed out")
            
            # Configure & Load (Configure already sent by heartbeat)
            logger.info("Sending Mermaid code...")
            await self.page.evaluate(SEND_LOAD_JS, mermaid_code)
            
            # Verify Render & Capture
            logger.info("Waiting for graph capture...")
            graph_captured = False
            for _ in range(20): # 10s timeout
                status = await self.page.evaluate(CHECK_RENDER_JS)
                if status.get("hasSvg") and status.get("hasCapturedGraph") and status.get("hasContent"):
                    graph_captured = True
                    break
                await asyncio.sleep(0.5)
                
            if not graph_captured:
                 logger.warning(f"Graph capture warning: {status}")
                 if not status.get("hasContent"):
                     raise RenderingError("Render failed: Graph is empty (no cells found)")
                 raise RenderingError("Failed to capture mxGraph instance for animation capture")

            # --- PHASE 2: APPLY ANIMATION ---
            logger.info("Applying animation styles...")
            result = await self.page.evaluate(APPLY_ANIMATION_JS)
            if not result.get("success"):
                 logger.warning(f"Animation warning: {result.get('error')}")
            
            # --- PHASE 3: RECORD ---
            # Wait for the exact animation duration to ensure full capture
            # Add a small buffer (0.5s) to ensure we capture the complete loop
            logger.info(f"Recording for {duration} seconds...")
            await asyncio.sleep(duration + 0.5)
            
        except (CaptureError, RenderingError):
            raise
        except Exception as e:
            raise CaptureError(f"Unexpected error during capture: {e}")


async def _capture_video_async(state: GraphState) -> GraphState:
    """
    Async implementation of video capture node.
    """
    logger.start(state, {
        "diagram_rendered": state.get("diagram_rendered"),
        "animation_applied": state.get("animation_applied"),
    })
    
    try:
        # Validate prerequisites
        # Note: animation_applied is set by previous node, but we re-apply it here visually
        # to ensure it's recorded. The flag mainly confirms intent/config.
        if not state.get("diagram_rendered"):
            raise CaptureError("Diagram must be rendered before capture")
        
        if not state.get("animation_applied"):
            raise CaptureError("Animation must be applied before capture")
        
        mermaid_code = state.get("mermaid_code")
        if not mermaid_code:
            raise CaptureError("No Mermaid code in state")
        
        # Get animation duration from manifest
        animation_manifest = state.get("animation_manifest", {})
        duration = animation_manifest.get("duration", 5.0)
        
        # Capture video using context manager
        async with CaptureController() as controller:
            await controller.capture_animation(mermaid_code, duration)
            video_path = await controller.close()
        
        if not video_path or not video_path.exists():
            raise CaptureError("Video file was not created")
        
        # Update state
        state["video_path"] = str(video_path)
        state["artifacts"]["video_duration"] = duration
        state["artifacts"]["video_size_bytes"] = video_path.stat().st_size
        
        logger.end(state, {
            "video_path": str(video_path),
            "size": state["artifacts"]["video_size_bytes"]
        })
        return state
        
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"Capture failed: {str(e)}")
        raise


def capture_controller(state: GraphState) -> GraphState:
    """Synchronous wrapper for LangGraph."""
    return asyncio.run(_capture_video_async(state))
