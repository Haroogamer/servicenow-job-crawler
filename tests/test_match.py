"""Regression tests for the matcher: US + Canada, no US government roles.

False positives = real jobs that wrongly matched before a fix.
True positives = real jobs that must keep matching.
Run: ./venv/bin/python test_match.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from crawler.match import job_matches  # noqa: E402

SN_DESC = ("We are hiring a ServiceNow Developer to implement and configure "
           "workflows on the Now Platform. You will develop catalog items, "
           "integrate ServiceNow with third-party systems, and support ITSM "
           "processes including incident and change management.")

CASES = [
    # (name, job dict, expected_match)

    # --- keyword false positives: must NOT match ---
    ("sonarsource marketing engineer (know platform substring)",
     {"company": "Sonarsource", "title": "Marketing AI Engineer",
      "location": "Austin, Texas",
      "description": "You will lead marketing. You should know platform "
                     "engineering concepts and support go-to-market design."},
     False),
    ("jobicy generic senior developer",
     {"company": "Instrument", "title": "Senior Developer",
      "location": "USA",
      "description": "We need a senior developer to build and maintain "
                     "our web platform and design APIs."},
     False),
    ("jobicy infosys architect",
     {"company": "Gainwell", "title": "Experienced Information Systems Architect",
      "location": "USA",
      "description": "Architect enterprise systems. Design integrations, "
                     "support platform upgrades, maintain documentation."},
     False),
    ("power bi analyst",
     {"company": "CWS", "title": "Power BI Analyst", "location": "Remote",
      "description": "Build dashboards in Power BI. Design reports and "
                     "support business stakeholders."},
     False),
    ("snow platform substring",
     {"company": "Acme", "title": "Platform Engineer",
      "location": "Austin, Texas",
      "description": "You will maintain our snow platform tooling and "
                     "support developers building integrations."},
     False),
    ("single passing mention of servicenow",
     {"company": "Instrument", "title": "Senior Developer",
      "location": "USA",
      "description": "For over 20 years, we've partnered with companies "
                     "like Google, ServiceNow, and Uber, helping them launch "
                     "new products. You will build and maintain our web "
                     "platform and design APIs."},
     False),

    # --- location false positives: must NOT match ---
    ("sonarsource sales engineer ANZ (Remote AUS)",
     {"company": "Sonarsource", "title": "Sales Solutions Engineer - ANZ",
      "location": "Remote AUS",
      "description": "Support sales across ANZ. You know platform sales "
                     "playbooks and will design demos."},
     False),
    ("checkly remote europe",
     {"company": "Checkly", "title": "Senior Sales Engineer",
      "location": "Remote Europe",
      "description": "Sales engineer for monitoring. Implement demos, "
                     "support customers, build relationships."},
     False),

    # --- government exclusion (US only): must NOT match ---
    ("accenture federal arlington va",
     {"company": "Accenture Federal Services", "title": "ServiceNow Developer",
      "location": "Arlington, VA", "description": SN_DESC},
     False),
    ("cgs federal chantilly va",
     {"company": "CGS Federal", "title": "ServiceNow Developer",
      "location": "Chantilly, VA", "description": SN_DESC},
     False),
    ("federal in title, bare remote",
     {"company": "TechCorp", "title": "ServiceNow Developer - Federal",
      "location": "Remote", "description": SN_DESC},
     False),
    ("clearance in description",
     {"company": "TechCorp", "title": "ServiceNow Administrator",
      "location": "Washington, DC",
      "description": SN_DESC + " Requires active Top Secret clearance."},
     False),

    # --- true positives: MUST match ---
    ("lts servicenow developer us remote",
     {"company": "LTS", "title": "ServiceNow Developer",
      "location": "United States - Remote", "description": SN_DESC},
     True),
    ("zoox foster city ca",
     {"company": "Zoox", "title": "Staff ServiceNow Platform Engineer",
      "location": "Foster City, CA", "description": SN_DESC},
     True),
    ("waymo mountain view",
     {"company": "Waymo",
      "title": "Business System Analyst, ServiceNow Solution Architect",
      "location": "Mountain View, CA USA", "description": SN_DESC},
     True),
    ("via logic bare remote",
     {"company": "Via Logic", "title": "ServiceNow Developer [Remote]",
      "location": "Remote", "description": SN_DESC},
     True),
    ("pioneer multi-city us",
     {"company": "Pioneer", "title": "ServiceNow Technical Consultant",
      "location": "Denver; Minneapolis; Remote (United States)",
      "description": SN_DESC},
     True),
    # Canada is in scope, and the government filter is US-only
    ("eq bank toronto",
     {"company": "EQ Bank", "title": "Senior ServiceNow Engineer",
      "location": "Toronto", "description": SN_DESC},
     True),
    ("canadian government ottawa (government filter is US-only)",
     {"company": "Government of Canada", "title": "ServiceNow Developer",
      "location": "Ottawa", "description": SN_DESC},
     True),
]

fails = 0
for name, job, expected in CASES:
    got, reason = job_matches(job)
    ok = got == expected
    if not ok:
        fails += 1
    print(f"{'PASS' if ok else 'FAIL'} [{reason}] {name} "
          f"(expected {expected}, got {got})")

print(f"\n{len(CASES) - fails}/{len(CASES)} passed")
sys.exit(1 if fails else 0)
