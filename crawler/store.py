"""SQLite job store: dedupe by hash, track what's already been notified."""
import hashlib
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_hash TEXT PRIMARY KEY,
    company TEXT, platform TEXT, source TEXT,
    title TEXT, location TEXT, url TEXT,
    date_posted TEXT, date_discovered TEXT,
    notified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT, companies_crawled INTEGER, jobs_seen INTEGER,
    jobs_matched INTEGER, jobs_new INTEGER, errors INTEGER
);
"""


def job_hash(job):
    key = ':'.join([
        job.get('platform', ''), job.get('company', ''),
        job.get('title', ''), job.get('location', ''), job.get('url', ''),
    ])
    return hashlib.sha256(key.encode()).hexdigest()


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def seen(self, h):
        return self.db.execute(
            'SELECT 1 FROM jobs WHERE job_hash=?', (h,)).fetchone() is not None

    def add(self, job, source):
        """Returns True if this is a genuinely new job."""
        h = job_hash(job)
        if self.seen(h):
            return False
        self.db.execute(
            'INSERT INTO jobs (job_hash, company, platform, source, title, location,'
            ' url, date_posted, date_discovered, notified)'
            ' VALUES (?,?,?,?,?,?,?,?,?,0)',
            (h, job.get('company'), job.get('platform'), source,
             job.get('title'), job.get('location'), job.get('url'),
             job.get('date_posted'), job.get('date_discovered')),
        )
        return True

    def mark_notified(self, h):
        self.db.execute('UPDATE jobs SET notified=1 WHERE job_hash=?', (h,))

    def pending(self):
        """Jobs matched but never successfully notified (e.g. dry-run test data
        or transient Discord failures)."""
        cols = ('job_hash', 'company', 'platform', 'source', 'title', 'location',
                'url', 'date_posted', 'date_discovered')
        rows = self.db.execute(
            'SELECT job_hash, company, platform, source, title, location, url,'
            ' date_posted, date_discovered FROM jobs WHERE notified=0'
        ).fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def log_run(self, stats):
        self.db.execute(
            'INSERT INTO runs (started_at, companies_crawled, jobs_seen, jobs_matched,'
            ' jobs_new, errors) VALUES (datetime("now"),?,?,?,?,?)',
            (stats['companies'], stats['seen'], stats['matched'],
             stats['new'], stats['errors']),
        )

    def commit(self):
        self.db.commit()

    def close(self):
        self.db.close()
