#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

def maidenhead_bbox(locator):
    """
    Return (lon_min, lon_max, lat_min, lat_max) for a 4-character Maidenhead locator.
    """
    loc = locator.strip().upper()
    if len(loc) < 4:
        raise ValueError("Locator must be at least 4 characters")
    a, b, c, d = loc[0], loc[1], loc[2], loc[3]
    lon_field = ord(a) - ord('A')           # 20° increments
    lat_field = ord(b) - ord('A')           # 10° increments
    lon_sq = int(c)                         # 2° increments
    lat_sq = int(d)                         # 1° increments

    lon_min = -180 + lon_field * 20 + lon_sq * 2
    lat_min = -90 + lat_field * 10 + lat_sq * 1
    lon_max = lon_min + 2
    lat_max = lat_min + 1
    return lon_min, lon_max, lat_min, lat_max

def add_maidenhead_grid(ax, lon_step=2, lat_step=1, line_kwargs=None):
    """
    Add boundaries for every 4-character Maidenhead grid square (2° x 1° cells).
    Draws vertical lines every lon_step degrees and horizontal lines every lat_step degrees.
    Skips specified angles separately for longitude and latitude so 30° longitude is shown.
    """
    if line_kwargs is None:
        line_kwargs = dict(color="gray", linewidth=0.4, alpha=0.6, zorder=5)

    # skip sets applied separately
    skip_lon_angles = {60, 180}          # don't skip 30° longitude anymore
    skip_lat_angles = {30, 60, 180}      # still skip these latitudes

    # vertical lines (constant longitude)
    lats = np.linspace(-90, 90, 361)
    for lon in range(-180, 181, lon_step):
        if abs(lon) in skip_lon_angles:
            continue
        ax.plot([lon] * lats.size, lats, transform=ccrs.PlateCarree(), **line_kwargs)

    # horizontal lines (constant latitude)
    lons = np.linspace(-180, 180, 721)
    for lat in range(-90, 91, lat_step):
        if abs(lat) in skip_lat_angles:
            continue
        ax.plot(lons, [lat] * lons.size, transform=ccrs.PlateCarree(), **line_kwargs)
        

def plot_world(output_path, highlight_locator, filled_locators=None, label="", dpi=300):
    if filled_locators is None:
        filled_locators = ["PM95", "DM13", "FM99"]

    proj = ccrs.Mollweide()
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(1, 1, 1, projection=proj)
    ax.set_global()

    # simple styling
    ax.add_feature(cfeature.OCEAN.with_scale("110m"), facecolor="#cfe8ff")
    ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor="#f0e6c8")
    ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.5)
    ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.3)

    # disable cartopy gridline labels and default x/y lines (we draw our own grid)
    ax.gridlines(draw_labels=False)

    add_maidenhead_grid(ax)

    # fill provided locators (highlighter yellow)
    for loc in filled_locators:
        if not loc:
            continue
        try:
            lon_min, lon_max, lat_min, lat_max = maidenhead_bbox(loc)
        except Exception:
            # skip invalid locators silently
            continue
        xs = [lon_min, lon_max, lon_max, lon_min]
        ys = [lat_min, lat_min, lat_max, lat_max]
        ax.fill(xs, ys, transform=ccrs.PlateCarree(),
                facecolor="purple", edgecolor="purple", alpha=0.45, zorder=8)

    # highlight requested 4-char Maidenhead square in red (drawn on top)
    if highlight_locator:
        try:
            lon_min, lon_max, lat_min, lat_max = maidenhead_bbox(highlight_locator)
            xs = [lon_min, lon_max, lon_max, lon_min]
            ys = [lat_min, lat_min, lat_max, lat_max]
            ax.fill(xs, ys, transform=ccrs.PlateCarree(), facecolor="red", edgecolor="red", alpha=0.45, zorder=10)
        except Exception:
            pass

    # add label text at the bottom center of the figure
    fig.text(0.9, 0.01, label, ha='right', va='bottom', fontsize=9, color='black')

    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved map to: {output_path}")

def render_from_counts(grid4_counts, output_path, highlight_locator=None, label=""):
    """
    Convenience wrapper to render a map using the keys of grid4_counts as the locators to highlight.
    grid4_counts: mapping-like with 4-char grid square keys (e.g. dict or Counter).
    """
    if grid4_counts is None:
        filled_locators = None
    else:
        # ensure stable ordering
        filled_locators = list(grid4_counts.keys())
    plot_world(output_path=output_path, highlight_locator=highlight_locator,
               filled_locators=filled_locators, label=label)

if __name__ == "__main__":
    # keep the previous default behaviour when run directly
    plot_world()