"""
Test diagram loading with the WORKING URLs (without configure=1)
"""
import asyncio
from playwright.async_api import async_playwright

async def test_working_url():
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
        
        # Use the WORKING URL (without configure=1)
        url = "https://embed.diagrams.net/?embed=1&proto=json"
        print(f"Loading: {url}")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(3)
        
        print("\n[SUCCESS] Page loaded! Now trying to load a diagram...")
        
        # Try loading a simple diagram with postMessage
        diagram_xml = """<mxfile>
  <diagram name="Test">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
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
                    autosave: 0
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
                    const allText = Array.from(texts).map(t => t.textContent).join(', ');
                    return {
                        found: true,
                        rects: rects.length,
                        texts: texts.length,
                        textContent: allText,
                        hasContent: rects.length > 5 || texts.length > 0
                    };
                }
                return { found: false };
            }
        """)
        
        print(f"\nCanvas check: {canvas_check}")
        
        if canvas_check.get('hasContent'):
            print("\n[SUCCESS] DIAGRAM RENDERED!")
            print(f"Text found: {canvas_check.get('textContent')}")
        else:
            print("\n[FAILED] No diagram content")
        
        # Take screenshot
        await page.screenshot(path="working_url_test.png")
        print("\nScreenshot: working_url_test.png")
        
        print("\nKeeping browser open for 20 seconds...")
        await asyncio.sleep(20)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_working_url())
