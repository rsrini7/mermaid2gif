"""
Test all Draw.io URLs mentioned in the approaches document
to see which ones actually work in a real browser
"""
import asyncio
from playwright.async_api import async_playwright

URLS_TO_TEST = [
    {
        "name": "Basic (Approach 5)",
        "url": "https://embed.diagrams.net/?embed=1&proto=json"
    },
    {
        "name": "Simple UI",
        "url": "https://embed.diagrams.net/?embed=1&ui=simple&proto=json&modified=0&libraries=1&saveAndExit=0&noSaveBtn=1&noExitBtn=1"
    },
    {
        "name": "Min UI with configure (Approach 4)",
        "url": "https://embed.diagrams.net/?embed=1&ui=min&spin=1&proto=json&configure=1"
    },
    {
        "name": "Atlas UI (Approach 9)",
        "url": "https://embed.diagrams.net/?embed=1&ui=atlas&spin=1&modified=unsavedChanges&proto=json&configure=1&chrome=0"
    }
]

async def test_all_urls():
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
        
        results = []
        
        for url_info in URLS_TO_TEST:
            print(f"\n{'='*80}")
            print(f"Testing: {url_info['name']}")
            print(f"URL: {url_info['url']}")
            print('='*80)
            
            # Navigate to URL
            await page.goto(url_info['url'], wait_until="networkidle")
            await asyncio.sleep(3)
            
            # Check what loaded
            page_info = await page.evaluate("""
                () => {
                    return {
                        title: document.title,
                        hasLoadingScreen: document.body.innerText.includes('Loading'),
                        hasJavaScriptWarning: document.body.innerText.includes('JavaScript'),
                        bodyText: document.body.innerText.substring(0, 200),
                        svgCount: document.querySelectorAll('svg').length,
                        hasCanvas: !!document.querySelector('.geDiagramContainer'),
                        hasToolbar: !!document.querySelector('.geToolbarContainer'),
                        mxGraphAvailable: typeof mxGraph !== 'undefined',
                        AppAvailable: typeof App !== 'undefined'
                    };
                }
            """)
            
            print(f"\nPage Info:")
            print(f"  Title: {page_info['title']}")
            print(f"  Has Loading Screen: {page_info['hasLoadingScreen']}")
            print(f"  Has JS Warning: {page_info['hasJavaScriptWarning']}")
            print(f"  SVG Count: {page_info['svgCount']}")
            print(f"  Has Canvas: {page_info['hasCanvas']}")
            print(f"  Has Toolbar: {page_info['hasToolbar']}")
            print(f"  mxGraph Available: {page_info['mxGraphAvailable']}")
            print(f"  App Available: {page_info['AppAvailable']}")
            print(f"  Body Text Preview: {page_info['bodyText'][:100]}...")
            
            # Take screenshot
            screenshot_name = f"url_test_{url_info['name'].replace(' ', '_').lower()}.png"
            await page.screenshot(path=screenshot_name)
            print(f"  Screenshot: {screenshot_name}")
            
            results.append({
                "name": url_info['name'],
                "url": url_info['url'],
                "info": page_info
            })
            
            # Wait a bit before next test
            await asyncio.sleep(2)
        
        print(f"\n\n{'='*80}")
        print("SUMMARY")
        print('='*80)
        
        for result in results:
            status = "WORKS" if result['info']['hasCanvas'] and not result['info']['hasLoadingScreen'] else "FAILED"
            print(f"\n{result['name']}: [{status}]")
            print(f"  - Canvas: {result['info']['hasCanvas']}")
            print(f"  - Loading: {result['info']['hasLoadingScreen']}")
            print(f"  - mxGraph: {result['info']['mxGraphAvailable']}")
        
        print("\n\nKeeping browser open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_all_urls())
