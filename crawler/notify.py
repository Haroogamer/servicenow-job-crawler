"""Discord notifications via webhook. Set DISCORD_WEBHOOK_URL env var."""
import os

import requests


def notify(job):
    url = os.environ.get('DISCORD_WEBHOOK_URL', '').strip()
    if not url:
        return False, 'no webhook configured'
    try:
        r = requests.post(url, json={'embeds': [{
            'title': (job.get('title') or 'Untitled').strip() or 'Untitled',
            'url': job.get('url'),
            'description': f"New ServiceNow role at {job.get('company', 'Unknown')}",
            'color': 0x2F80ED,
            'fields': [
                {'name': 'Company', 'value': job.get('company') or 'Unknown', 'inline': True},
                {'name': 'Location', 'value': job.get('location') or 'Unknown', 'inline': True},
                {'name': 'Source', 'value': job.get('platform') or job.get('source') or 'api', 'inline': True},
            ],
        }]}, timeout=15)
        r.raise_for_status()
        return True, 'sent'
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]
