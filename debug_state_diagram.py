"""
Debug script to inspect state diagram SVG structure
"""
import asyncio
from playwright.async_api import async_playwright

async def inspect_state_diagram():
    mermaid_code = """
stateDiagram-v2
    [*] --> A
    A --> B
    B --> C
    C --> [*]
"""
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head>
<body>
    <div id="diagram-container"></div>
    <script>
        mermaid.initialize({{
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose'
        }});
        
        async function render() {{
            const {{ svg }} = await mermaid.render('diagram', `{mermaid_code}`);
            document.getElementById('diagram-container').innerHTML = svg;
            
            // Log all path and line elements with their classes
            const paths = document.querySelectorAll('path');
            const lines = document.querySelectorAll('line');
            
            console.log('=== PATHS ===');
            paths.forEach((p, i) => {{
                console.log(`Path ${{i}}: class="${{p.className.baseVal}}" id="${{p.id}}"`);
            }});
            
            console.log('=== LINES ===');
            lines.forEach((l, i) => {{
                console.log(`Line ${{i}}: class="${{l.className.baseVal}}" id="${{l.id}}"`);
            }});
        }}
        
        render();
    </script>
</body>
</html>
"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        page.on('console', lambda msg: print(f"BROWSER: {msg.text}"))
        
        await page.set_content(html)
        await asyncio.sleep(3)
        
        # Get the outer HTML to see structure
        svg_html = await page.evaluate("""
            () => {
                const svg = document.querySelector('svg');
                return svg ? svg.outerHTML : 'NO SVG';
            }
        """)
        
        print("\n=== SVG STRUCTURE ===")
        print(svg_html[:2000])  # First 2000 chars
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_state_diagram())
