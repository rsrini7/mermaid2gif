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
        Capture video of animated diagram with smart viewport sizing.
        
        Uses a two-phase approach:
        1. Measure: Detect actual SVG dimensions
        2. Record: Create video with exact fit (no excess white space)
        
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
        
        self.logger.info("Initializing smart viewport capture", metadata={
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
                # ============================================================
                # PHASE 1: MEASUREMENT (Probe)
                # ============================================================
                self.logger.info("Phase 1: Measuring diagram dimensions")
                
                # Create temporary context for measurement (no recording)
                measure_context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080}
                )
                measure_page = await measure_context.new_page()
                
                # Load HTML and wait for SVG
                await measure_page.set_content(animated_html)
                await measure_page.wait_for_selector("svg", timeout=5000)
                
                # Measure the SVG bounding box
                bbox = await measure_page.evaluate("""
                    () => {
                        const svg = document.querySelector('svg');
                        if (!svg) return null;
                        const rect = svg.getBoundingClientRect();
                        return { 
                            width: Math.ceil(rect.width), 
                            height: Math.ceil(rect.height) 
                        };
                    }
                """)
                
                # Close measurement context
                await measure_context.close()
                
                if not bbox or bbox['width'] <= 0 or bbox['height'] <= 0:
                    raise RuntimeError(f"Invalid SVG dimensions detected: {bbox}")
                
                # Calculate final dimensions with padding
                padding = 40
                raw_width = bbox['width'] + padding
                raw_height = bbox['height'] + padding
                
                # Ensure dimensions are even (FFmpeg requirement)
                final_width = raw_width if raw_width % 2 == 0 else raw_width + 1
                final_height = raw_height if raw_height % 2 == 0 else raw_height + 1
                
                self.logger.info("Diagram dimensions measured", metadata={
                    "svg_width": bbox['width'],
                    "svg_height": bbox['height'],
                    "final_width": final_width,
                    "final_height": final_height,
                    "padding": padding
                })
                
                # ============================================================
                # PHASE 2: RECORDING (Action)
                # ============================================================
                self.logger.info("Phase 2: Recording with optimized viewport")
                
                # Create context with exact dimensions for recording
                context = await browser.new_context(
                    viewport={"width": final_width, "height": final_height},
                    record_video_dir=str(output_dir),
                    record_video_size={"width": final_width, "height": final_height}
                )
                
                page = await context.new_page()
                
                # Load the animated HTML
                await page.set_content(animated_html)
                
                # Wait for SVG to be present
                await page.wait_for_selector("svg", timeout=5000)
                
                # Inject CSS to center the content
                await page.add_style_tag(content="""
                    body {
                        margin: 0;
                        padding: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        background: white;
                    }
                """)
                
                self.logger.info("Starting video recording", metadata={
                    "duration_seconds": duration,
                    "buffer_seconds": 2.0,
                    "viewport": f"{final_width}x{final_height}"
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
                
                self.logger.info("Video saved with smart viewport", metadata={
                    "path": str(video_path),
                    "size_bytes": video_path.stat().st_size,
                    "dimensions": f"{final_width}x{final_height}"
                })
                
                return video_path
                
            finally:
                await browser.close()
