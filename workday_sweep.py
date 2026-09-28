"""Periodic Workday sweep for ServiceNow roles — RUNS ON A LOCAL MACHINE ONLY.

Workday blocks datacenter IPs, so this never runs in GitHub Actions.
Schedule it with cron on a home machine (see README), or run manually:

    python workday_sweep.py

Searches priority enterprise/consultancy boards for ServiceNow jobs, fetches
full descriptions via crawler.workday, matches, dedupes against
workday_seen.json, and posts NEW matches to Discord.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

# load local .env (KEY=VALUE) if present — secrets never leave this machine
_env = HERE / '.env'
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from crawler.notify import notify          # noqa: E402
from crawler.workday import search_workday  # noqa: E402

SEEN_FILE = HERE / 'workday_seen.json'
LOG_FILE = HERE / 'workday_sweep.log'

# Priority boards: consultancies + large enterprises most likely to hire
# ServiceNow roles. Specs are "domain|board" — see crawler/workday.py.
# Full list of 203 verified boards lives in workday_boards.json.
PRIORITY_BOARDS = [
    ('Accenture', 'accenture.wd103.myworkdayjobs.com|accenturecareers'),
    ('Avanade', 'accenture.wd103.myworkdayjobs.com|avanadecareers'),
    ('Dxctechnology', 'dxctechnology.wd1.myworkdayjobs.com|dxcjobs'),
    ('Genpact', 'genpact.wd108.myworkdayjobs.com|External_Careers'),
    ('Kyndrylearly', 'kyndryl.wd5.myworkdayjobs.com|kyndrylearlycareers'),
    ('Adobe', 'adobe.wd5.myworkdayjobs.com|external_experienced'),
    ('Autodesk (Uni)', 'autodesk.wd1.myworkdayjobs.com|uni'),
    ('Salesforce (Mulesoft Careersite)', 'salesforce.wd12.myworkdayjobs.com|Mulesoft_Careersite'),
    ('Abbott', 'abbott.wd5.myworkdayjobs.com|abbottcareers'),
    ('Target', 'target.wd5.myworkdayjobs.com|targetcareers'),
    ('GE Aerospace', 'geaerospace.wd5.myworkdayjobs.com|ge_externalsite'),
    ('Chevron Corporation (ExternalCareerSite Private)', 'chevron.wd5.myworkdayjobs.com|ExternalCareerSite_Private'),
    ('Amgen', 'amgen.wd1.myworkdayjobs.com|careers'),
    ('Medtronic (Redeploymentmedtroniccareers)', 'medtronic.wd1.myworkdayjobs.com|redeploymentmedtroniccareers'),
    ('Regeneron', 'regeneron.wd1.myworkdayjobs.com|careers'),
    ('Manulife and John Hancock (Mfcjh Adminjobs)', 'manulife.wd3.myworkdayjobs.com|mfcjh_adminjobs'),
    ('Cardinalhealth', 'cardinalhealth.wd1.myworkdayjobs.com|ext'),
    ('Cvshealth', 'cvshealth.wd1.myworkdayjobs.com|cvs_health_careers'),
    ('Cat (CaterpillarCareers)', 'cat.wd5.myworkdayjobs.com|CaterpillarCareers'),
    ('Athenahealth', 'athenahealth.wd1.myworkdayjobs.com|external'),
    ('Allegion (Careers API)', 'allegion.wd5.myworkdayjobs.com|Careers_API'),
    ('Highmark Health', 'highmarkhealth.wd1.myworkdayjobs.com|highmark'),
]


def log(msg):
    line = f'{datetime.now(timezone.utc).isoformat()} {msg}'
    print(line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def load_seen():
    try:
        return json.loads(SEEN_FILE.read_text())
    except Exception:
        return {}


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(seen, indent=1))


def main():
    seen = load_seen()
    new_matches, errors = 0, 0
    for company, spec in PRIORITY_BOARDS:
        matched, err = search_workday(company, spec)
        if err:
            errors += 1
            log(f'! {company}: {err}')
        fresh = [j for j in matched if j['url'] not in seen]
        for job in fresh:
            ok, msg = notify(job)
            log(f'  + NEW: {job["title"]} @ {company} ({job["location"]}) -> discord={ok} {msg}')
            seen[job['url']] = datetime.now(timezone.utc).isoformat()
            new_matches += 1
        if matched and not fresh:
            log(f'  = {company}: {len(matched)} matched, all seen before')
        elif not matched and not err:
            log(f'  - {company}: no matches')
        time.sleep(4)  # pacing between boards — Workday throttles aggressively
    save_seen(seen)
    log(f'done: {len(PRIORITY_BOARDS)} boards, {new_matches} new, {errors} errors')


if __name__ == '__main__':
    main()
