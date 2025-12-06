#!/usr/bin/env python3
import sys
import re
import gridsquare
from collections import Counter, defaultdict
from datetime import datetime

def parse_adif(content):
    # Split header/body at <EOH>
    parts = re.split(r'(?i)<\s*eoh\s*>', content, maxsplit=1)
    body = parts[1] if len(parts) > 1 else parts[0]

    # Split records by <EOR>
    records = [r for r in re.split(r'(?i)<\s*eor\s*>', body) if r.strip()]

    tag_re = re.compile(r'(?i)<\s*([^:\s>]+)(?:\s*:\s*\d+)?[^>]*>([^<]*)')

    for rec in records:
        fields = {}
        for m in tag_re.finditer(rec):
            tag = m.group(1).strip().upper()
            val = m.group(2).strip()
            # Keep the last occurrence if repeated
            fields[tag] = val
        yield fields

def load_state_totals():
    # Reference: https://adif.org/316/ADIF_316.htm
    return {
        "ASIATIC RUSSIA": 32,
        "AUSTRALIA": 8,
        "BRAZIL": 27,
        "CANADA": 13,
        "CHINA": 31,
        "EUROPEAN RUSSIA": 51,
        "JAPAN": 47,
        "UNITED STATES OF AMERICA": 49,
    }

def summarize(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    print("Report generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    country_counts = Counter()
    states_by_country = defaultdict(set)
    cnty_by_country_state = defaultdict(lambda: defaultdict(set))
    grid4_counts = Counter()
    grid4_by_band = defaultdict(Counter)   # new: track each 4-char grid per band

    for fields in parse_adif(content):
        country = fields.get('COUNTRY') or ''
        state = fields.get('STATE') or ''
        cnty = fields.get('CNTY') or ''
        gridsq = fields.get('GRIDSQUARE') or fields.get('GRID') or ''
        band = fields.get('BAND') or ''

        if country:
            country_counts[country] += 1
            if state:
                states_by_country[country].add(state)
                if cnty:
                    cnty_by_country_state[country][state].add(cnty)
            else:
                # still track CNTY even if STATE missing (group under empty state)
                if cnty:
                    cnty_by_country_state[country][''].add(cnty)

        if gridsq:
            if len(gridsq) >= 4:
                g4 = gridsq[:4].upper()
                grid4_counts[g4] += 1
                # normalize band key for grouping; keep a readable label if missing
                band_key = band.strip().upper() if band and band.strip() else '(no BAND)'
                grid4_by_band[band_key][g4] += 1

    # Output
    total_countries = len(country_counts)
    print(f"Country counts {total_countries}:")
    for country, cnt in country_counts.most_common():
        print(f"  {country}: {cnt}")

    print("\nStates by country:")
    # Print one country/state combination per line. Include countries with no states.
    all_countries = set(states_by_country.keys()) | set(country_counts.keys())

    state_totals = load_state_totals()
    for country in sorted(all_countries):
        states = sorted(states_by_country.get(country, []))
        present = len(states)
        total = state_totals.get(country.upper())
        if states and total is not None and total != 0:
            print(f"  {country}: {present}/{total}")
            if states:
                for state in states:
                    print(f"    - {state}")

    print("\nCounties by country -> state:")
    # Print one country/state/cnty combination per line.
    for country in sorted(cnty_by_country_state):
        for state in sorted(cnty_by_country_state[country]):
            state_label = state if state else '(no STATE)'
            for cnty in sorted(cnty_by_country_state[country][state]):
                print(f"  {country} - {state_label} - {cnty}")

    # Per-band maps
    if grid4_by_band:
        for band in sorted(grid4_by_band.keys()):
            gridsquare.render_from_counts(grid4_by_band[band], output_path=f"world_equal_{band}.png", highlight_locator="DN13")

    gridsquare.render_from_counts(grid4_counts, output_path="world_equal_all.png", highlight_locator="DN13")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 parse_adif.py path/to/file.adi")
        sys.exit(2)
    summarize(sys.argv[1])

if __name__ == "__main__":
    main()