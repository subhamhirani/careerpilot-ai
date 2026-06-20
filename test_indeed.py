from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080}
    )
    
    print('Navigating to Indeed India...')
    page.goto('https://in.indeed.com/jobs?q=software+engineer&l=India&sort=date', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(3000)
    
    print('URL:', page.url)
    print('Title:', page.title())
    
    page_text = page.content()
    print('Page length:', len(page_text))
    
    if 'captcha' in page_text.lower():
        print('BLOCKED: Captcha detected')
    elif 'verify' in page_text.lower()[:500]:
        print('BLOCKED: Verification page')
    else:
        cards = page.query_selector_all('div.job_seen_beacon')
        if not cards:
            cards = page.query_selector_all('div[data-testid="job-card"]')
        if not cards:
            cards = page.query_selector_all('div.jobCard')
        
        print('Job cards found:', len(cards))
        
        json_ld_scripts = page.query_selector_all('script[type="application/ld+json"]')
        print('JSON-LD blocks:', len(json_ld_scripts))
        
        if json_ld_scripts:
            for script in json_ld_scripts[:5]:
                content = script.inner_text()
                try:
                    data = json.loads(content)
                    if data.get('@type') == 'JobPosting':
                        org = data.get('hiringOrganization', {})
                        org_name = org.get('name', '') if isinstance(org, dict) else org
                        print('  Job:', data.get('title', 'N/A'), '@', org_name)
                    elif data.get('@type') == 'ItemList':
                        items = data.get('itemListElement', [])
                        print('  ItemList with', len(items), 'items')
                        for item in items[:3]:
                            name = item.get('name', item.get('item', {}).get('name', 'N/A'))
                            print('   ', name)
                except:
                    pass
        
        if cards:
            for card in cards[:5]:
                title = card.query_selector('h2.jobTitle a, a[data-testid="job-card-title"], a[class*="title"]')
                company = card.query_selector('span[data-testid="company-name"], span.companyName')
                location = card.query_selector('div[data-testid="job-card-location"]')
                t = title.inner_text() if title else 'N/A'
                c = company.inner_text() if company else 'N/A'
                loc = location.inner_text() if location else 'N/A'
                print('  ', t, '@', c, '|', loc)
        
        if not cards and not json_ld_scripts:
            print('No data found. Checking page structure...')
            body = page.evaluate('document.body.innerText.substring(0, 500)')
            print('Body preview:', body[:300])
    
    browser.close()
