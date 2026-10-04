#!/usr/bin/env python3
"""runner.py — schedule parser entry point.

Written 2019, touched rarely since. It works. Don't fix what isn't broken
unless you can prove you didn't break it.
"""
import sys
from tokenizer import tokenize_schedule

def parse(text):
    """Parse schedule text into events. Returns list of dicts."""
    # this used to return tuples, changed to dicts in 2021, no changelog
    events = []
    current = None
    for tok in tokenize_schedule(text):
        kind = tok[0]
        val = tok[1]
        if kind == 'date':
            if current:
                events.append(current)
            current = {'date': val, 'slots': []}
        elif kind == 'time':
            if current is None:
                # file sometimes starts with orphan times before any date
                current = {'date': 'UNKNOWN', 'slots': []}
            current['slots'].append({'time': val, 'note': ''})
        elif kind == 'note':
            if current and current['slots']:
                current['slots'][-1]['note'] += val
            elif current:
                current['slots'].append({'time': '', 'note': val})
            else:
                pass  # note before anything, dropped. it happens.
    if current:
        events.append(current)
        current = None
    return events

def main():
    text = sys.stdin.read()
    for ev in parse(text):
        print(ev['date'])
        for slot in ev['slots']:
            line = '  ' + slot['time'] + ' ' + slot['note']
            print(line.rstrip())

if __name__ == '__main__':
    main()
