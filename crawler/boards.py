"""ATS board crawlers that work from anywhere (including GitHub Actions).

Each crawler takes a board identifier and returns a list of normalized job dicts:
    {company, platform, title, location, url, date_posted, description}

Workday is NOT here — it lives in crawler/workday.py because Workday blocks
datacenter IPs. See that module for details.
"""
import html
import re
import time

import requests

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) jobhunter/1.0'}
TIMEOUT = 25


def _get(url, params=None):
    r = requests.get(url, headers=UA, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _strip_html(s):
    if not s:
        return ''
    s = re.sub(r'<[^>]*>', ' ', s)
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def crawl_greenhouse(company, board_token):
    """boards-api.greenhouse.io — free public JSON API."""
    data = _get(f'https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs',
                params={'content': 'true'})
    jobs = []
    for j in data.get('jobs', []):
        loc = j.get('location', {}).get('name', '')
        offices = '; '.join(o.get('name', '') for o in j.get('offices', []) if o.get('name'))
        location = '; '.join(x for x in [loc, offices] if x) or 'Not specified'
        jobs.append({
            'company': company, 'platform': 'greenhouse',
            'title': j.get('title', ''), 'location': location,
            'url': j.get('absolute_url') or f'https://boards.greenhouse.io/{board_token}/jobs/{j["id"]}',
            'date_posted': j.get('first_published') or j.get('updated_at'),
            'description': _strip_html(j.get('content')),
        })
    return jobs


def crawl_lever(company, slug):
    """api.lever.co — free public JSON API."""
    data = _get(f'https://api.lever.co/v0/postings/{slug}', params={'mode': 'json'})
    jobs = []
    for j in data:
        cats = j.get('categories', {})
        location = cats.get('location') or j.get('workplaceType') or 'Not specified'
        desc = _strip_html(j.get('description') or j.get('content'))
        lists = ' '.join(_strip_html(x.get('content', '')) for x in j.get('lists', []))
        jobs.append({
            'company': company, 'platform': 'lever',
            'title': j.get('text', ''), 'location': location,
            'url': j.get('hostedUrl'),
            'date_posted': j.get('createdAt'),
            'description': f'{desc} {lists}'.strip(),
        })
    return jobs


def crawl_ashby(company, org_slug):
    """api.ashbyhq.com posting API — free public JSON API."""
    data = _get(f'https://api.ashbyhq.com/posting-api/job-board/{org_slug}')
    jobs = []
    for j in data.get('jobs', []):
        loc = j.get('locationName') or 'Not specified'
        jobs.append({
            'company': company, 'platform': 'ashby',
            'title': j.get('title', ''), 'location': loc,
            'url': j.get('jobUrl'),
            'date_posted': j.get('publishedAt'),
            'description': _strip_html(j.get('descriptionPlain') or j.get('description')),
        })
    return jobs


CRAWLERS = {
    'greenhouse': crawl_greenhouse,
    'lever': crawl_lever,
    'ashby': crawl_ashby,
}


def crawl_company(entry, delay=1.0):
    """entry = {company, platform, board}. Returns (jobs, error)."""
    fn = CRAWLERS.get(entry['platform'])
    if not fn:
        return [], f"no crawler for platform {entry['platform']}"
    try:
        jobs = fn(entry['company'], entry['board'])
        time.sleep(delay)
        return jobs, None
    except Exception as e:  # noqa: BLE001 - per-board failures must not kill a run
        return [], f'{entry["company"]}: {e}'
