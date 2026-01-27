import asyncio
from playwright.async_api import async_playwright

DRAWIO_URL = "https://embed.diagrams.net/?embed=1&proto=json&spin=1&configure=1"

async def debug_drawio():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Setup console logging
        page.on("console", lambda msg: print(f"Page Console: {msg.text}"))
        
        print(f"Navigating to {DRAWIO_URL}...")
        await page.goto(DRAWIO_URL, wait_until="networkidle")
        
        # Inject listener for init message
        print("Waiting for init message...")
        init_received = await page.evaluate("""() => {
            return new Promise(resolve => {
                window.addEventListener('message', (event) => {
                    const data = JSON.parse(event.data);
                    if (data.event === 'init') {
                        console.log('Init received!');
                        resolve(true);
                    }
                });
                // Timeout fallback
                setTimeout(() => resolve(false), 5000);
            });
        }""")
        
        if not init_received:
            print("WARNING: No init message received. Trying to proceed anyway...")
        
        # Send Configure
        print("Sending configure...")
        await page.evaluate("""() => {
             window.postMessage(JSON.stringify({
                action: 'configure', 
                config: { css: '' }
            }), '*');
        }""")
        
        await asyncio.sleep(0.5)
        
        # Send Mermaid Load
        print("Sending load with Mermaid...")
        mermaid_code = "graph TD; A-->B;"
        await page.evaluate(f"""() => {{
            window.postMessage(JSON.stringify({{
                action: 'load', 
                autosave: 0, 
                xml: `{mermaid_code}`
            }}), '*');
        }}""")
        
        # Wait for potential render
        print("Waiting for render...")
        await asyncio.sleep(5)
        
        # Check for SVG
        frame_count = len(page.frames)
        print(f"Frame count: {frame_count}")
        
        has_svg = await page.evaluate("document.querySelectorAll('svg').length > 0")
        print(f"Has SVG in main frame: {has_svg}")
        
        # Inspect Global Scope again
        info = await page.evaluate("""() => {
            const info = {};
            
            if (typeof App !== 'undefined') {
                info.hasMainUi = typeof App.mainUi !== 'undefined';
            }
            
            // Check HeadlessUi
            if (typeof HeadlessEditorUi !== 'undefined') {
                 info.headlessUiMethods = Object.keys(HeadlessEditorUi.prototype);
            }
            
            // Search for graph in frames if main failed
            // (Only works if same origin, but embed is same origin)
            
            return info;
        }""")
        
        import json
        print(json.dumps(info, indent=2))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_drawio())
