"""
Mermaid syntax fix agent.

This agent repairs syntax errors in Mermaid diagrams using LiteLLM
with structured JSON output.
"""

import json
from typing import List, Dict, Any

import litellm

from ..core.config import get_config
from ..core.exceptions import LLMError, LLMResponseError, LLMTimeoutError, RetryExhaustedError
from ..core.state import GraphState
from ..utils.logger import get_logger

logger = get_logger("fix_agent")

# System prompt for fix agent
FIX_SYSTEM_PROMPT = """You are a Mermaid syntax repair specialist. Fix syntax and structural errors in Mermaid diagrams while preserving the original intent.

COMMON SYNTAX ERRORS TO FIX:

1. **Parentheses in Labels** (Most Common Error)
   - ERROR: A[Return fib(n-1) + fib(n-2)]
   - FIX: A[Return fib n-1 plus fib n-2]
   - FIX: A[Return fibonacci sum]
   
2. **Special Characters in Labels**
   - Remove: () | " ' ` 
   - Replace with words: "Input/Output" → "Input or Output"
   
3. **Invalid Arrow Syntax**
   - ERROR: A -> B (single dash)
   - FIX: A --> B (double dash)
   
4. **Hyphens in Node IDs**
   - ERROR: step-1[Start]
   - FIX: step1[Start] or A[Start]

5. **Unclosed Brackets**
   - ERROR: A[Start --> B[End]
   - FIX: A[Start] --> B[End]

6. **ER Diagram Syntax Errors**
   - ERROR: TEACHER --> DEPARTMENT (wrong arrow)
   - FIX: TEACHER ||--o{ DEPARTMENT : teaches
   - ERROR: TEACHER(id, name) ||--o{ DEPT (attributes in entity)
   - FIX: TEACHER ||--o{ DEPARTMENT : teaches
   - Cardinality: ||--o{ (one-to-many), }o--|| (many-to-one), ||--|| (one-to-one)

FIXING STRATEGY:
1. Identify the parse error location (line number, character)
2. Look for parentheses, pipes, quotes in that area
3. Simplify the label by removing/replacing special characters
4. Preserve the semantic meaning
5. Ensure all brackets are balanced

Rules:
- Fix syntax errors ONLY
- Preserve diagram structure and meaning
- Do NOT add new features or nodes
- Simplify labels to avoid parser ambiguity
- Use standard Mermaid diagram types only

Output JSON with the following structure:
{
  "mermaid": "string - the fixed Mermaid diagram code"
}
"""


def mermaid_fix_agent(state: GraphState) -> GraphState:
    """
    LangGraph node: Fix Mermaid syntax errors.
    
    This agent:
    1. Reads validation_errors from state
    2. Calls LiteLLM to fix syntax issues
    3. Updates mermaid_code with fixed version
    4. Increments retry_count
    5. Raises RetryExhaustedError if max retries exceeded
    
    Args:
        state: Current graph state
        
    Returns:
        GraphState: Updated state with fixed mermaid_code
        
    Raises:
        RetryExhaustedError: If retry limit exceeded
    """
    config = get_config()
    max_retries = config.max_retry_attempts
    
    logger.start(state, {
        "retry_count": state.get("retry_count", 0),
        "error_count": len(state.get("validation_errors", [])),
    })
    
    try:
        # Check retry count
        retry_count = state.get("retry_count", 0)
        if retry_count >= max_retries:
            raise RetryExhaustedError("mermaid_fix_agent", max_retries)
        
        # Get current Mermaid code and validation errors
        mermaid_code = state.get("mermaid_code", "")
        validation_errors = state.get("validation_errors", [])
        
        if not mermaid_code:
            raise LLMError("No mermaid_code in state")
        
        if not validation_errors:
            raise LLMError("No validation_errors in state")
        
        # Format error messages for the LLM
        error_messages = _format_validation_errors(validation_errors)
        
        # Prepare messages for LiteLLM
        messages = [
            {"role": "system", "content": FIX_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""Fix the following Mermaid diagram:

```mermaid
{mermaid_code}
```

Errors found:
{error_messages}

Return the fixed Mermaid code."""
            },
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
                temperature=0.1,  # Lower temperature for more deterministic fixes
                max_tokens=1500,
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
        
        # Extract fixed Mermaid code
        fixed_mermaid = result["mermaid"]
        
        # Update state
        state["mermaid_code"] = fixed_mermaid
        state["retry_count"] = retry_count + 1
        state["validation_errors"] = None  # Clear errors for re-validation
        
        logger.end(state, {
            "retry_count": state["retry_count"],
            "fixed_length": len(fixed_mermaid),
        })
        
        return state
        
    except RetryExhaustedError:
        logger.error(state, RetryExhaustedError("mermaid_fix_agent", max_retries))
        state["errors"].append(f"Max retries ({max_retries}) exceeded in fix agent")
        raise
    except Exception as e:
        logger.error(state, e)
        state["errors"].append(f"Fix agent failed: {str(e)}")
        raise


def _format_validation_errors(errors: List[Dict[str, Any]]) -> str:
    """
    Format validation errors for LLM consumption.
    
    Args:
        errors: List of validation error dictionaries
        
    Returns:
        str: Formatted error messages
    """
    if not errors:
        return "No specific errors provided"
    
    formatted = []
    for i, error in enumerate(errors, 1):
        error_type = error.get("type", "Unknown")
        message = error.get("message", "No message")
        line = error.get("line", "?")
        formatted.append(f"{i}. [{error_type}] Line {line}: {message}")
    
    return "\n".join(formatted)
