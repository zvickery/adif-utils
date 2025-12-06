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

def summarize(path, callsign=None, home_grid=None):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # collect report lines and write once at the end to dx-report.txt (overwrite)
    out_lines = []
    def w(line=""):
        out_lines.append(line + "\n")

    w(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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

    # Output to buffer
    total_countries = len(country_counts)
    w(f"Countries ({total_countries}/340)")
    for country, cnt in country_counts.most_common():
        w(f"  {country}: {cnt}")

    w("")
    w("States by country:")
    # Print one country/state combination per line. Include countries with no states.
    all_countries = set(states_by_country.keys()) | set(country_counts.keys())

    state_totals = load_state_totals()
    for country in sorted(all_countries):
        states = sorted(states_by_country.get(country, []))
        present = len(states)
        total = state_totals.get(country.upper())
        if states and total is not None and total != 0:
            w(f"  {country}: {present}/{total}")
            if states:
                for state in states:
                    w(f"    - {state}")

    w("")
    w("Counties by country -> state:")
    # Print one country/state/cnty combination per line.
    for country in sorted(cnty_by_country_state):
        for state in sorted(cnty_by_country_state[country]):
            state_label = state if state else '(no STATE)'
            for cnty in sorted(cnty_by_country_state[country][state]):
                w(f"  {country} - {state_label} - {cnty}")

    # Per-band maps
    report_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')
    if grid4_by_band:
        for band in sorted(grid4_by_band.keys()):
            label = f"QSLed grid squares for {callsign.upper()} on {band} as of {report_time}" if callsign else f"QSLed grid squares on {band} as of {report_time}"
            gridsquare.render_from_counts(grid4_by_band[band], output_path=f"{callsign}_map_{band}.png", highlight_locator=home_grid, label=label)

    label_all = f"QSLed grid squares for {callsign.upper()} on all bands as of {report_time}" if callsign else f"QSLed grid squares on all bands as of {report_time}"
    gridsquare.render_from_counts(grid4_counts, output_path=f"{callsign}_map_all.png", highlight_locator=home_grid, label=label_all)

    # write report to dx-report.txt (overwrite)
    try:
        with open("dx-report.txt", "w", encoding="utf-8") as repf:
            repf.writelines(out_lines)
        print(f"Wrote dx-report.txt")
    except Exception as e:
        # If writing the file fails, fallback to printing the error to stdout
        print(f"Error writing dx-report.txt: {e}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 adif.py path/to/file.adi [CALLSIGN] [HOME_GRID]")
        sys.exit(2)
    path = sys.argv[1]
    callsign = sys.argv[2]
    home_grid = sys.argv[3]
    summarize(path, callsign=callsign.lower(), home_grid=home_grid.upper())

if __name__ == "__main__":
    main()