"""
Mermaid.js Direct Renderer
Native Mermaid.js rendering module using Playwright
"""

from playwright.async_api import async_playwright, Page, Browser
from ..core.config import get_config
from ..utils.logger import get_logger
from typing import Dict, Any
import asyncio
import nest_asyncio

# Allow nested event loops for LangGraph compatibility
nest_asyncio.apply()

logger = get_logger("mermaid_renderer")


def render_mermaid_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper for async Mermaid rendering.
    Required for LangGraph compatibility.
    """
    return asyncio.run(_render_mermaid_async(state))


async def _render_mermaid_async(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Render Mermaid code to SVG using Mermaid.js library.
    
    Args:
        state: Graph state containing mermaid_code
        
    Returns:
        Updated state with render_html artifact
    """
    mermaid_code = state.get("mermaid_code", "")
    
    if not mermaid_code:
        raise ValueError("No mermaid_code found in state")
    
    logger.info("Starting Mermaid.js rendering", metadata={
        "code_length": len(mermaid_code),
        "code_preview": mermaid_code[:100]
    })
    
    renderer = MermaidRenderer()
    try:
        render_html = await renderer.render(mermaid_code)
        
        # Store in artifacts
        if "artifacts" not in state:
            state["artifacts"] = {}
        state["artifacts"]["render_html"] = render_html
        
        # Set flag to indicate successful rendering
        state["diagram_rendered"] = True
        
        logger.info("Mermaid rendering completed", metadata={
            "html_size": len(render_html)
        })
        
        return state
        
    except Exception as e:
        logger.error(state, e, metadata={
            "component": "mermaid_renderer"
        })
        raise


class MermaidRenderer:
    """Renders Mermaid diagrams to SVG using Playwright and Mermaid.js CDN"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("mermaid_renderer")
    
    async def render(self, mermaid_code: str) -> str:
        """
        Render Mermaid code to full HTML with embedded SVG.
        
        Args:
            mermaid_code: Mermaid diagram syntax
            
        Returns:
            Full HTML document with rendered SVG
        """
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ]
            )
            
            try:
                # Use wide viewport to allow LR diagrams to render at full resolution
                page = await browser.new_page(
                    viewport={"width": 4000, "height": 3000}
                )
                
                # Create HTML shell with Mermaid.js
                html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mermaid Diagram</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: white;
        }}
        #diagram-container {{
            /* Removed max-width constraint to allow wide diagrams */
        }}
    </style>
</head>
<body>
    <div id="diagram-container"></div>
</body>
</html>
"""
                
                self.logger.info("Loading Mermaid.js library")
                await page.set_content(html_template)
                
                # Wait for Mermaid.js to load
                await page.wait_for_function("typeof mermaid !== 'undefined'")
                
                self.logger.info("Rendering Mermaid diagram")
                
                # Render Mermaid code to SVG
                svg_result = await page.evaluate(f"""
                    async (code) => {{
                        try {{
                            // Initialize Mermaid with configuration
                            mermaid.initialize({{
                                startOnLoad: false,
                                theme: 'default',
                                securityLevel: 'loose',
                                flowchart: {{
                                    useMaxWidth: false,  // Allow diagrams to render at natural width
                                    htmlLabels: true
                                }}
                            }});
                            
                            // Render the diagram
                            const {{ svg }} = await mermaid.render('mermaid-diagram', code);
                            
                            // Insert into container
                            document.getElementById('diagram-container').innerHTML = svg;
                            
                            return {{ success: true, svg: svg }};
                        }} catch (error) {{
                            return {{ success: false, error: error.toString() }};
                        }}
                    }}
                """, mermaid_code)
                
                if not svg_result.get("success"):
                    error_msg = svg_result.get("error", "Unknown error")
                    raise RuntimeError(f"Mermaid rendering failed: {error_msg}")
                
                self.logger.info("Mermaid diagram rendered successfully")
                
                # Get the full HTML with rendered SVG
                full_html = await page.content()
                
                return full_html
                
            finally:
                await browser.close()
