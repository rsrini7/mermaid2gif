# End-to-End Requirement Document

## Project: **Mermaid-GIF (Mermaid → Flow-Animated GIF Automation)**

**Version:** **5.0 (Final, Guardrail-Augmented)**
**Status:** **Approved – Build Contract Locked**
**Execution Model:** Agentic (LangGraph Directed Cyclic Graph)
**Runtime:** Headless, deterministic, containerized

---

## 0. Implementation Guardrails (MANDATORY PREAMBLE)

These guardrails are **binding** and exist to ensure that AI-generated code is robust, testable, and production-safe.

### Guardrail 1: Secret Management Strategy

* All secrets **must not** be hardcoded.
* Configuration **must** be handled using **Pydantic Settings** (`pydantic-settings`).
* The IDE **must generate**:

  * `src/core/config.py`
  * `.env.example`

**Requirements**

* Secrets are loaded from environment variables or `.env`.
* Strict validation is enforced at startup.

**Example constraints**

* `OPENROUTER_API_KEY`:

  * Required
  * Type: `str`
  * Must start with `sk-or-`
* Chromium executable paths, FFmpeg paths, and timeouts must be configurable.

Failure to load valid configuration must result in **immediate process termination**.

---

### Guardrail 2: Mock-First Testing Requirement

* The IDE **must generate mocks** before real integrations.

**Mandatory Mocks**

* LiteLLM client (LLM calls)
* Playwright browser/page/context

**Testing Rules**

* The default **smoke test** must:

  * Run the LangGraph end-to-end
  * Use mocks only
  * Validate graph routing, retries, and terminal states
* No real:

  * API calls
  * Chromium launches
  * FFmpeg executions

Real integrations are allowed **only** in explicit integration tests.

---

### Guardrail 3: Structured Logging Schema

All logs must follow this **strict schema**:

```python
{
  "timestamp": "ISO8601",
  "node": "node_name",
  "event": "START | END | ERROR",
  "state_hash": "sha256(serialized_state)",
  "metadata": {}
}
```

**Rules**

* Logs must be JSON-serializable.
* Every LangGraph node **must emit**:

  * START log
  * END or ERROR log
* No free-form logging is allowed.

---

## 1. Objective

Build a **fully autonomous system** that converts:

> **Natural language or Mermaid input → draw.io flow-animated diagram → clean looping GIF**

The system must:

* Run fully headless (CI-safe)
* Require zero manual interaction
* Produce deterministic output
* Isolate volatile browser logic
* Enforce bounded retries

---

## 2. Architectural Principles (Binding)

1. **LangGraph is mandatory**
   Required for bounded retries, conditional routing, and state persistence.

2. **Strict separation of concerns**

   * LLMs → intent, correction, planning
   * Deterministic code → parsing, rendering, capture, encoding

3. **Pure Mermaid Rendering**

   * No external rendering services (like Draw.io)
   * All rendering via local `mermaid.js` execution

4. **Renderer volatility must be isolated**

   * All rendering happens in a controlled, invisible browser context

5. **Looping correctness supersedes visual fidelity**

   * A clean looping GIF is more important than animation purity

---

## 3. System Architecture Overview

The system is implemented as a **Directed Cyclic Graph (DCG)** using LangGraph.

```
Input
  ↓
Intent & Mermaid Agent
  ↓
Mermaid Validator
  ↓ (invalid)
Mermaid Fix Agent ──┐
  ↓ (valid)         │
Animation Planner   │
  ↓                 │
Mermaid Renderer ←──┘
  ↓
Animation Applicator
  ↓
Capture Controller
  ↓
FFmpeg Transcoder
  ↓
Final Output
```

Retries are **node-local and bounded**.

---

## 4. Technology Stack (Final)

| Layer            | Technology                        |
| ---------------- | --------------------------------- |
| Orchestration    | LangGraph                         |
| LLM Interface    | LiteLLM                           |
| LLM Provider     | Groq, OpenRouter (Optional)       |
| Mermaid Parsing  | `mermaid-parser-py`               |
| Rendering Engine | Native Mermaid.js (via Playwright)  |
| Browser Control  | Playwright (Python, Chromium)     |
| Media Processing | FFmpeg (`ffmpeg-python`)          |
| Config           | Pydantic Settings                 |
| Runtime          | Docker (Python 3.11 + Node.js 20) |

