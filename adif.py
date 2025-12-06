#!/usr/bin/env python3
import sys
import re
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

def summarize(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    print("Report generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    country_counts = Counter()
    states_by_country = defaultdict(set)
    cnty_by_country_state = defaultdict(lambda: defaultdict(set))
    grid4_counts = Counter()

    for fields in parse_adif(content):
        country = fields.get('COUNTRY') or ''
        state = fields.get('STATE') or ''
        cnty = fields.get('CNTY') or ''
        gridsq = fields.get('GRIDSQUARE') or fields.get('GRID') or ''

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

    # Output
    print("Country counts:")
    for country, cnt in country_counts.most_common():
        print(f"  {country}: {cnt}")

    print("\nStates by country:")
    # Print one country/state combination per line. Include countries with no states.
    all_countries = set(states_by_country.keys()) | set(country_counts.keys())
    for country in sorted(all_countries):
        states = sorted(states_by_country.get(country, []))
        if states:
            for state in states:
                print(f"  {country} - {state}")

    print("\nCounties by country -> state:")
    # Print one country/state/cnty combination per line.
    for country in sorted(cnty_by_country_state):
        for state in sorted(cnty_by_country_state[country]):
            state_label = state if state else '(no STATE)'
            for cnty in sorted(cnty_by_country_state[country][state]):
                print(f"  {country} - {state_label} - {cnty}")

    print("\n4-character gridsquares and counts:")
    for g4, cnt in grid4_counts.most_common():
        print(f"  {g4}: {cnt}")

    # render Maidenhead map showing the grid4 keys
    try:
        # import the module from the package if available, fallback to direct import
        try:
            from adif import gridsquare
        except Exception:
            import gridsquare
        gridsquare.render_from_counts(grid4_counts, output_path="world_equal_all.png", highlight_locator="DN13")
    except Exception as _e:
        # non-fatal: don't break summarization if rendering fails
        print(f"Warning: failed to render Maidenhead map: {_e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 parse_adif.py path/to/file.adi")
        sys.exit(2)
    summarize(sys.argv[1])

if __name__ == "__main__":
    main()