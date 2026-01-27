"""
Test Draw.io using insights from React implementation
Key changes:
1. Listen for BOTH 'init' AND 'configure' events
2. Use ui=atlas instead of ui=min
3. Implement timeout fallback
4. Test with proper Draw.io XML
"""
import asyncio
from playwright.async_api import async_playwright

async def test_react_approach():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        
        # Use ui=atlas as in React code
        url = "https://embed.diagrams.net/?embed=1&ui=atlas&spin=1&modified=unsavedChanges&proto=json&configure=1"
        print(f"Loading: {url}")
        await page.goto(url, wait_until="networkidle")
        
        # Setup message listener that handles BOTH init and configure
        print("\nSetting up message listener...")
        init_result = await page.evaluate("""
            () => {
                return new Promise((resolve) => {
                    let initialized = false;
                    const messages = [];
                    
                    const handler = (event) => {
                        if (event.origin !== 'https://embed.diagrams.net') return;
                        
                        try {
                            const message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
                            console.log('Received:', message);
                            messages.push(message);
                            
                            // CRITICAL: Accept BOTH 'init' AND 'configure' as initialization
                            if (message.event === 'init' || message.event === 'configure') {
                                console.log('Draw.io initialized via:', message.event);
                                initialized = true;
                                window.removeEventListener('message', handler);
                                resolve({ success: true, event: message.event, messages });
                            }
                        } catch (e) {
                            console.error('Parse error:', e);
                        }
                    };
                    
                    window.addEventListener('message', handler);
                    
                    // Timeout fallback (like React code)
                    setTimeout(() => {
                        if (!initialized) {
                            console.warn('Init timeout - forcing load');
                            window.removeEventListener('message', handler);
                            resolve({ success: false, timeout: true, messages });
                        }
                    }, 5000);
                });
            }
        """)
        
        print(f"Init result: {init_result}")
        
        if init_result.get('success'):
            print(f"\n[SUCCESS] Initialization successful via '{init_result.get('event')}' event!")
            
            # Now try to load a diagram
            print("\nLoading diagram...")
            
            # Use proper Draw.io XML format (from React code's getEmptyDiagram)
            diagram_xml = """<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="embed.diagrams.net" modified="2024-01-27T00:00:00.000Z" agent="TestAgent" version="21.0.0" etag="" type="embed">
  <diagram name="Test" id="test">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="2" value="Hello World" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
          <mxGeometry x="200" y="150" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="3" value="Test Node" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="1">
          <mxGeometry x="200" y="250" width="120" height="60" as="geometry"/>
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
                        autosave: 1
                    }}), '*');
                }}
            """, diagram_xml)
            
            await asyncio.sleep(3)
            
            # Check if diagram rendered
            canvas_check = await page.evaluate("""
                () => {
                    const canvas = document.querySelector('.geDiagramContainer');
                    if (canvas) {
                        const rects = canvas.querySelectorAll('rect');
                        const texts = canvas.querySelectorAll('text');
                        return {
                            found: true,
                            rects: rects.length,
                            texts: texts.length,
                            hasContent: rects.length > 0 || texts.length > 0
                        };
                    }
                    return { found: false };
                }
            """)
            
            print(f"\nCanvas check: {canvas_check}")
            
            if canvas_check.get('hasContent'):
                print("[SUCCESS] DIAGRAM RENDERED SUCCESSFULLY!")
            else:
                print("[FAILED] No diagram content found")
            
            # Take screenshot
            await page.screenshot(path="react_approach_test.png")
            print("\nScreenshot: react_approach_test.png")
            
        else:
            print(f"\n[FAILED] Initialization failed: {init_result}")
        
        print("\nKeeping browser open for 20 seconds...")
        await asyncio.sleep(20)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_react_approach())
