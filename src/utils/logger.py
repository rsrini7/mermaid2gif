"""
Structured logging for Mermaid2GIF system.

All logs follow a strict JSON schema for observability and debugging.
Every LangGraph node must emit START and END/ERROR logs.
"""

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..core.state import GraphState


# ============================================
# Log Schema
# ============================================

class StructuredLogger:
    """
    Structured logger that enforces the canonical log schema.
    
    Schema:
    {
        "timestamp": "ISO8601",
        "node": "node_name",
        "event": "START | END | ERROR",
        "state_hash": "sha256(serialized_state)",
        "metadata": {}
    }
    """
    
    def __init__(self, node_name: str, enable_structured: bool = True):
        """
        Initialize structured logger for a specific node.
        
        Args:
            node_name: Name of the LangGraph node
            enable_structured: Whether to use structured JSON logging
        """
        self.node_name = node_name
        self.enable_structured = enable_structured
        self.logger = logging.getLogger(f"mermaid_gif.{node_name}")
    
    def _compute_state_hash(self, state: GraphState) -> str:
        """
        Compute SHA256 hash of serialized state.
        
        Args:
            state: Current graph state
            
        Returns:
            str: Hexadecimal hash string
        """
        # Serialize state to JSON (sorted keys for determinism)
        state_json = json.dumps(state, sort_keys=True, default=str)
        # Compute SHA256 hash
        return hashlib.sha256(state_json.encode()).hexdigest()
    
    def _emit_log(
        self,
        event: str,
        state: Optional[GraphState] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: int = logging.INFO,
    ) -> None:
        """
        Emit a structured log entry.
        
        Args:
            event: Event type (START, END, ERROR)
            state: Current graph state (optional)
            metadata: Additional metadata (optional)
            level: Log level
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": self.node_name,
            "event": event,
            "state_hash": self._compute_state_hash(state) if state else None,
            "metadata": metadata or {},
        }
        
        if self.enable_structured:
            # Emit as JSON
            self.logger.log(level, json.dumps(log_entry))
        else:
            # Emit as human-readable format
            msg = f"[{event}] {self.node_name}"
            if metadata:
                msg += f" | {metadata}"
            self.logger.log(level, msg)
    
    def start(self, state: GraphState, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log node start event.
        
        Args:
            state: Current graph state
            metadata: Additional metadata
        """
        self._emit_log("START", state, metadata, logging.INFO)
    
    def end(self, state: GraphState, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log node end event.
        
        Args:
            state: Current graph state
            metadata: Additional metadata
        """
        self._emit_log("END", state, metadata, logging.INFO)
    
    def error(
        self,
        state: GraphState,
        error: Exception,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log node error event.
        
        Args:
            state: Current graph state
            error: Exception that occurred
            metadata: Additional metadata
        """
        error_metadata = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(metadata or {}),
        }
        self._emit_log("ERROR", state, error_metadata, logging.ERROR)

    def info(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log general info message.
        
        Args:
            message: Information message
            metadata: Additional metadata
        """
        self._emit_log("INFO", None, {"message": message, **(metadata or {})}, logging.INFO)

    def warning(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log warning message.
        
        Args:
            message: Warning message
            metadata: Additional metadata
        """
        self._emit_log("WARNING", None, {"message": message, **(metadata or {})}, logging.WARNING)


# ============================================
# Logger Configuration
# ============================================

def configure_logging(log_level: str = "INFO", structured: bool = True) -> None:
    """
    Configure global logging settings.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Whether to use structured JSON logging
    """
    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s" if structured else "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    
    # Suppress noisy third-party loggers
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(node_name: str, enable_structured: bool = True) -> StructuredLogger:
    """
    Get a structured logger for a specific node.
    
    Args:
        node_name: Name of the LangGraph node
        enable_structured: Whether to use structured JSON logging
        
    Returns:
        StructuredLogger: Configured logger instance
    """
    return StructuredLogger(node_name, enable_structured)
