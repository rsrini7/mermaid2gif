"""
Intent and Mermaid generation agent.

This agent converts natural language input into Mermaid diagram code
using LiteLLM with structured JSON output.
"""

import json
from typing import Any, Dict

import litellm

from ..core.config import get_config
from ..core.exceptions import LLMError, LLMResponseError, LLMTimeoutError
from ..core.state import GraphState
from ..utils.logger import get_logger

logger = get_logger("intent_agent")

# System prompt for intent agent
INTENT_SYSTEM_PROMPT = """You are a Mermaid Diagram Expert. Convert input text to a standard Mermaid diagram.

Supported diagram types:
- flowchart LR (left to right flowchart)
- flowchart TD (top to bottom flowchart)
- sequenceDiagram

Output JSON with the following structure:
{
  "mermaid": "string - the complete Mermaid diagram code",
  "animation": {
    "duration": number - animation duration in seconds (default: 5.0),
    "preset": "string - animation preset name (default, fast, slow, presentation)"
  }
}

Rules:
- Use clear, descriptive node labels
- Keep diagrams simple and focused
- Use standard Mermaid syntax only
- Include proper diagram type declaration
- Ensure all connections are valid
"""


def intent_agent(state: GraphState) -> GraphState:
    """
    LangGraph node: Convert natural language to Mermaid diagram.
    
    This agent:
    1. Takes raw text input from state
    2. Calls LiteLLM with structured JSON output
    3. Extracts Mermaid code and animation manifest
    4. Updates state with results
    
    Args:
        state: Current graph state
        
    Returns:
        GraphState: Updated state with mermaid_code and animation_manifest
    """
    logger.start(state, {"input_length": len(state.get("raw_input", ""))})
    
    try:
        config = get_config()
        raw_input = state.get("raw_input", "")
        
        if not raw_input:
            raise LLMError("No raw_input in state")
        
        # Prepare messages for LiteLLM
        messages = [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Convert this to a Mermaid diagram:\n\n{raw_input}"},
        ]
        
        # Call LiteLLM with structured JSON output
        # Use Groq API key if available, otherwise OpenRouter
        api_key = config.groq_api_key or config.openrouter_api_key
        
        try:
            response = litellm.completion(
                model=config.litellm_model,
                messages=messages,
                api_key=api_key,
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2000,
                timeout=30,
            )
        except litellm.Timeout as e:
            raise LLMTimeoutError(f"LLM request timed out: {e}")
        except Exception as e:
            raise LLMError(f"LLM request failed: {e}")
        
        # Extract response content
        content = response.choices[0].message.content
        
        # Parse JSON response
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMResponseError(f"Failed to parse LLM response as JSON: {e}")
        
        # Validate response structure
        if "mermaid" not in result:
            raise LLMResponseError("LLM response missing 'mermaid' key")
        
        # Extract Mermaid code and animation manifest
        mermaid_code = result["mermaid"]
        animation_manifest = result.get("animation", {
            "duration": 5.0,
            "preset": "default",
        })
        
        # Update state
        state["mermaid_code"] = mermaid_code
        state["animation_manifest"] = animation_manifest
        
        logger.end(state, {
            "mermaid_length": len(mermaid_code),
            "animation_preset": animation_manifest.get("preset"),
        })
        
        return state
        
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"Intent agent failed: {str(e)}")
        raise


def input_router(state: GraphState) -> GraphState:
    """
    LangGraph node: Route input based on type.
    
    Determines if input is already Mermaid code or natural language text.
    
    Args:
        state: Current graph state
        
    Returns:
        GraphState: Updated state (unchanged, just validates input type)
    """
    logger.start(state, {"input_type": state.get("raw_input_type")})
    
    try:
        input_type = state.get("raw_input_type", "text")
        
        # If input is already Mermaid, copy it to mermaid_code
        if input_type == "mermaid":
            state["mermaid_code"] = state.get("raw_input", "")
            state["animation_manifest"] = {
                "duration": 5.0,
                "preset": "default",
            }
        
        logger.end(state, {"routed_to": "mermaid" if input_type == "mermaid" else "intent_agent"})
        
        return state
        
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"Input router failed: {str(e)}")
        raise
