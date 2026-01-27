"""
Minimal test of Draw.io postMessage workflow
Using only: https://embed.diagrams.net/?embed=1&proto=json
"""
import asyncio
from playwright.async_api import async_playwright

async def test_minimal_drawio():
    async with async_playwright() as p:
        # Launch with stealth configuration
        browser = await p.chromium.launch(
            headless=False,  # Visible so you can see what's happening
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
        
        # Navigate to minimal URL
        url = "https://embed.diagrams.net/?embed=1&proto=json"
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="networkidle")
        
        # Wait a bit for page to stabilize
        print("Waiting 3 seconds for page to load...")
        await asyncio.sleep(3)
        
        # Listen for messages from Draw.io
        messages_received = []
        
        await page.evaluate("""
            () => {
                window.drawioMessages = [];
                window.addEventListener('message', (event) => {
                    try {
                        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
                        console.log('Received message:', data);
                        window.drawioMessages.push(data);
                    } catch (e) {
                        console.log('Non-JSON message:', event.data);
                    }
                });
            }
        """)
        
        # Send a simple test message
        print("Sending test postMessage...")
        await page.evaluate("""
            () => {
                window.postMessage(JSON.stringify({
                    action: 'status'
                }), '*');
            }
        """)
        
        await asyncio.sleep(2)
        
        # Check what messages we received
        messages = await page.evaluate("() => window.drawioMessages")
        print(f"Messages received: {messages}")
        
        # Try sending a simple diagram
        print("\nSending simple Mermaid diagram...")
        mermaid_code = """graph TD
    A[Start] --> B[End]"""
        
        await page.evaluate(f"""
            (code) => {{
                window.postMessage(JSON.stringify({{
                    action: 'load',
                    xml: code,
                    autosave: 0
                }}), '*');
            }}
        """, mermaid_code)
        
        await asyncio.sleep(5)
        
        # Check if anything rendered
        svg_count = await page.evaluate("() => document.querySelectorAll('svg').length")
        print(f"\nSVG elements found: {svg_count}")
        
        # Check messages again
        messages = await page.evaluate("() => window.drawioMessages")
        print(f"All messages received: {messages}")
        
        print("\nKeeping browser open for 10 seconds for manual inspection...")
        await asyncio.sleep(10)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_minimal_drawio())
