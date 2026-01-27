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
                    try {
                        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
                        if (data.event === 'init') {
                            console.log('Init received!');
                            resolve(true);
                        }
                    } catch (e) {
                        // Ignore parse errors from other messages
                    }
                });
                // Timeout fallback
                setTimeout(() => resolve(false), 5000);
            });
        }""")
        
        if not init_received:
            print("WARNING: No init message received. Trying to proceed anyway...")
        
        # Monkey Patch mxGraph.prototype.getModel to capture instance
        print("Monkey-patching mxGraph.prototype.getModel...")
        await page.evaluate("""() => {
            if (typeof mxGraph !== 'undefined') {
                const originalGetModel = mxGraph.prototype.getModel;
                mxGraph.prototype.getModel = function() {
                    if (!window.capturedGraph) {
                        console.log("Captured graph instance via getModel!");
                        window.capturedGraph = this;
                    }
                    return originalGetModel.apply(this, arguments);
                }
                console.log("mxGraph.prototype.getModel patched successfully");
            } else {
                console.error("mxGraph not defined, cannot patch");
            }
        }""")
        
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
        
        # Check for SVG and Captured Graph
        info = await page.evaluate("""() => {
            return {
                hasSvg: document.querySelectorAll('svg').length > 0,
                hasCapturedGraph: typeof window.capturedGraph !== 'undefined',
                graphModel: window.capturedGraph ? window.capturedGraph.getModel().constructor.name : null
            };
        }""")
        print(f"Result: {info}")
        
        import json
        print(json.dumps(info, indent=2))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_drawio())
