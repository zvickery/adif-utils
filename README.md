# adif-utils

Simple utility to generate a DX report and Maidenhead-grid maps from an ADIF file.

Features
- Parse an ADIF file and produce a text report (`dx-report.txt`) with:
  - per-country counts
  - states-by-country with III.B.12 totals (if provided)
  - counties (CNTY) listing
- Produce per-band and overall Maidenhead 4-character grid maps (PNG) using Cartopy/Matplotlib.
- Maps highlight a "home" grid and fill reported grids with a highlighter color and optional bottom label.

Requirements
- Python 3.14+
- See `requirements.txt` in this folder. Recommended install:
  - With pip:
    pip install -r requirements.txt
  - If using conda (recommended for cartopy):
    conda install -c conda-forge cartopy matplotlib numpy pytz

Files
- `dx-report.py` — CLI entrypoint. Reads ADIF, writes `dx-report.txt`, and renders maps.
- `gridsquare.py` — map rendering helpers (Maidenhead grid handling + map output).
- `requirements.txt` — python package requirements.

Usage (CLI)
- Basic:
  python3 dx-report.py path/to/log.adi CALLSIGN HOME_GRID
  - `CALLSIGN` (e.g. K0ABC) is used for output map filenames and labels.
  - `HOME_GRID` (4-char Maidenhead, e.g. FN31) will be highlighted / used as map center.

- Example:
  python3 dx-report.py ~/logs/mylog.adi K0ABC FN31

Outputs
- `dx-report.txt` — overwritten each run, contains the textual DX report.
- `<CALLSIGN>_map_all.png` — overall map showing all reported 4-char grids.
- `<CALLSIGN>_map_<BAND>.png` — per-band maps (if band data present).

Programmatic usage
- From Python you can call the renderer directly:
  from gridsquare import render_from_counts
  render_from_counts(grid4_counts, output_path="out.png", highlight_locator="FN31", label="My label")

Notes
- The per-country "states total" values are looked up from a small builtin mapping (ADIF III.B.12) and can be extended by adding a `state_totals.json` next to the scripts (simple JSON mapping Country -> integer).
- Cartopy can be challenging to install; use conda-forge on macOS / Linux to simplify geospatial dependencies.

License
- No license specified. Use/modify as needed.
```
