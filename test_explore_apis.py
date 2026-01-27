"""
Explore what APIs are actually available in Draw.io embed mode
"""
import asyncio
from playwright.async_api import async_playwright

async def explore_drawio_apis():
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
        
        # Explore available globals
        apis = await page.evaluate("""
            () => {
                const result = {
                    App: typeof App !== 'undefined' ? Object.keys(App).slice(0, 20) : null,
                    EditorUi: typeof EditorUi !== 'undefined',
                    mxGraph: typeof mxGraph !== 'undefined',
                    mxCell: typeof mxCell !== 'undefined',
                    mxCodec: typeof mxCodec !== 'undefined',
                    mxUtils: typeof mxUtils !== 'undefined'
                };
                
                // Try to find the editor instance
                if (typeof EditorUi !== 'undefined') {
                    result.editorUiMethods = Object.getOwnPropertyNames(EditorUi.prototype).slice(0, 30);
                }
                
                return result;
            }
        """)
        
        print("\nAvailable APIs:")
        for key, value in apis.items():
            print(f"  {key}: {value}")
        
        # Try to access the actual editor instance
        editor_info = await page.evaluate("""
            () => {
                // Common ways to access the editor
                const checks = {
                    'window.editorUi': typeof window.editorUi !== 'undefined',
                    'window.editor': typeof window.editor !== 'undefined',
                    'App.editor': typeof App !== 'undefined' && typeof App.editor !== 'undefined',
                };
                
                // Try to find graph instance
                if (window.editorUi && window.editorUi.editor) {
                    checks.hasGraph = typeof window.editorUi.editor.graph !== 'undefined';
                }
                
                return checks;
            }
        """)
        
        print("\nEditor instance checks:")
        for key, value in editor_info.items():
            print(f"  {key}: {value}")
        
        # Check if we can insert XML directly
        print("\nTrying to insert simple XML diagram...")
        simple_xml = """<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="2" value="Hello" style="rounded=1;whiteSpace=wrap;" vertex="1" parent="1">
      <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>"""
        
        xml_result = await page.evaluate(f"""
            (xml) => {{
                try {{
                    // Try postMessage with XML
                    window.postMessage(JSON.stringify({{
                        action: 'load',
                        xml: xml,
                        autosave: 0
                    }}), '*');
                    return {{ success: true, method: 'postMessage-xml' }};
                }} catch (e) {{
                    return {{ success: false, error: e.toString() }};
                }}
            }}
        """, simple_xml)
        
        print(f"XML insert result: {xml_result}")
        
        print("\nKeeping browser open for 20 seconds...")
        await asyncio.sleep(20)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_drawio_apis())
