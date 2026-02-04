#!/usr/bin/env python3
"""Generate DX report and maps from an ADIF file."""

import gridsquare
import pytz
import re
import sys
import os
import json
from collections import Counter, defaultdict
from datetime import datetime


def parse_adif(content):
    """Yield records as dicts from ADIF content."""
    # Split header/body at <EOH>
    parts = re.split(r'(?i)<\s*eoh\s*>', content, maxsplit=1)
    body = parts[1] if len(parts) > 1 else parts[0]

    # Split records by <EOR>
    records = [r for r in re.split(r'(?i)<\s*eor\s*>', body) if r.strip()]

    tag_re = re.compile(
        r'(?i)<\s*([^:\s>]+)(?:\s*:\s*\d+)?[^>]*>([^<]*)'
    )

    for rec in records:
        fields = {}
        for m in tag_re.finditer(rec):
            tag = m.group(1).strip().upper()
            val = m.group(2).strip()
            # Keep the last occurrence if repeated
            fields[tag] = val
        yield fields


def load_state_totals():
    """Return small mapping of country -> total number of states (per ADIF III.B.12)."""
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


# Data file from https://www.iota-world.org/islands-on-the-air/downloads/download-file.html?path=islands.json
def load_iota_map():
    """
    Load an IOTA reference -> name mapping from iota.json (next to this file).
    Supports either a dict mapping refno->name or a list of objects containing
    'refno' and 'name' keys. Returned keys are upper-cased strings.
    """
    here = os.path.dirname(__file__)
    path = os.path.join(here, "iota.json")
    mapping = {}
    if not os.path.exists(path):
        return mapping
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return mapping

    if isinstance(data, dict):
        for k, v in data.items():
            if k is None:
                continue
            mapping[str(k).strip().upper()] = v
        return mapping

    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            ref = item.get("refno") or item.get("RefNo") or item.get("ref") or item.get("id")
            name = item.get("name") or item.get("Name") or item.get("island")
            if ref and name:
                mapping[str(ref).strip().upper()] = name
    return mapping


def summarize(path, callsign=None, home_grid=None):
    """Parse ADIF file at path and write a DX report and per-band maps."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()

    # collect report lines and write once at the end to dx-report.txt (overwrite)
    out_lines = []

    def w(line=""):
        out_lines.append(line + "\n")

    w(
        f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    country_counts = Counter()
    states_by_country = defaultdict(set)
    cnty_by_country_state = defaultdict(lambda: defaultdict(set))
    grid4_counts = Counter()
    grid4_by_band = defaultdict(Counter)
    iota_values = set()

    # load IOTA mapping once
    iota_map = load_iota_map()

    for fields in parse_adif(content):
        country = fields.get("COUNTRY") or ""
        state = fields.get("STATE") or ""
        cnty = fields.get("CNTY") or ""
        gridsq = fields.get("GRIDSQUARE") or fields.get("GRID") or ""
        band = fields.get("BAND") or ""
        iota = fields.get("IOTA") or ""

        if country:
            country_counts[country] += 1
            if state:
                states_by_country[country].add(state)
                if cnty:
                    cnty_by_country_state[country][state].add(cnty)
            else:
                # still track CNTY even if STATE missing (group under empty state)
                if cnty:
                    cnty_by_country_state[country][""].add(cnty)

        if gridsq and len(gridsq) >= 4:
            g4 = gridsq[:4].upper()
            grid4_counts[g4] += 1
            band_key = band.strip().upper() if band and band.strip() else "(no BAND)"
            grid4_by_band[band_key][g4] += 1

        if iota:
            iota_values.add(iota.strip().upper())

    total_countries = len(country_counts)
    w(f"LotW QSLed Countries ({total_countries}/340)")
    # sort primarily by count (descending), secondarily by country name (ascending)
    for country, cnt in sorted(country_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        w(f"  {country}: {cnt}")

    w("")
    w("QSLed States (by country):")
    all_countries = set(states_by_country.keys()) | set(country_counts.keys())

    state_totals = load_state_totals()
    for country in sorted(all_countries):
        states = sorted(states_by_country.get(country, []))
        present = len(states)
        total = state_totals.get(country.upper())
        if states and total is not None and total != 0:
            w(f"  {country}: {present}/{total}")
            for state in states:
                w(f"    - {state}")

    w("")
    w("QSLed Counties (by country / state):")
    for country in sorted(cnty_by_country_state):
        for state in sorted(cnty_by_country_state[country]):
            state_label = state if state else "(no STATE)"
            for cnty in sorted(cnty_by_country_state[country][state]):
                if country.strip().upper() == "JAPAN":
                    continue
                w(f"  {country} - {state_label} - {cnty}")

    w("")
    w("QSLed IOTA:")
    if iota_values:
        for iota in sorted(iota_values):
            ref = iota.strip().upper()
            if not ref:
                continue
            # exclude undesired placeholder value
            if ref == "SA-999":
                continue
            # direct lookup
            name = iota_map.get(ref)
            # try numeric-only form if not found
            if not name:
                digits = "".join(ch for ch in ref if ch.isdigit())
                if digits:
                    name = iota_map.get(digits) or iota_map.get(str(int(digits)))
            if not name:
                # try uppercase lookup (already uppercased above) but keep for robustness
                name = iota_map.get(ref.upper())
            if name:
                w(f"  {ref} -> {name}")
            else:
                w(f"  {ref}")
    else:
        w("  (none)")

    # Per-band maps
    report_time = datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    if grid4_by_band:
        for band in sorted(grid4_by_band.keys()):
            if callsign:
                label = (
                    f"QSLed grid squares for {callsign.upper()} on {band} "
                    f"as of {report_time}"
                )
            else:
                label = f"QSLed grid squares on {band} as of {report_time}"
            gridsquare.render_from_counts(
                grid4_by_band[band],
                output_path=f"{callsign}_map_{band}.png",
                highlight_locator=home_grid,
                label=label,
            )

    if callsign:
        label_all = (
            f"LotW QSLed grid squares for {callsign.upper()} on all bands "
            f"as of {report_time}"
        )
    else:
        label_all = f"LotW QSLed grid squares on all bands as of {report_time}"

    gridsquare.render_from_counts(
        grid4_counts,
        output_path=f"{callsign}_map_all.png",
        highlight_locator=home_grid,
        label=label_all,
    )

    # write report to dx-report.txt (overwrite)
    try:
        with open("dx-report.txt", "w", encoding="utf-8") as repf:
            repf.writelines(out_lines)
        print("Wrote dx-report.txt")
    except Exception as exc:
        print(f"Error writing dx-report.txt: {exc}")


def main():
    """CLI entrypoint."""
    if len(sys.argv) != 4:
        print("Usage: python3 dx-report.py path/to/file.adi [CALLSIGN] [HOME_GRID]")
        sys.exit(2)

    path = sys.argv[1]
    callsign = sys.argv[2]
    home_grid = sys.argv[3]
    summarize(path, callsign=callsign.lower(), home_grid=home_grid.upper())


if __name__ == "__main__":
    main()
