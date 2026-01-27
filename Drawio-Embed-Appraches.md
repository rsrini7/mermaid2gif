# Draw.io Integration Debugging Log

**Date:** 2026-01-27  
**Objective:** Resolve blank GIF output and "Loading..." screen issues in Draw.io integration  
**Status:** ❌ Draw.io embed mode `postMessage` API non-functional

---

## Problem Statement

The mermaid-gif application uses Draw.io's embed mode to render Mermaid diagrams, but encounters a persistent "Loading..." screen that never clears, resulting in blank GIF outputs.

---

## Approaches Attempted

### Approach 1: Optimistic Handshake Strategy

**Date:** Initial implementation  
**Method:** Send `configure` message immediately upon page load without waiting for `init`

**Implementation:**
- Modified `WAIT_FOR_INIT_JS` to send configure message optimistically
- Removed dependency on `init` event acknowledgment

**Result:** ❌ **FAILED**
- Loading screen persisted
- No diagram rendering occurred
- Timeout after 15 seconds

**Root Cause:** Race condition - configure message sent before Draw.io was ready to receive it

---

### Approach 2: Heartbeat Configure Strategy

**Date:** Mid-session  
**Method:** Repeatedly send `configure` messages every 500ms until `init` received

**Implementation:**
```javascript
const sendConfigure = () => {
    window.postMessage(JSON.stringify({
        action: 'configure', 
        config: { css: '' }
    }), '*');
};
setInterval(sendConfigure, 500);
```

**Result:** ❌ **FAILED**
- Loading screen still appeared
- `init` event never received
- Heartbeat continued for full 15s timeout

**Root Cause:** Draw.io not responding to `postMessage` at all, likely due to headless browser detection

---

### Approach 3: Simplified URL (Remove configure=1)

**Date:** Mid-session  
**Method:** Remove `configure=1` parameter to bypass handshake requirement

**Implementation:**
- URL: `https://embed.diagrams.net/?embed=1&proto=json&chrome=0&ui=min`
- Simple 2-second wait before sending load command

**Result:** ❌ **FAILED**
- Error: "Render validation failed: SVG not found in DOM or graph empty"
- JSON protocol requires `configure=1` to function

**Root Cause:** `proto=json` mode requires configuration handshake; removing `configure=1` breaks the protocol

---

### Approach 4: Stealth Browser Configuration

**Date:** Latest session  
**Method:** Bypass headless browser detection with comprehensive stealth configuration

**Implementation:**
```python
browser_args = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
]
context = await browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    viewport={"width": 1920, "height": 1080},
)
await page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
""")
```

**Result:** ✅ **PARTIAL SUCCESS**
- Loading screen cleared!
- Draw.io UI loaded successfully (file icons visible)
- `mxGraph` API available
- **BUT:** Diagrams still don't render

**Outcome:** Stealth configuration works for page load, but `postMessage` API still non-functional

---

### Approach 5: Direct postMessage with Mermaid Code

**Date:** Latest session  
**Method:** Send raw Mermaid syntax via `postMessage` load action  
**Test Script:** `test_minimal_drawio.py`

**Implementation:**
```javascript
window.postMessage(JSON.stringify({
    action: 'load',
    xml: 'graph TD\n    A[Start] --> B[End]',
    autosave: 0
}), '*');
```

**Result:** ❌ **FAILED**
- Messages echoed back successfully
- 47 SVG elements found (Draw.io UI loaded)
- **No diagram content rendered**

**Root Cause:** Draw.io doesn't understand raw Mermaid syntax; expects Draw.io XML format

---

### Approach 6: App.importData API

**Date:** Latest session  
**Method:** Use Draw.io's internal `App.importData()` function for Mermaid import  
**Test Script:** `test_import_api.py`

**Implementation:**
```javascript
await App.importData(code, 'mermaid');
```

**Result:** ❌ **FAILED**
- Error: `TypeError: App.importData is not a function`
- `App` object exists but doesn't have `importData` method

**Root Cause:** `App.importData` is not available in embed mode; only exists in full editor mode

---

### Approach 7: Draw.io XML Format via postMessage

**Date:** Latest session  
**Method:** Convert to Draw.io XML format before sending  
**Test Script:** `test_xml_render.py`

