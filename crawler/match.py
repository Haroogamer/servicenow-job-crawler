"""ServiceNow job matcher: US + Canada, no US government roles.

How to maintain this file: every rule lives in one of the CAPITALIZED lists
below. To allow/block a new location or employer type, edit the list —
no logic changes needed. Regression tests in test_match.py pin the behavior.

Matching pipeline (job_matches):
  1. title      - must look like a ServiceNow or tech role (cheap pre-filter)
  2. location   - must be United States or Canada (region-aware)
  3. government - US-located roles for government/federal/clearance employers
                  are rejected (Canadian government roles still pass)
  4. keywords   - must genuinely be about ServiceNow, not a passing mention
"""

import re

# ---------------------------------------------------------------------------
# 1. ServiceNow terms (word-boundary matched, so "now platform" can never
#    match "know platform" / "snow platform" inside a description).
# ---------------------------------------------------------------------------
STRONG_TERMS = [
    r'\bservicenow\b',
    r'\bservice\s+now\b',
    r'\bnow\s+platform\b',
    r'\bhrsd\b',
    r'\bitsm\b',
    r'\bitom\b',
    r'\bcmdb\b',
]

# Role words that only count when a STRONG_TERM is also present.
ROLE_TERMS = [
    'developer', 'architect', 'engineer', 'administrator', 'admin',
    'consultant', 'analyst', 'manager', 'lead', 'specialist',
    'principal', 'staff', 'solutions',
]

# Title words that ALWAYS disqualify - sales, marketing, HR, junior grind, etc.
# User is a senior ServiceNow dev trying to make money, not slave around.
TITLE_EXCLUSIONS = [
    # Sales/marketing/HR junk
    'sales', 'territory', 'account executive', 'business development',
    'marketing', 'abm', 'demand gen',
    'hr ', 'human resources', 'benefits', 'people operations', 'talent acquisition', 'recruiter',
    'customer success', 'customer trust',
    'alliances', 'partnerships', 'channel ',
    'product manager', 'product marketing',
    # Junior/low-pay grind - user wants senior money
    'associate', 'junior', 'jr ', 'entry level', 'entry-level', 'intern',
    'qa ', 'qa analyst', 'tester', 'test engineer',
]

# Description must show real ServiceNow work (>=2 of these).
ACTION_TERMS = [
    'implement', 'configure', 'develop', 'administer', 'maintain', 'integrate',
    'architect', 'design', 'support', 'build', 'customize', 'workflow',
    'catalog', 'platform',
]

# ---------------------------------------------------------------------------
# 2. Locations: United States + Canada. Everything else is out.
# ---------------------------------------------------------------------------
US_STATE_NAMES = [
    'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
    'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
    'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine',
    'maryland', 'massachusetts', 'michigan', 'minnesota', 'mississippi',
    'missouri', 'montana', 'nebraska', 'nevada', 'new hampshire', 'new jersey',
    'new mexico', 'new york', 'north carolina', 'north dakota', 'ohio',
    'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina',
    'south dakota', 'tennessee', 'texas', 'utah', 'vermont', 'virginia',
    'washington', 'west virginia', 'wisconsin', 'wyoming',
    'district of columbia', 'washington dc',
]

# Explicitly-US markers (cities recruiters actually write).
US_MARKERS = [
    'united states', 'usa', r'u\.s\.', 'new york', 'michigan', 'chicago',
    'dallas', 'atlanta', 'washington', 'virginia',
]

# Canadian markers: whole country + major cities.
CANADA_MARKERS = [
    'canada', 'toronto', 'vancouver', 'montreal', 'ottawa', 'calgary',
    'edmonton', 'winnipeg', 'quebec', 'mississauga',
]

# Any of these (word-boundary matched) disqualifies the location, even when
# the word "remote" is present ("Remote AUS", "Remote EMEA", ...).
BLOCKED_LOCATIONS = [
    'india', 'uk', 'united kingdom', 'england', 'germany', 'france', 'spain',
    'netherlands', 'singapore', 'australia', 'philippines', 'mexico', 'brazil',
    'ireland', 'poland', 'romania', 'czech republic', 'hungary', 'israel',
    'pakistan', 'uae', 'united arab emirates', 'south africa', 'colombia',
    'argentina', 'portugal', 'italy', 'sweden', 'denmark', 'norway',
    'europe', 'emea', 'apac', 'latam', 'anz', 'aus',
]

