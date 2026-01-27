"""
Test if XML diagram actually renders visually
"""
import asyncio
from playwright.async_api import async_playwright

async def test_xml_rendering():
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
        
        print("Loading Draw.io...")
        await page.goto("https://embed.diagrams.net/?embed=1&proto=json", wait_until="networkidle")
        await asyncio.sleep(3)
        
        # Send a more complete Draw.io XML with multiple shapes
        drawio_xml = """<mxfile host="embed.diagrams.net">
  <diagram name="Test">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Start" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="1">
          <mxGeometry x="200" y="100" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="3" value="Process" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
          <mxGeometry x="200" y="200" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="4" value="End" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;" vertex="1" parent="1">
          <mxGeometry x="200" y="300" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="5" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" edge="1" parent="1" source="2" target="3">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="6" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" edge="1" parent="1" source="3" target="4">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""
        
        print("Sending Draw.io XML via postMessage...")
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
        
        # Take a screenshot to verify
        screenshot_path = "drawio_test_render.png"
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")
        
        # Check canvas content
        canvas_info = await page.evaluate("""
            () => {
                const canvas = document.querySelector('.geDiagramContainer');
                if (canvas) {
                    const svgs = canvas.querySelectorAll('svg');
                    const rects = canvas.querySelectorAll('rect');
                    const texts = canvas.querySelectorAll('text');
                    return {
                        svgCount: svgs.length,
                        rectCount: rects.length,
                        textCount: texts.length,
                        hasContent: rects.length > 0 || texts.length > 0
                    };
                }
                return { error: 'No canvas found' };
            }
        """)
        
        print(f"\nCanvas content: {canvas_info}")
        
        if canvas_info.get('hasContent'):
            print("✅ Diagram rendered successfully!")
        else:
            print("❌ No diagram content found")
        
        print("\nKeeping browser open for 15 seconds for visual inspection...")
        await asyncio.sleep(15)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_xml_rendering())
