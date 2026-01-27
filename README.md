# Mermaid-GIF

**Autonomous Mermaid to Flow-Animated GIF Converter**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Mermaid-GIF is a fully autonomous, headless system that converts Mermaid diagrams into flow-animated GIFs. The system uses LangGraph for orchestration, LiteLLM for LLM interactions, and Playwright for browser automation.

**Key Features:**
- 🤖 Fully autonomous (zero manual interaction)
- 🎯 Headless execution (CI-safe)
- 🔄 Deterministic output (same input → same output)
- 🎬 Flow-animated diagrams with seamless looping
- 🛡️ Bounded retries and robust error handling
- 📊 Structured logging for observability

## Architecture

The system is implemented as a **Directed Cyclic Graph (DCG)** using LangGraph:

```
Input → Intent Agent → Validator → Fix Agent ⟲
                          ↓
        Animation Planner → Draw.io Renderer
                          ↓
        Animation Applicator → Capture Controller
                          ↓
        FFmpeg Transcoder → Final Output
```

## Technology Stack

- **Orchestration:** LangGraph
- **LLM Interface:** LiteLLM
- **LLM Provider:** OpenRouter
- **Mermaid Parsing:** mermaid-parser-py
- **Rendering:** Draw.io (embed mode)
- **Browser Control:** Playwright (Chromium)
- **Media Processing:** FFmpeg
- **Configuration:** Pydantic Settings

## Installation

### Prerequisites

- Python 3.11+
- FFmpeg
- Node.js 20+ (for mermaid-parser-py)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mermaid-gif.git
cd mermaid-gif
```

2. Install dependencies:
```bash
pip install -e .
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

## Configuration

All configuration is managed through environment variables or `.env` file:

### Required
- `OPENROUTER_API_KEY`: OpenRouter API key (must start with `sk-or-`)

### Optional
- `LITELLM_MODEL`: LiteLLM model identifier (default: `openrouter/anthropic/claude-3.5-sonnet`)
- `BROWSER_TIMEOUT_MS`: Browser timeout in milliseconds (default: 30000)
- `VIEWPORT_WIDTH`: Browser viewport width (default: 1920)
- `VIEWPORT_HEIGHT`: Browser viewport height (default: 1080)
- `DEFAULT_ANIMATION_DURATION`: Animation duration in seconds (default: 5.0)
- `DEFAULT_FPS`: Frame rate for GIF (default: 30)
- `LOG_LEVEL`: Logging level (default: INFO)
- `STRUCTURED_LOGGING`: Enable JSON logging (default: true)

See `.env.example` for complete configuration options.

## Usage

### Basic Usage

```python
from src.core.state import create_initial_state
from src.core.graph import run_graph

# Create initial state
state = create_initial_state(
    raw_input="Create a flowchart showing user authentication flow",
    input_type="text"
)

# Run the graph
result = run_graph(state)

# Access the output
print(f"GIF created at: {result['gif_path']}")
```

### Using Mermaid Code Directly

```python
mermaid_code = """
graph TD
    A[Start] --> B{Is user logged in?}
    B -->|Yes| C[Show Dashboard]
    B -->|No| D[Show Login]
    D --> E[Authenticate]
    E --> C
"""

state = create_initial_state(
    raw_input=mermaid_code,
    input_type="mermaid"
)

result = run_graph(state)
```

## Project Structure

```
mermaid-gif/
├── config/                      # Configuration files
│   ├── llm_config.yaml         # LLM agent settings
│   └── animation_presets.json  # Animation presets
├── src/
│   ├── agents/                 # LLM-powered agents
│   │   ├── intent.py          # Intent & Mermaid generation
│   │   └── fixer.py           # Mermaid syntax repair
│   ├── core/                   # Core system components
│   │   ├── state.py           # GraphState definition
│   │   ├── graph.py           # LangGraph orchestration
│   │   ├── config.py          # Pydantic Settings
│   │   └── exceptions.py      # Custom exceptions
│   ├── engine/                 # Deterministic nodes
│   │   ├── mermaid_validator.py
│   │   ├── drawio_driver.py
│   │   ├── animation_applicator.py
│   │   ├── capture_controller.py
│   │   └── ffmpeg_processor.py
│   └── utils/
│       └── logger.py          # Structured logging
├── tests/
│   ├── mocks/                 # Mock implementations
│   └── test_graph_smoke.py   # Smoke tests
├── Dockerfile
├── pyproject.toml
└── .env.example
```

## Testing

### Mock-First Smoke Test

```bash
pytest tests/test_graph_smoke.py
```

This test validates:
- Graph routing logic
- Retry mechanisms
- Terminal states
- No real API calls or browser launches

### Integration Tests

```bash
pytest tests/integration/
```

## Development

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/
```

### Logging

All logs follow a strict JSON schema:

```json
{
  "timestamp": "2026-01-27T08:00:00Z",
  "node": "intent_agent",
  "event": "START",
  "state_hash": "abc123...",
  "metadata": {}
}
```

## Critical Constraints

1. **No UI Automation**: Draw.io interaction via JavaScript injection only (`page.evaluate()`)
2. **Headless Only**: No manual interaction required
3. **Bounded Retries**: Maximum 2 retries per fix loop
4. **Strict Validation**: Configuration errors terminate immediately
5. **Deterministic**: Same input always produces same output

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.

## Support

For issues and questions, please open a GitHub issue.