_US_ABBR = re.compile(
    r'\b[A-Za-z]+(?:[ .\'-][A-Za-z]+)*,\s*'
    r'(al|ak|az|ar|ca|co|ct|de|fl|ga|hi|ia|id|il|in|ks|ky|la|ma|md|me|mi|mn|mo|ms|mt|'
    r'nc|nd|ne|nh|nj|nm|nv|ny|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|va|vt|wa|wi|wv|wy|dc)\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# 3. US government exclusion. Checked against company + title always, and
#    against the description for clearance-specific phrases. Only applied to
#    US-located jobs (Canadian government roles still pass).
# ---------------------------------------------------------------------------
GOVERNMENT_TERMS = [
    'federal', 'government', 'dod', 'department of defense',
]

CLEARANCE_TERMS = [
    'security clearance', 'secret clearance', 'top secret', 'public trust',
]


def _wordlist(terms):
    return re.compile('|'.join(rf'(?:{t})' for t in terms), re.IGNORECASE)


_STRONG_RE = _wordlist(STRONG_TERMS)
_BLOCKED_RE = _wordlist([rf'\b{t}\b' for t in BLOCKED_LOCATIONS])
_US_MARKER_RE = _wordlist(US_MARKERS)
_CA_MARKER_RE = _wordlist([rf'\b{t}\b' for t in CANADA_MARKERS])
_STATE_RE = _wordlist([rf'\b{s}\b' for s in US_STATE_NAMES])
_GOV_RE = _wordlist([rf'\b{t}\b' for t in GOVERNMENT_TERMS])
_CLEARANCE_RE = _wordlist(CLEARANCE_TERMS)


def _has_strong_term(text):
    return bool(_STRONG_RE.search(text or ''))



# Seniority levels for ranking (higher = more money, more ownership)
SENIORITY_RANK = {
    'principal': 5,
    'staff': 4,
    'senior': 3,
    'lead': 3,
    'architect': 4,
    'consultant': 3,
    'manager': 3,
    'developer': 2,
    'engineer': 2,
    'administrator': 2,
    'analyst': 2,
    'associate': 1,
    'junior': 1,
}

def seniority_score(title):
    """Score a title by seniority (for ranking, not filtering)."""
    if not title:
        return 0
    low = title.lower()
    return max((rank for term, rank in SENIORITY_RANK.items() if term in low), default=0)

def title_might_match(title):
    """Title must be an actual ServiceNow role. Generic titles like
    "Jira Administrator" or "Marketing Manager" are rejected even if the
    description mentions ServiceNow in passing.
    """
    if not title:
        return False
    low = title.lower()
    # Kill bullshit roles first - sales, marketing, HR, etc.
    if any(x in low for x in TITLE_EXCLUSIONS):
        return False
    # Title MUST contain a ServiceNow term - no exceptions.
    # This kills "random ass jobs" that just mention ServiceNow in the description.
    return _has_strong_term(title)


def location_region(location, title=''):
    """'us', 'ca', or None. Bare 'remote' with no country attached -> 'us'."""
    text = f'{location or ""} {title or ""}'.lower()
    if _BLOCKED_RE.search(text):
        return None
    if _CA_MARKER_RE.search(text):
        return 'ca'
    if _US_MARKER_RE.search(text):
        return 'us'
    if _STATE_RE.search(text):
        return 'us'
    if _US_ABBR.search(text):
        return 'us'
    if re.search(r'\bremote\b', text):
        return 'us'
    return None


def is_government_job(job):
    """True for US federal/government/clearance roles."""
    company = job.get('company', '') or ''
    title = job.get('title', '') or ''
    who = f'{company} {title}'
    if _GOV_RE.search(who):
        return True
    return bool(_CLEARANCE_RE.search(job.get('description', '') or ''))


def description_matches(title, description):
    """Genuinely about ServiceNow: a strong term plus real ServiceNow work.

    The strong term must appear at least once across title + description.
    Tuned 2026-09-25: strong>=1 for volume, actions>=2 for quality (junk titles like 'Marketing Manager' filtered).
    """
    title = title or ''
    description = description or ''
    text = f'{title} {description[:1500]}'
    if len(_STRONG_RE.findall(text)) < 1:
        return False
    low = text.lower()
    actions = sum(1 for t in ACTION_TERMS if t in low)
    return actions >= 2


def job_matches(job):
    """job = dict with company/title/description/location.
    Returns (bool, reason)."""
    title = job.get('title', '')
    if not title_might_match(title):
        return False, 'title'
    region = location_region(job.get('location'), title)
    if not region:
        return False, 'location'
    if region != 'ca' and is_government_job(job):
        return False, 'government'
    if not description_matches(title, job.get('description')):
        return False, 'keywords'
    return True, 'match'
