"""
Custom exceptions for Mermaid-GIF system.

All exceptions follow a hierarchy to enable precise error handling
and recovery strategies in the LangGraph.
"""


class MermaidGIFError(Exception):
    """Base exception for all Mermaid-GIF errors."""
    pass


# ============================================
# Configuration Errors
# ============================================

class ConfigurationError(MermaidGIFError):
    """Raised when configuration is invalid or missing."""
    pass


# ============================================
# Validation Errors
# ============================================

class ValidationError(MermaidGIFError):
    """Base class for validation errors."""
    pass


class MermaidSyntaxError(ValidationError):
    """Raised when Mermaid code has syntax errors."""
    pass


class MermaidStructureError(ValidationError):
    """Raised when Mermaid code has structural errors."""
    pass


# ============================================
# Rendering Errors
# ============================================

class RenderingError(MermaidGIFError):
    """Base class for rendering errors."""
    pass





class AnimationApplicationError(RenderingError):
    """Raised when animation cannot be applied to diagram."""
    pass


class AnimationError(RenderingError):
    """Raised when animation application fails via JavaScript injection."""
    pass


# ============================================
# Capture Errors
# ============================================

class CaptureError(MermaidGIFError):
    """Base class for capture errors."""
    pass


class VideoRecordingError(CaptureError):
    """Raised when video recording fails."""
    pass


# ============================================
# Encoding Errors
# ============================================

class EncodingError(MermaidGIFError):
    """Base class for encoding errors."""
    pass


class FFmpegError(EncodingError):
    """Raised when FFmpeg processing fails."""
    pass


class GIFGenerationError(EncodingError):
    """Raised when GIF generation fails."""
    pass


# ============================================
# Retry Exhaustion
# ============================================

class RetryExhaustedError(MermaidGIFError):
    """Raised when retry limit is exceeded."""
    
    def __init__(self, node_name: str, max_retries: int):
        self.node_name = node_name
        self.max_retries = max_retries
        super().__init__(
            f"Retry limit exceeded in node '{node_name}' (max: {max_retries})"
        )


# ============================================
# LLM Errors
# ============================================

class LLMError(MermaidGIFError):
    """Base class for LLM-related errors."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    pass


class LLMResponseError(LLMError):
    """Raised when LLM response is invalid or unparseable."""
    pass
