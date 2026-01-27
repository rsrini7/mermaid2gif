"""
FFmpeg processor for converting video to optimized, looping GIF.

This module uses ffmpeg-python to convert captured video into high-quality,
seamlessly looping GIFs using palette-based encoding.

CRITICAL FEATURES:
- Palette-based encoding for quality
- Filter complex for optimal color mapping
- Seamless looping support
- Configurable scaling and frame rate
"""

import subprocess
from pathlib import Path
from typing import Optional

import ffmpeg

from ..core.config import get_config
from ..core.exceptions import FFmpegError, GIFGenerationError
from ..core.state import GraphState
from ..utils.logger import get_logger

logger = get_logger("ffmpeg_processor")


class FFmpegProcessor:
    """
    FFmpeg-based video to GIF converter.
    
    Uses a two-pass palette generation approach:
    1. Generate optimal color palette from video
    2. Apply palette to create high-quality GIF
    """
    
    def __init__(self):
        """Initialize the FFmpeg processor."""
        self.config = get_config()
    
    def convert_to_gif(
        self,
        video_path: Path,
        output_path: Path,
        fps: Optional[int] = None,
        scale_width: int = 1280,
    ) -> None:
        """
        Convert video to optimized GIF using palette-based encoding.
        
        This method uses FFmpeg's filter complex to:
        1. Split the input stream
        2. Generate a color palette from one stream
        3. Apply the palette to the other stream for optimal quality
        
        Args:
            video_path: Path to input video file
            output_path: Path to output GIF file
            fps: Frame rate for output GIF (default: from config)
            scale_width: Width for output GIF (height auto-scaled, default: 800)
            
        Raises:
            FFmpegError: If FFmpeg processing fails
            GIFGenerationError: If GIF generation fails
        """
        if not video_path.exists():
            raise FFmpegError(f"Video file not found: {video_path}")
        
        # Use configured FPS if not specified
        if fps is None:
            fps = self.config.default_fps
        
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build FFmpeg filter complex
            # This implements the two-pass palette approach:
            # 1. Split input: [0:v] split [a][b]
            # 2. Generate palette: [a] palettegen [p]
            # 3. Apply palette: [b][p] paletteuse
            
            # Skip first 1.0 second (loading buffer) and take duration length
            # This ensures we get a clean loop without blank frames
            input_stream = ffmpeg.input(
                str(video_path),
                ss=1.0,
                t=self.config.default_animation_duration  # 5.0s by default
            )
            
            # Split the video stream into two branches with labels
            split_outputs = input_stream.video.split()
            
            # Branch 1: Generate high-quality palette with more colors
            palette = split_outputs[0].filter(
                "palettegen",
                max_colors=256,
                stats_mode="diff"
            )
            
            # Branch 2: Scale to higher resolution for better quality
            scaled = split_outputs[1].filter("scale", w=scale_width, h=-1, flags="lanczos")
            
            # Apply palette with improved dithering
            output = ffmpeg.filter(
                [scaled, palette],
                "paletteuse",
                dither="sierra2_4a",
                diff_mode="rectangle"
            )
            
            # Set frame rate
            output = output.filter("fps", fps=fps)
            
            # Configure output with loop settings
            output = ffmpeg.output(
                output,
                str(output_path),
                loop=0,  # Infinite loop
                **{"f": "gif"},
            )
            
            # Run FFmpeg
            output.overwrite_output().run(
                capture_stdout=True,
                capture_stderr=True,
                quiet=True,
            )
            
            # Validate output
            if not output_path.exists():
                raise GIFGenerationError("GIF file was not created")
            
            if output_path.stat().st_size == 0:
                raise GIFGenerationError("GIF file is empty")
            
        except (FFmpegError, GIFGenerationError):
            raise
        except Exception as e:
            # Handle any other exceptions (including ffmpeg.Error if present)
            error_msg = str(e)
            if hasattr(e, 'stderr'):
                try:
                    stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
                    error_msg = f"FFmpeg processing failed: {stderr}"
                except:
                    pass
            raise GIFGenerationError(f"Error during GIF generation: {error_msg}")
    
    def get_video_info(self, video_path: Path) -> dict:
        """
        Get video metadata using ffprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            dict: Video metadata (duration, width, height, fps)
            
        Raises:
            FFmpegError: If ffprobe fails
        """
        if not video_path.exists():
            raise FFmpegError(f"Video file not found: {video_path}")
        
        try:
            probe = ffmpeg.probe(str(video_path))
            video_stream = next(
                (s for s in probe["streams"] if s["codec_type"] == "video"),
                None,
            )
            
            if not video_stream:
                raise FFmpegError("No video stream found")
            
            return {
                "duration": float(probe["format"].get("duration", 0)),
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "fps": eval(video_stream.get("r_frame_rate", "0/1")),
            }
            
        except FFmpegError:
            raise
        except Exception as e:
            # Handle any exceptions (including ffmpeg.Error if present)
            error_msg = str(e)
            if hasattr(e, 'stderr'):
                try:
                    stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
                    error_msg = f"ffprobe failed: {stderr}"
                except:
                    pass
            raise FFmpegError(f"Failed to get video info: {error_msg}")


def transcode_to_gif_node(state: GraphState) -> GraphState:
    """
    LangGraph node: Convert captured video to optimized GIF.
    
    This node:
    1. Reads video_path from state
    2. Converts video to GIF using palette-based encoding
    3. Updates state with gif_path
    
    Args:
        state: Current graph state
        
    Returns:
        GraphState: Updated state with gif_path
    """
    logger.start(state, {"video_path": state.get("video_path")})
    
    try:
        video_path = state.get("video_path")
        if not video_path:
            raise GIFGenerationError("No video_path in state")
        
        video_path = Path(video_path)
        
        # Generate output path
        output_path = video_path.parent / f"{video_path.stem}.gif"
        
        # Convert to GIF
        processor = FFmpegProcessor()
        processor.convert_to_gif(video_path, output_path)
        
        # Get video info for metadata
        video_info = processor.get_video_info(video_path)
        
        # Update state
        state["gif_path"] = str(output_path)
        state["artifacts"]["video_info"] = video_info
        state["artifacts"]["gif_size_bytes"] = output_path.stat().st_size
        
        logger.end(state, {
            "gif_path": str(output_path),
            "gif_size_mb": round(output_path.stat().st_size / 1024 / 1024, 2),
        })
        
        return state
        
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"GIF generation failed: {str(e)}")
        raise
