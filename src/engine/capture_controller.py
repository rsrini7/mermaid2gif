"""
Capture Controller for Mermaid.js Animated Diagrams
Records video of animated SVG diagrams
"""

from playwright.async_api import async_playwright
from pathlib import Path
from ..core.config import get_config
from ..utils.logger import get_logger
from typing import Dict, Any
import asyncio
import nest_asyncio

# Allow nested event loops for LangGraph compatibility
nest_asyncio.apply()

logger = get_logger("capture_controller")


def capture_video_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper for async video capture.
    Required for LangGraph compatibility.
    """
    return asyncio.run(_capture_video_async(state))


async def _capture_video_async(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Capture video of animated Mermaid diagram.
    
    Args:
        state: Graph state containing animated_html artifact
        
    Returns:
        Updated state with video_path artifact
    """
    animated_html = state.get("artifacts", {}).get("animated_html")
    
    if not animated_html:
        raise ValueError("No animated_html found in state artifacts")
    
    logger.info("Starting video capture")
    
    controller = CaptureController()
    try:
        video_path = await controller.capture(animated_html, state)
        
        # Store in artifacts and state root (for ffmpeg_processor)
        state["artifacts"]["video_path"] = str(video_path)
        state["video_path"] = str(video_path)
        
        logger.info("Video capture completed", metadata={
            "video_path": str(video_path)
        })
        
        return state
        
    except Exception as e:
        logger.error(state, e, metadata={
            "component": "capture_controller"
        })
        raise


class CaptureController:
    """Captures video of animated Mermaid diagrams"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("capture_controller")
    
    async def capture(self, animated_html: str, state: Dict[str, Any]) -> Path:
        """
        Capture video of animated diagram.
        
        Args:
            animated_html: HTML with animated SVG
            state: Graph state for configuration
            
        Returns:
            Path to captured video file
        """
        # Get configuration
        duration = state.get("duration", self.config.default_animation_duration)
        fps = 30  # Default FPS
        
        # Create output directory
        output_dir = Path("./output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate dynamic video filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]  # Up to milliseconds
        video_path = output_dir / f"mermaid_{timestamp}.webm"
        
        self.logger.info("Initializing video capture", metadata={
            "duration": duration,
            "fps": fps,
            "output": str(video_path)
        })
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            try:
                # Create context with video recording
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    record_video_dir=str(output_dir),
                    record_video_size={"width": 1920, "height": 1080}
                )
                
                page = await context.new_page()
                
                self.logger.info("Loading animated HTML")
                
                # Load the animated HTML directly
                await page.set_content(animated_html)
                
                # Wait for SVG to be present
                await page.wait_for_selector("svg", timeout=5000)
                
                self.logger.info("Starting video recording", metadata={
                    "duration_seconds": duration,
                    "buffer_seconds": 2.0
                })
                
                # Record longer than needed to create buffers at start and end
                # Start buffer (1.0s): Hides loading/blank frame
                # End buffer (1.0s): Hides context closing
                # We will trim this in FFmpeg later
                await asyncio.sleep(duration + 2.0)
                
                self.logger.info("Video recording complete")
                
                # IMPORTANT: Close context first to stop recording
                # This prevents capturing blank frames when the page closes
                await context.close()
                
                # Get the recorded video path
                # Playwright saves it with a unique name based on page ID
                # We need to find the latest file created in the output dir
                video_files = list(output_dir.glob("*.webm"))
                if not video_files:
                    raise RuntimeError("No video file was created")
                
                # Find the most recently created video file that matches Playwright's random naming
                # Playwright generates random names, so we assume the newest one is ours
                latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
                
                # Rename to our desired dynamic filename
                latest_video.rename(video_path)
                
                self.logger.info("Video saved", metadata={
                    "path": str(video_path),
                    "size_bytes": video_path.stat().st_size
                })
                
                return video_path
                
            finally:
                await browser.close()
