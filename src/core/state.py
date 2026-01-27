"""
Canonical LangGraph state definition.

All nodes MUST read/write exclusively through this state.
This ensures deterministic execution and proper state tracking.
"""

from typing import Any, Dict, List, Optional, TypedDict


class GraphState(TypedDict):
    """
    Canonical state for the Mermaid-GIF LangGraph.
    
    All nodes must interact exclusively through this state structure.
    No side effects or external state mutations are allowed.
    
    Attributes:
        raw_input: Original user input (text or Mermaid code)
        raw_input_type: Type of input ("text" or "mermaid")
        mermaid_code: Validated Mermaid diagram code
        animation_manifest: Animation configuration and directives
        validation_errors: List of validation errors from Mermaid parser
        diagram_rendered: Flag indicating successful diagram rendering
        animation_applied: Flag indicating successful animation application
        video_path: Path to captured video file
        gif_path: Path to final GIF output
        errors: List of error messages encountered during execution
        artifacts: Dictionary of artifacts (screenshots, logs, etc.)
        retry_count: Current retry attempt count for fix loops
    """
    
    # Input fields
    raw_input: str
    raw_input_type: str  # "text" or "mermaid"
    
    # Mermaid generation/validation
    mermaid_code: Optional[str]
    animation_manifest: Optional[Dict[str, Any]]
    validation_errors: Optional[List[Dict[str, Any]]]
    
    # Rendering state
    diagram_rendered: bool
    animation_applied: bool
    
    # Output paths
    video_path: Optional[str]
    gif_path: Optional[str]
    
    # Error tracking
    errors: List[str]
    
    # Artifacts and metadata
    artifacts: Dict[str, Any]
    
    # Retry management
    retry_count: int


def create_initial_state(raw_input: str, input_type: str = "text") -> GraphState:
    """
    Create an initial GraphState with default values.
    
    Args:
        raw_input: The user's input (text description or Mermaid code)
        input_type: Type of input ("text" or "mermaid")
    
    Returns:
        GraphState: Initial state object
    """
    return GraphState(
        raw_input=raw_input,
        raw_input_type=input_type,
        mermaid_code=None,
        animation_manifest=None,
        validation_errors=None,
        diagram_rendered=False,
        animation_applied=False,
        video_path=None,
        gif_path=None,
        errors=[],
        artifacts={},
        retry_count=0,
    )
