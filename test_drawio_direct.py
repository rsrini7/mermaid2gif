"""
Quick test to verify Draw.io loading behavior
"""
import asyncio
from playwright.async_api import async_playwright

async def test_drawio():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        page = await browser.new_page()
        
        # Navigate to Draw.io embed
        url = "https://embed.diagrams.net/?embed=1&proto=json&configure=1&chrome=0&ui=min"
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="networkidle")
        
        # Wait to observe the loading screen
        print("Waiting 5 seconds to observe loading screen...")
        await asyncio.sleep(5)
        
        # Try to send configure message to iframe
        result = await page.evaluate("""
        () => {
            const iframe = document.querySelector('iframe');
            if (iframe && iframe.contentWindow) {
                console.log("Found iframe, sending configure to contentWindow");
                iframe.contentWindow.postMessage(JSON.stringify({
                    action: 'configure',
                    config: { css: '' }
                }), '*');
                return "Sent to iframe";
            } else {
                console.log("No iframe found, sending to window");
                window.postMessage(JSON.stringify({
                    action: 'configure',
                    config: { css: '' }
                }), '*');
                return "Sent to window";
            }
        }
        """)
        print(f"Result: {result}")
        
        # Wait to see if it clears
        print("Waiting 5 more seconds...")
        await asyncio.sleep(5)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_drawio())
