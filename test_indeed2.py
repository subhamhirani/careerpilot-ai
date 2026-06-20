from playwright.sync_api import sync_playwright
import json, time

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        locale='en-IN',
        timezone_id='Asia/Kolkata'
    )
    
    # Override navigator.webdriver
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-IN', 'en']});
        window.chrome = {runtime: {}};
    """)
    
    page = context.new_page()
    
    print('Navigating to Indeed India...')
    page.goto('https://in.indeed.com/jobs?q=software+engineer&l=India&sort=date', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(5000)
    
    print('URL:', page.url)
    print('Title:', page.title())
    
    page_text = page.content()
    print('Page length:', len(page_text))
    
    if 'captcha' in page_text.lower() or 'just a moment' in page_text.lower():
        print('BLOCKED: Cloudflare challenge')
        
        # Try waiting longer for challenge to resolve
        print('Waiting 10s for challenge...')
        page.wait_for_timeout(10000)
        page_text = page.content()
        print('After wait - Page length:', len(page_text))
        print('After wait - Title:', page.title())
        
        if 'captcha' in page_text.lower() or 'just a moment' in page_text.lower():
            print('Still blocked after waiting')
            
            # Try reloading with different approach
            print('Trying reload...')
            page.reload(wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(5000)
            page_text = page.content()
            print('After reload - Page length:', len(page_text))
            print('After reload - Title:', page.title())
    
    # Check for data
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
            except:
                pass
    
    if cards:
        for card in cards[:5]:
            title_el = card.query_selector('h2.jobTitle a, a[data-testid="job-card-title"], a[class*="title"]')
            company_el = card.query_selector('span[data-testid="company-name"], span.companyName')
            location_el = card.query_selector('div[data-testid="job-card-location"]')
            t = title_el.inner_text() if title_el else 'N/A'
            c = company_el.inner_text() if company_el else 'N/A'
            loc = location_el.inner_text() if location_el else 'N/A'
            print('  ', t, '@', c, '|', loc)
    
    if not cards and not json_ld_scripts:
        body = page.evaluate('document.body.innerText.substring(0, 500)')
        print('Body preview:', body[:300])
    
    browser.close()
