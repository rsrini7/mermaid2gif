"""
Shared utilities for Draw.io interactions.

This module centralizes the critical JavaScript injection scripts and constants
required to robustly drive the Draw.io embed mode using the specific 'proto=json'
workflow and 'mxGraph' instance capture technique discovered during debugging.
"""

DRAWIO_URL = "https://embed.diagrams.net/?embed=1&proto=json&spin=1&configure=1"
DRAWIO_BASE_URL = "https://embed.diagrams.net"

# Constants
DEFAULT_TIMEOUT = 30000

# 1. Monkey patch mxGraph.prototype.getModel to capture the instance reliably
#    This hook is called whenever the graph renders, guaranteeing we capture 'this'.
PATCH_MXGRAPH_JS = """
() => {
    if (typeof mxGraph !== 'undefined' && !window.mxGraphPatched) {
        const originalGetModel = mxGraph.prototype.getModel;
        mxGraph.prototype.getModel = function() {
            if (!window.capturedGraph) {
                console.log("Captured graph instance via getModel!");
                window.capturedGraph = this;
            }
            return originalGetModel.apply(this, arguments);
        }
        window.mxGraphPatched = true;
        console.log("mxGraph.prototype.getModel patched successfully");
    } else if (typeof mxGraph === 'undefined') {
        console.warn("mxGraph not defined yet, cannot patch");
    }
}
"""

# 2. Wait for the 'init' message from the iframe
#    This confirms the app is ready to receive configuration.
WAIT_FOR_INIT_JS = """
() => {
    return new Promise(resolve => {
        const handler = (event) => {
            try {
                // Ensure origin matches to prevent security issues (optional but good practice)
                // if (event.origin !== 'https://embed.diagrams.net') return;
                
                const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
                if (data.event === 'init') {
                    console.log('Draw.io Init received!');
                    window.removeEventListener('message', handler);
                    resolve(true);
                }
            } catch (e) {
                // Ignore parse errors from other messages
            }
        };
        window.addEventListener('message', handler);
        // Fallback timeout in case we missed it or it's delayed
        setTimeout(() => {
            window.removeEventListener('message', handler);
            resolve(false); 
        }, 10000);
    });
}
"""

# 3. Send configuration message
SEND_CONFIGURE_JS = """
() => {
    window.postMessage(JSON.stringify({
        action: 'configure', 
        config: { css: '' }
    }), '*');
}
"""

# 4. Send load message with Mermaid XML
#    Takes `mermaid_code` as an argument.
SEND_LOAD_JS = """
(mermaidCode) => {
    window.postMessage(JSON.stringify({
        action: 'load', 
        autosave: 0, 
        xml: mermaidCode
    }), '*');
}
"""

# 5. Check if graph captured and SVG rendered
CHECK_RENDER_JS = """
() => {
    return {
        hasSvg: document.querySelectorAll('svg').length > 0,
        hasCapturedGraph: typeof window.capturedGraph !== 'undefined'
    };
}
"""

# 6. Apply flow animation to edges using captured graph
APPLY_ANIMATION_JS = """
() => {
    try {
        const graph = window.capturedGraph;
        if (!graph) return { success: false, error: "Cloud not find mxGraph instance (window.capturedGraph is undefined)" };
        
        graph.getModel().beginUpdate();
        let edgeCount = 0;
        try {
            const parent = graph.getDefaultParent();
            const children = graph.getChildCells(parent);
            
            for (let i = 0; i < children.length; i++) {
                const cell = children[i];
                if (cell.isEdge()) {
                    // Set flowAnimation=1
                    let style = cell.getStyle();
                    if (!style.includes('flowAnimation=1')) {
                        if (style && style[style.length - 1] !== ';') style += ';';
                        style += 'flowAnimation=1;';
                        graph.getModel().setStyle(cell, style);
                        edgeCount++;
                    }
                }
            }
        } finally {
            graph.getModel().endUpdate();
        }
        
        // Force refresh
        graph.refresh();
        
        return { success: true, edgeCount: edgeCount };
    } catch (error) {
        return { success: false, error: error.message };
    }
}
"""
