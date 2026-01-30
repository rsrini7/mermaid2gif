"""
LangGraph orchestration for Mermaid2GIF system.

This module defines the state machine that orchestrates the entire
Mermaid to GIF conversion pipeline using LangGraph.
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from .state import GraphState
from ..agents.intent import intent_agent, input_router
from ..agents.fixer import mermaid_fix_agent
from ..engine.mermaid_renderer import render_mermaid_node
from ..engine.ffmpeg_processor import transcode_to_gif_node
from ..engine.mermaid_validator import mermaid_validator
from ..engine.animation_applicator import apply_animation_node
from ..engine.capture_controller import capture_video_node
from ..utils.logger import get_logger, configure_logging

logger = get_logger("graph")


# ============================================
# Helper Nodes
# ============================================

def animation_planner(state: GraphState) -> GraphState:
    """
    Plan animation settings.
    
    This node normalizes animation directives and ensures
    a valid animation_manifest exists in state.
    """
    logger.start(state)
    
    # Use existing manifest or create default
    if not state.get("animation_manifest"):
        state["animation_manifest"] = {
            "duration": 5.0,
            "preset": "default",
        }
    
    logger.end(state, {"preset": state["animation_manifest"].get("preset")})
    return state


# ============================================
# Conditional Routing Functions
# ============================================

def should_fix_mermaid(state: GraphState) -> Literal["fix_mermaid", "animation_planner"]:
    """
    Conditional edge: Route based on validation result.
    
    Args:
        state: Current graph state
        
    Returns:
        str: Next node name ("fix_mermaid" or "animation_planner")
    """
    validation_errors = state.get("validation_errors")
    
    if validation_errors:
        return "fix_mermaid"
    else:
        return "animation_planner"


def should_retry_validation(state: GraphState) -> Literal["mermaid_validator", "end_fail"]:
    """
    Conditional edge: Route based on retry count.
    
    Args:
        state: Current graph state
        
    Returns:
        str: Next node name ("mermaid_validator" or "end_fail")
    """
    from ..core.config import get_config
    
    config = get_config()
    retry_count = state.get("retry_count", 0)
    
    # Route to failure if retry count exceeds configured maximum
    if retry_count > config.max_retry_attempts:
        return "end_fail"
    else:
        return "mermaid_validator"


def should_generate_mermaid(state: GraphState) -> Literal["intent_agent", "mermaid_validator"]:
    """
    Conditional edge: Route based on input type.
    
    Args:
        state: Current graph state
        
    Returns:
        str: Next node name ("intent_agent" or "mermaid_validator")
    """
    input_type = state.get("raw_input_type", "text")
    
    if input_type == "mermaid":
        return "mermaid_validator"
    else:
        return "intent_agent"


# ============================================
# Terminal Nodes
# ============================================

def end_success(state: GraphState) -> GraphState:
    """Terminal node: Successful completion."""
    logger.start(state)
    logger.end(state, {"status": "success", "gif_path": state.get("gif_path")})
    return state


def end_fail(state: GraphState) -> GraphState:
    """Terminal node: Failed completion."""
    logger.start(state)
    logger.end(state, {"status": "failed", "errors": state.get("errors", [])})
    return state


# ============================================
# Graph Construction
# ============================================

def create_graph() -> StateGraph:
    """
    Create the LangGraph state machine.
    
    Graph structure:
    
    ```
    input_router
      ├─> intent_agent ─> mermaid_validator
      └─> mermaid_validator
            ├─> (valid) ─> animation_planner
            └─> (invalid) ─> fix_mermaid
                              ├─> (retry < 2) ─> mermaid_validator
                              └─> (retry >= 2) ─> end_fail
    
    animation_planner ─> mermaid_renderer ─> animation_applicator
      ─> capture_controller ─> ffmpeg_transcoder ─> end_success
    ```
    
    Returns:
        StateGraph: Compiled LangGraph workflow
    """
    # Create workflow
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("input_router", input_router)
    workflow.add_node("intent_agent", intent_agent)
    workflow.add_node("mermaid_validator", mermaid_validator)
    workflow.add_node("fix_mermaid", mermaid_fix_agent)
    workflow.add_node("animation_planner", animation_planner)
    workflow.add_node("mermaid_renderer", render_mermaid_node)
    workflow.add_node("animation_applicator", apply_animation_node)
    workflow.add_node("capture_controller", capture_video_node)
    workflow.add_node("ffmpeg_transcoder", transcode_to_gif_node)
    workflow.add_node("end_success", end_success)
    workflow.add_node("end_fail", end_fail)
    
    # Set entry point
    workflow.set_entry_point("input_router")
    
    # Add edges
    # input_router -> intent_agent OR mermaid_validator (based on input type)
    workflow.add_conditional_edges(
        "input_router",
        should_generate_mermaid,
        {
            "intent_agent": "intent_agent",
            "mermaid_validator": "mermaid_validator",
        }
    )
    
    # intent_agent -> mermaid_validator
    workflow.add_edge("intent_agent", "mermaid_validator")
    
    # mermaid_validator -> animation_planner OR fix_mermaid (based on validation)
    workflow.add_conditional_edges(
        "mermaid_validator",
        should_fix_mermaid,
        {
            "fix_mermaid": "fix_mermaid",
            "animation_planner": "animation_planner",
        }
    )
    
    # fix_mermaid -> mermaid_validator OR end_fail (based on retry count)
    workflow.add_conditional_edges(
        "fix_mermaid",
        should_retry_validation,
        {
            "mermaid_validator": "mermaid_validator",
            "end_fail": "end_fail",
        }
    )
    
    # Linear pipeline: animation_planner -> mermaid_renderer -> animation_applicator
    workflow.add_edge("animation_planner", "mermaid_renderer")
    workflow.add_edge("mermaid_renderer", "animation_applicator")
    workflow.add_edge("animation_applicator", "capture_controller")
    workflow.add_edge("capture_controller", "ffmpeg_transcoder")
    workflow.add_edge("ffmpeg_transcoder", "end_success")
    
    # Terminal nodes
    workflow.add_edge("end_success", END)
    workflow.add_edge("end_fail", END)
    
    return workflow


def compile_graph():
    """
    Compile the LangGraph workflow.
    
    Returns:
        Compiled workflow ready for execution
    """
    workflow = create_graph()
    return workflow.compile()


def run_graph(state: GraphState) -> GraphState:
    """
    Run the complete Mermaid2GIF pipeline.
    
    Args:
        state: Initial graph state
        
    Returns:
        GraphState: Final state after execution
    """
    # Configure logging
    configure_logging()
    
    logger.start(state, {"input_type": state.get("raw_input_type")})
    
    # Compile and run graph
    app = compile_graph()
    final_state = app.invoke(state)
    
    logger.end(final_state, {
        "success": bool(final_state.get("gif_path")),
        "errors": len(final_state.get("errors", [])),
    })
    
    return final_state
