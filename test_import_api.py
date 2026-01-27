"""
Test Draw.io with proper importData API for Mermaid
"""
import asyncio
from playwright.async_api import async_playwright

async def test_drawio_import():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        url = "https://embed.diagrams.net/?embed=1&proto=json"
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="networkidle")
        
        print("Waiting for Draw.io to initialize...")
        await asyncio.sleep(3)
        
        # Try to use Draw.io's importData function directly
        mermaid_code = """graph TD
    A[Start] --> B[Process]
    B --> C[End]"""
        
        print("Attempting to import Mermaid using App.importData...")
        result = await page.evaluate(f"""
            async (code) => {{
                // Wait for App to be available
                let attempts = 0;
                while (typeof App === 'undefined' && attempts < 50) {{
                    await new Promise(r => setTimeout(r, 100));
                    attempts++;
                }}
                
                if (typeof App === 'undefined') {{
                    return {{ success: false, error: 'App not found' }};
                }}
                
                try {{
                    // Try to import as Mermaid
                    await App.importData(code, 'mermaid');
                    return {{ success: true, method: 'App.importData' }};
                }} catch (e) {{
                    return {{ success: false, error: e.toString(), method: 'App.importData' }};
                }}
            }}
        """, mermaid_code)
        
        print(f"Import result: {result}")
        
        await asyncio.sleep(3)
        
        # Check if diagram rendered
        svg_in_canvas = await page.evaluate("""
            () => {
                const canvas = document.querySelector('.geDiagramContainer');
                if (canvas) {
                    return canvas.querySelectorAll('svg').length;
                }
                return 0;
            }
        """)
        
        print(f"SVG elements in diagram canvas: {svg_in_canvas}")
        
        # Check for any mxGraph
        has_graph = await page.evaluate("""
            () => {
                return typeof mxGraph !== 'undefined';
            }
        """)
        
        print(f"mxGraph available: {has_graph}")
        
        print("\nKeeping browser open for 15 seconds for inspection...")
        await asyncio.sleep(15)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_drawio_import())
