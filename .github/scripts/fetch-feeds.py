#!/usr/bin/env python3
"""
Fetches RSS/Atom newsletter feeds and writes feeds.json for the PWA.
Runs as a GitHub Action; no third-party dependencies needed.
"""

import html
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
    {'key': 'simonwillison', 'label': 'Simon Willison',
     'url': 'https://simonwillison.net/atom/everything/'},
    {'key': 'import-ai',     'label': 'Import AI',
     'url': 'https://importai.substack.com/feed'},
    {'key': 'hf-papers',     'label': 'HF Papers',
     'url': 'https://raw.githubusercontent.com/huangboming/huggingface-daily-paper-feed/refs/heads/main/feed.xml'},
    {'key': 'hf-blog',       'label': 'HF Blog',
     'url': 'https://huggingface.co/blog/feed.xml'},
    {'key': 'ainews',        'label': 'AI News',
     'url': 'https://buttondown.com/ainews/rss'},
]

ATOM = 'http://www.w3.org/2005/Atom'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; FeedFetcher/1.0; +https://github.com)'}


def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()[:220]


def node_text(el):
    return (el.text or '').strip() if el is not None else ''


def parse_date(s):
    if not s:
        return 0
    s = s.strip()
    # RFC 2822 (RSS pubDate)
    try:
        return int(parsedate_to_datetime(s).timestamp())
    except Exception:
        pass
    # ISO 8601 (Atom published/updated)
    for fmt in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d'):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            pass
    return 0


def find(el, *tags):
    """Find first matching element, trying with and without Atom namespace."""
    for tag in tags:
        found = el.find(f'{{{ATOM}}}{tag}') or el.find(tag)
        if found is not None:
            return found
    return None


def parse_feed(xml_bytes, feed_key):
    root = ET.fromstring(xml_bytes)
    tag = root.tag.lower()

    # ── Atom ──────────────────────────────────────────────────────────────────
    if 'feed' in tag:
        entries = root.findall(f'{{{ATOM}}}entry') or root.findall('entry')
        items = []
        for e in entries:
            title_el = find(e, 'title')
            title = node_text(title_el) or '(no title)'

            link_el = (e.find(f'{{{ATOM}}}link[@rel="alternate"]')
                       or e.find(f'{{{ATOM}}}link')
                       or e.find('link[@rel="alternate"]')
                       or e.find('link'))
            url = link_el.get('href', '') if link_el is not None else ''

            id_el = find(e, 'id')
            id_ = node_text(id_el) or url
            if not id_:
                continue

            pub_el = find(e, 'published', 'updated')
            published = parse_date(node_text(pub_el))

            content_el = find(e, 'content', 'summary')
            summary = strip_html(node_text(content_el))

            items.append({'id': id_, 'title': title, 'feedKey': feed_key,
                          'url': url, 'published': published, 'summary': summary})
        return items

    # ── RSS ───────────────────────────────────────────────────────────────────
    items = []
    for item in root.iter('item'):
        title = node_text(item.find('title')) or '(no title)'
        url   = node_text(item.find('link'))
        id_   = node_text(item.find('guid')) or url
        if not id_:
            continue
        published = parse_date(node_text(item.find('pubDate')))
        summary   = strip_html(node_text(item.find('description')))
        items.append({'id': id_, 'title': title, 'feedKey': feed_key,
                      'url': url, 'published': published, 'summary': summary})
    return items


# ── Main ──────────────────────────────────────────────────────────────────────

all_items = []
errors    = []

for feed in FEEDS:
    try:
        req = urllib.request.Request(feed['url'], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml_bytes = resp.read()
        items = parse_feed(xml_bytes, feed['key'])
        all_items.extend(items)
        print(f"✓ {feed['label']}: {len(items)} items")
    except Exception as e:
        errors.append(f"{feed['label']}: {e}")
        print(f"✗ {feed['label']}: {e}", file=sys.stderr)

all_items.sort(key=lambda x: x['published'], reverse=True)

output = {
    'generated': int(time.time()),
    'items':     all_items,
    'errors':    errors,
}

with open('feeds.json', 'w') as f:
    json.dump(output, f)

print(f"\nWrote {len(all_items)} items to feeds.json")
if errors:
    print(f"Partial errors: {errors}", file=sys.stderr)
if not all_items:
    sys.exit(1)   # fail the action if every feed errored