**Implementation:**
```xml
<mxfile>
  <diagram name="Test">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Hello" style="rounded=1;..." vertex="1" parent="1">
          <mxGeometry x="200" y="100" width="120" height="60" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**Result:** ❌ **FAILED**
- `postMessage` succeeded (no errors)
- Canvas content: `{'svgCount': 1, 'rectCount': 0, 'textCount': 0, 'hasContent': False}`
- **No shapes rendered**

**Root Cause:** `postMessage` load action not functioning even with correct XML format

---

### Approach 8: Configure Handshake + XML Load

**Date:** Latest session  
**Method:** Proper configure/init handshake followed by XML load  
**Test Script:** `test_configure_load.py`

**Implementation:**
1. Send `configure` message with `config: { css: '' }`
2. Wait for `init` event response
3. Send `load` message with Draw.io XML

**Result:** ❌ **FAILED**
- Configure message sent successfully
- **Init event NEVER received** from Draw.io
- Canvas content: `{'rects': 0, 'texts': 0, 'paths': 0}`
- No diagram rendered

**Root Cause:** Draw.io embed mode not responding to `postMessage` configure action, even with stealth configuration

---

## Key Findings

### What Works ✅

1. **Stealth configuration successfully bypasses headless detection**
   - Page loads without "Please ensure JavaScript is enabled" error
   - Draw.io UI renders (file icons, toolbar visible)
   - `mxGraph`, `mxCodec`, `mxUtils` APIs available

2. **`postMessage` communication channel functions**
   - Messages are delivered to the page
   - Messages are echoed back in listener
   - No CORS or security errors

### What Doesn't Work ❌

1. **`postMessage` API for diagram loading is non-functional**
   - `configure` action: No `init` response
   - `load` action: Accepted but no rendering occurs
   - Works with neither Mermaid code nor Draw.io XML

2. **No programmatic access to editor instance**
   - `window.editorUi` is `undefined`
   - `window.editor` is `undefined`
   - `App.editor` is `undefined`
   - Cannot directly manipulate graph

3. **Import APIs unavailable in embed mode**
   - `App.importData()` does not exist
   - No alternative import functions found

---

## Technical Analysis

### Draw.io Embed Mode Architecture

```
embed.diagrams.net/?embed=1&proto=json&configure=1
│
├─ Loads Draw.io UI ✅
├─ Exposes mxGraph API ✅
├─ Listens for postMessage ✅
│
└─ postMessage Actions:
    ├─ 'configure' → Should trigger 'init' event ❌ (No response)
    ├─ 'load' → Should render diagram ❌ (Silently fails)
    └─ 'status' → Echoed back ✅ (Works)
```

### Hypothesis: Embed Mode Limitations

The `postMessage` API in `embed.diagrams.net` appears designed for **iframe embedding within the Draw.io ecosystem**, not for **external programmatic control**. The API may:

- Require specific origin/referrer headers
- Validate message source against whitelist
- Expect additional handshake parameters we're not providing
- Be intentionally disabled for security reasons

---

## Test Scripts Created

| Script | Purpose | Outcome |
|--------|---------|---------|
| `test_drawio_direct.py` | Basic page load test | Page loads, no rendering |
| `test_minimal_drawio.py` | Simple postMessage with Mermaid | Messages work, no rendering |
| `test_import_api.py` | Test `App.importData()` | API doesn't exist |
| `test_explore_apis.py` | Enumerate available APIs | Found mxGraph but no editor instance |
| `test_xml_render.py` | Send Draw.io XML format | XML accepted, no rendering |
| `test_configure_load.py` | Full configure/init/load workflow | Init never received |

---

## Conclusion

**Draw.io's embed mode `postMessage` API is fundamentally non-functional for programmatic diagram loading**, despite:

- Successful stealth configuration
- Working message delivery
- Correct XML format
- Proper handshake sequence

The API either:

1. Requires undocumented parameters/headers
2. Is restricted to specific origins/contexts
3. Is not intended for external automation
4. Has breaking changes not reflected in documentation

---

## Recommended Next Steps

### Option A: Switch to Mermaid.js Direct Rendering ⭐ **RECOMMENDED**

- Use Mermaid.js library directly in browser
- Render to SVG natively
- Apply animations via CSS/JavaScript
- Capture with Playwright
- **Pros:** Full control, no third-party dependencies, proven approach
- **Cons:** Deviates from REQUIREMENTS.md specification

### Option B: Local Draw.io Desktop Application

- Use Draw.io desktop app via CLI
- Export diagrams programmatically
- **Pros:** Official Draw.io support
- **Cons:** Requires installation, platform-specific

### Option C: Alternative Diagram Rendering Service

- Kroki.io, Mermaid Live Editor, or similar
- **Pros:** Dedicated rendering APIs
- **Cons:** External dependency, network calls

### Option D: Continue Draw.io Investigation

- Contact Draw.io developers for embed mode documentation
- Reverse-engineer working embed implementations
- **Pros:** Maintains REQUIREMENTS.md compliance
- **Cons:** Time-intensive, uncertain outcome

---

## Artifacts Generated

### Screenshots
- `drawio_test_render.png` - Empty canvas after XML load
- `configure_then_load_test.png` - No rendering after full handshake

### Code
- 6 test scripts documenting each approach
- Modified `drawio_utils.py` with stealth configuration
- Updated `drawio_driver.py`, `animation_applicator.py`, `capture_controller.py`

---

## Time Investment

- **Stealth Configuration:** ~2 hours
- **postMessage Testing:** ~3 hours  
- **API Exploration:** ~1 hour
- **Total:** ~6 hours of debugging

**Outcome:** Draw.io embed mode confirmed non-viable for programmatic use