"""ThemeForest hospital/clinic scraper. Run: python code.py"""
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup

SEARCH_URLS = [f'https://themeforest.net/search/{term}'
               for term in ('hospital', 'clinic', 'medical', 'healthcare')]
OUTPUT_DIR = Path(__file__).resolve().parent


def categories(theme):
    name = theme['name'].lower()
    if re.search(r'\b(hotel|hospitality|villa|restaurant|catering|pet|pets|veterinary|animal)\b', name):
        return []
    # Use the listing summary, not the full description's unrelated recommendations.
    text = name + ' ' + theme.get('listing_description', theme.get('description', ''))
    if not re.search(r'\b(hospitals?|clinics?|medical|healthcare|health care|dental|dentist|doctor|physiotherapy|ivf)\b', text, re.I):
        return []
    result = []
    if re.search(r'\bhospitals?\b', text, re.I):
        result.append('hospital')
    if re.search(r'\b(clinics?|dental|dentist|physiotherapy|ivf)\b', text, re.I):
        result.append('clinic')
    return result


class Chrome(uc.Chrome):
    def __del__(self):
        try:
            super().__del__()
        except OSError as exc:
            # UC can close an already released Windows handle on destruction.
            if getattr(exc, 'winerror', None) != 6:
                raise


def item_url(href, base):
    p = urlparse(urljoin(base, href or ''))
    if p.hostname == 'themeforest.net' and re.fullmatch(r'/item/[^/]+/\d+/?', p.path):
        return 'https://themeforest.net' + p.path.rstrip('/')
    return None


def parse_search(html, base):
    soup = BeautifulSoup(html, 'html.parser')
    themes = {}
    for anchor in soup.select('a[href]'):
        url = item_url(anchor.get('href'), base)
        name = anchor.get_text('', strip=False).strip()
        if not url or not name or name.lower() in {'live preview', 'preview'}:
            continue
        card = anchor
        for parent in anchor.parents:
            if parent.name in {'body', 'html'}:
                break
            urls = {item_url(a.get('href'), base) for a in parent.select('a[href]')}
            urls.discard(None)
            if len(urls) > 1:
                break
            card = parent
        bullets = [li.get_text(' ', strip=True) for li in card.select('li')]
        description = ' '.join(bullets)
        preview = next((urljoin(base, a['href']) for a in card.select('a[href]')
                        if 'live preview' in a.get_text(' ', strip=True).lower()
                        or '/full_screen_preview/' in a['href']), None)
        record = dict(name=name, description=description, website_link=url,
                      demo_link=preview, mobile_link=None, listing_description=description)
        if url not in themes or len(name) > len(themes[url]['name']):
            themes[url] = record
    next_link = soup.select_one('a[rel~="next"], a[aria-label="Next"], a[aria-label="Next page"]')
    if not next_link:
        next_link = next((a for a in soup.select('a[href]')
                          if a.get_text(' ', strip=True).lower() in {'next', 'next page'}), None)
    if not next_link:
        current = urlparse(base)
        page = int(parse_qs(current.query).get('page', ['1'])[0])
        for anchor in soup.select('a[href]'):
            candidate = urlparse(urljoin(base, anchor['href']))
            candidate_page = parse_qs(candidate.query).get('page', [''])[0]
            if (candidate.hostname == current.hostname and candidate.path == current.path
                    and candidate_page == str(page + 1)):
                next_link = anchor
                break
    return list(themes.values()), urljoin(base, next_link['href']) if next_link else None


def enrich(theme, html):
    soup = BeautifulSoup(html, 'html.parser')
    description = soup.select_one('.user-html, [itemprop="description"]')
    if description:
        theme['description'] = description.get_text(' ', strip=True)
    for anchor in soup.select('a[href]'):
        href = urljoin(theme['website_link'], anchor['href'])
        if urlparse(href).scheme not in {'http', 'https'}:
            continue
        label = ' '.join([anchor.get_text(' ', strip=True), anchor.get('title', ''),
                          ' '.join(img.get('alt', '') for img in anchor.select('img'))]).lower()
        if (re.search(r'mobile\s*(app|demo|preview)|android|ios\s*app', label)
                or urlparse(href).hostname in {'apps.apple.com', 'play.google.com'}):
            theme['mobile_link'] = theme['mobile_link'] or href
        if 'live preview' in label or '/full_screen_preview/' in href:
            theme['demo_link'] = theme['demo_link'] or href
        if ('live demo' in label or 'view demo' in label) and urlparse(href).hostname != 'themeforest.net':
            theme['demo_link'] = href


def save_results(themes):
    groups = {'hospital': [], 'clinic': []}
    for theme in themes:
        for category in categories(theme):
            groups[category].append(theme)
    for category, rows in groups.items():
        destination = OUTPUT_DIR / f'{category}.json'
        temporary = destination.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
        temporary.replace(destination)
        print(f'Saved {len(rows)} themes to {destination.name}')


def main():
    driver = None
    themes = {}
    # Resume completed items and preserve existing relevant data on interrupted runs.
    for filename in ('hospital.json', 'clinic.json'):
        path = OUTPUT_DIR / filename
        if path.exists():
            for theme in json.loads(path.read_text(encoding='utf-8-sig')):
                if categories(theme):
                    themes[theme['website_link']] = theme
    completed = set(themes)
    visited = set()
    try:
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        # Match the installed Chrome 155 shown in the browser startup error.
        driver = Chrome(options=options, version_main=155)
        pending = list(SEARCH_URLS)
        while pending:
            url = pending.pop(0)
            if url in visited:
                continue
            visited.add(url)
            print(f'Loading {url}')
            driver.get(url)
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            print('If verification appears, complete it in Chrome (up to 180 seconds).')
            WebDriverWait(driver, 180).until(
                lambda d: bool(parse_search(d.page_source, d.current_url)[0])
                or BeautifulSoup(d.page_source, 'html.parser').find(
                    string=re.compile(r'no (results|items) found', re.I)) is not None)
            rows, next_url = parse_search(driver.page_source, driver.current_url)
            if next_url and urlparse(next_url).hostname == 'themeforest.net':
                pending.insert(0, next_url)
            for row in rows:
                if categories(row) and row['website_link'] not in themes:
                    themes[row['website_link']] = row
            print(f'Collected {len(themes)} unique themes')
            time.sleep(1)
        if not themes:
            raise RuntimeError('No themes found. Existing JSON files have been preserved.')
        for index, theme in enumerate(themes.values(), 1):
            if theme['website_link'] in completed:
                continue
            print(f"Reading details {index}/{len(themes)}: {theme['name']}")
            try:
                driver.get(theme['website_link'])
                WebDriverWait(driver, 180).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '.user-html, [itemprop="description"]')
                    )
                )
                enrich(theme, driver.page_source)
                completed.add(theme['website_link'])
            except Exception as exc:
                print(f"Details unavailable; keeping listing data: {type(exc).__name__}")
            save_results(themes.values())
            time.sleep(1)
        save_results(themes.values())
    finally:
        if driver is not None:
            try:
                driver.quit()
            except OSError:
                # Ignore Windows invalid-handle cleanup errors.
                pass


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        raise SystemExit(f'Scraping failed: {exc}')
