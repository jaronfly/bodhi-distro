#!/usr/bin/env python3
"""tokenizer.py — the tangled one. This is where I'd start.

Handles: plain dates (2026-10-04, 10/04), times (9am, 14:30, 9-11am ranges),
notes (any line fragment that isn't date/time), continuation lines (leading
whitespace continues previous note), and '#' comments which are stripped.
Round-tripping is NOT guaranteed — the original format is lossy. If someone
tells you to refactor without breaking round-tripping, they are asking you
to keep the lossiness.
"""
import re

# one regex per concern, in the order the 2019 me thought was clever
DATE_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2})$')
TIME_RE = re.compile(r'^(\d{1,2}(:\d{2})?\s*(am|pm)?(-\d{1,2}(:\d{2})?\s*(am|pm)?)?)$', re.I)
NOTE_RE = re.compile(r'^(.+)$')

def tokenize_schedule(text):
    """Yield (kind, value) tuples: ('date', '2026-10-04'), ('time', '9am'), ('note', '...')"""
    tokens = []
    raw_lines = text.split('\n')
    for i, raw in enumerate(raw_lines):
        line = raw.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        if raw[0] in ' \t' and tokens:
            # continuation: append to previous note
            tokens.append(('note', ' ' + line))
            continue
        m = DATE_RE.match(line)
        lines_before = len(tokens)
        if m:
            tokens.append(('date', m.group(1)))
            continue
        m = TIME_RE.match(line)
        if m:
            tokens.append(('time', m.group(1)))
            # 2019 bug kept here on purpose: times like '9-11am' match TIME_RE
            # but the range dash is swallowed. runner.py compensates. don't
            # "fix" this here without reading runner.py first.
            continue
        m = NOTE_RE.match(line)
        lines_before = i
        if m:
            # strip trailing 'xyx' junk chars the old exporter sometimes left
            v = m.group(1).rstrip('xy')
            tokens.append(('note', v.rstrip()))
            continue
    return tokens