---

## 5. Repository Structure (Enforced)

```text
mermaid-gif/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── fixer.py
│   │   └── intent.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── graph.py
│   │   └── state.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── animation_applicator.py
│   │   ├── capture_controller.py
│   │   ├── ffmpeg_processor.py
│   │   ├── mermaid_renderer.py
│   │   ├── mermaid_validator.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logger.py
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── mocks/
│   ├── __init__.py
│   └── test_smoke.py
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## 6. Canonical LangGraph State

All nodes **must read/write exclusively** through this state.

```python
class GraphState(TypedDict):
    raw_input: str
    raw_input_type: str
    mermaid_code: Optional[str]
    animation_manifest: Optional[Dict[str, Any]]
    validation_errors: Optional[List[Dict[str, Any]]]
    diagram_rendered: bool
    animation_applied: bool
    video_path: Optional[str]
    gif_path: Optional[str]
    errors: List[str]
    artifacts: Dict[str, Any]
    retry_count: int
```

---

## 7. Node Specifications (Final)

### 7.1 Input Router Node

* Determines Mermaid vs text input
* Deterministic logic only
* No LLM usage

---

### 7.2 Intent & Mermaid Generation Agent

* Converts text → Mermaid
* Produces animation manifest
* Restricted to a **safe Mermaid subset**

  * Flowcharts
  * Simple sequences

---

### 7.3 Mermaid Validator Node

**Library:** `mermaid-parser-py`

* Parses Mermaid into structured representation
* Detects syntax and structural errors
* No auto-fixing
* No rendering assumptions

---

### 7.4 Mermaid Fix Agent

* Repairs syntax only
* Max 2 retries
* Exceed → terminal failure

---

### 7.5 Animation Planner Node

* Deterministic normalization of animation settings
* No LLM usage

---

### 7.6 Mermaid Renderer Node (Critical)

**Rendering Strategy**

* Use **Playwright** with local HTML shell
* Inject `mermaid.min.js` from CDN
* Render to SVG via `mermaid.render()`

**Rules**

* Use `page.set_content()`
* Wait for `mermaid` object
* Capture SVG output directly
* No external service dependencies

---

### 7.7 Animation Applicator Node

* Access `mxGraph`
* Apply `flowAnimation=1`
* Idempotent execution
* Layout stabilization before mutation

---

### 7.8 Capture Controller Node (Loop Safety)

**Directive-Driven**

* Force animation duration to frame-aligned multiples
* Capture exact duration
* No time guessing

---

### 7.9 FFmpeg Transcoder Node

* Palette-based GIF generation
* Enforce seamless looping
* Optional boomerang/crossfade stabilization

---

### 7.10 Final Output Node

* Validate GIF integrity
* Attach artifacts
* Emit success metadata

---

## 8. Node Isolation (Directive C)

* `mermaid-parser-py` must run:

  * In a subprocess or isolated thread
* Node.js startup latency must not block the graph

---

## 9. Error Handling & Recovery

| Failure             | Action               |
| ------------------- | -------------------- |
| Mermaid parse error | Fix loop             |
| Import failure      | Renderer retry       |
| Animation missing   | Reapply              |
| Loop imperfect      | FFmpeg stabilization |
| Retry exhausted     | Terminal failure     |

---

## 10. Determinism & Reproducibility

* Fixed Chromium version
* Fixed viewport
* Fixed animation duration
* Fixed FFmpeg filters
* Dockerized runtime

---

## 11. Security Constraints

* No external service dependencies (except CDN)
* No persistent browser state
* No user sessions or logins
* Strict secret handling via environment

---

## 12. Testing Requirements (Expanded)

* Mock-only smoke test required
* Graph routing validated without real IO
* Integration tests explicitly separated

---

## 13. Deliverables (Mandatory)

1. LangGraph `graph.py`
2. All node implementations
3. Pydantic config + `.env.example`
4. Dockerfile
5. Mock-first tests
6. Sample GIF outputs
7. CI-safe smoke test

---

## 14. Completion Criteria

The system is complete when:

* ✅ Fully headless
* ✅ Perfectly looping GIF
* ✅ No external rendering dependencies
* ✅ Bounded retries enforced
* ✅ Logs conform to schema
* ✅ Same input → same output
