"""
Test if configure handshake is required before load works
"""
import asyncio
from playwright.async_api import async_playwright

async def test_configure_then_load():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        
        # Use URL WITH configure=1
        url = "https://embed.diagrams.net/?embed=1&proto=json&configure=1"
        print(f"Loading: {url}")
        await page.goto(url, wait_until="networkidle")
        
        print("Setting up message listener...")
        await page.evaluate("""
            () => {
                window.receivedMessages = [];
                window.addEventListener('message', (event) => {
                    try {
                        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
                        console.log('Received:', data);
                        window.receivedMessages.push(data);
                    } catch (e) {}
                });
            }
        """)
        
        await asyncio.sleep(2)
        
        # Step 1: Send configure and wait for init
        print("\n1. Sending configure message...")
        await page.evaluate("""
            () => {
                window.postMessage(JSON.stringify({
                    action: 'configure',
                    config: { css: '' }
                }), '*');
            }
        """)
        
        await asyncio.sleep(2)
        
        messages = await page.evaluate("() => window.receivedMessages")
        print(f"   Messages after configure: {messages}")
        
        init_received = any(msg.get('event') == 'init' for msg in messages)
        print(f"   Init received: {init_received}")
        
        # Step 2: Now send the load with XML
        print("\n2. Sending load with Draw.io XML...")
        drawio_xml = """<mxfile>
  <diagram name="Test">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Hello World" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="200" y="150" width="120" height="60" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""
        
        await page.evaluate(f"""
            (xml) => {{
                window.postMessage(JSON.stringify({{
                    action: 'load',
                    xml: xml,
                    autosave: 0
                }}), '*');
            }}
        """, drawio_xml)
        
        await asyncio.sleep(3)
        
        # Check if diagram rendered
        canvas_check = await page.evaluate("""
            () => {
                const canvas = document.querySelector('.geDiagramContainer');
                if (canvas) {
                    return {
                        rects: canvas.querySelectorAll('rect').length,
                        texts: canvas.querySelectorAll('text').length,
                        paths: canvas.querySelectorAll('path').length
                    };
                }
                return { error: 'No canvas' };
            }
        """)
        
        print(f"\n3. Canvas content: {canvas_check}")
        
        # Also check for any mxGraph instance
        graph_check = await page.evaluate("""
            () => {
                if (typeof mxGraph !== 'undefined') {
                    // Try to find any graph instance
                    const graphInstances = [];
                    for (let key in window) {
                        try {
                            if (window[key] && window[key].constructor && 
                                window[key].constructor.name === 'mxGraph') {
                                graphInstances.push(key);
                            }
                        } catch (e) {}
                    }
                    return { available: true, instances: graphInstances };
                }
                return { available: false };
            }
        """)
        
        print(f"   mxGraph check: {graph_check}")
        
        # Take screenshot
        await page.screenshot(path="configure_then_load_test.png")
        print("\n   Screenshot: configure_then_load_test.png")
        
        print("\nKeeping browser open for 20 seconds...")
        await asyncio.sleep(20)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_configure_then_load())
