#!/usr/bin/env python3
"""Render a GeoDa LISA result as an interactive kepler.gl map.

Input: a GeoJSON whose features carry, per row (in GeoDa's row order):
  - a cluster category label  (default column "LISA_CAT"), and
  - an optional significance flag (default column "LISA_SIG")

Output: a standalone HTML kepler.gl map with a geojson polygon layer colored by
LISA cluster category, using GeoDa's own palette (so it matches the GeoDa
cluster map), plus a summary panel overlay.

See skill-references/lisa-kepler-map.md for the full procedure and the gotchas
this script works around.

Usage:
  python make_lisa_kepler_map.py INPUT.geojson OUTPUT.html [--var HR90] [--moran 0.388]

Requires: pip install keplergl geopandas
"""
from __future__ import annotations

import argparse
from collections import Counter

import geopandas as gpd
from keplergl import KeplerGl

# GeoDa's canonical LISA cluster palette (GdaColorUtils::GetLISAColors,
# GeoDa/GenUtils.cpp). Category -> (integer index, hex). The integer index is a
# stable 1..5 key so kepler's color scale maps categories 1:1 regardless of label
# sort order — the layer's colorField points at this index, not the label.
PALETTE = [
    ("High-High", 1, "#ff0000"),
    ("Low-Low", 2, "#0000ff"),
    ("Low-High", 3, "#9696ff"),
    ("High-Low", 4, "#ff9696"),
    ("Not significant", 5, "#f0f0f0"),
]
CAT_TO_IDX = {cat: idx for cat, idx, _ in PALETTE}
CAT_TO_COLOR = {cat: color for cat, _, color in PALETTE}
DATASET = "lisa"


def build_config() -> dict:
    return {
        "version": "v1",
        "config": {
            "visState": {
                "layerBlending": "normal",
                "layers": [
                    {
                        "type": "geojson",
                        "config": {
                            "dataId": DATASET,  # must equal the data dict key
                            "label": "Local Moran's I",
                            "isVisible": True,
                            # A GeoDataFrame serializes its geometry under the column
                            # name "geometry" (NOT "_geojson" — that is only for GeoJSON
                            # dict/string input). A wrong name makes kepler silently
                            # render a default uniform layer with no color mapping.
                            "columns": {"geojson": "geometry"},
                            "visConfig": {
                                "opacity": 0.9,
                                "filled": True,
                                "stroked": True,
                                "thickness": 0.5,
                                "strokeColor": [60, 60, 60],
                                "colorRange": {
                                    # "custom" is required for a user palette; type
                                    # "ordinal" with an unknown name falls back to a
                                    # built-in ramp.
                                    "type": "custom",
                                    "name": "LISA cluster",
                                    "category": "Custom",
                                    "colors": [c for _, _, c in PALETTE],
                                },
                            },
                        },
                        # visualChannels is a SIBLING of config, not inside it.
                        "visualChannels": {
                            "colorField": {"name": "LISA_IDX", "type": "integer"},
                            "colorScale": "ordinal",
                        },
                    }
                ],
                "interactionConfig": {
                    "tooltip": {
                        "enabled": True,
                        "fieldsToShow": {DATASET: ["NAME", "LISA_CAT", "LISA_SIG"]},
                    }
                },
            },
            "mapState": {
                "latitude": 39.3, "longitude": -98.0, "zoom": 3.4,
                "bearing": 0, "pitch": 0, "dragRotate": False,
            },
            "mapStyle": {"styleType": "dark-matter"},
        },
    }


def summary_panel(gdf: gpd.GeoDataFrame, variable: str, moran: float | None) -> str:
    counts = Counter(gdf["LISA_CAT"])
    total = len(gdf)
    sig = sum(n for cat, n in counts.items() if cat != "Not significant")
    order = [cat for cat, _, _ in PALETTE]

    rows = ""
    for cat in order:
        n = counts.get(cat, 0)
        rows += (
            f'<div class="lisa-row">'
            f'<span class="lisa-swatch" style="background:{CAT_TO_COLOR[cat]}"></span>'
            f'<span class="lisa-label">{cat}</span>'
            f'<span class="lisa-count">{n:,} ({100 * n / total:.1f}%)</span></div>'
        )

    moran_line = (
        f'<div class="smp-sub">Global Moran\'s I = {moran:g}</div>' if moran is not None else ""
    )
    return f"""
<div id="sample-map-panel">
  <div class="smp-header">Local Moran's I &mdash; {variable}</div>
  <div class="smp-sub">Queen contiguity &middot; p &le; 0.05</div>
  {moran_line}
  <div class="smp-divider"></div>
  <div class="smp-stats">
    <div class="smp-stat"><span class="smp-stat-num">{total:,}</span><span class="smp-stat-lbl">Observations</span></div>
    <div class="smp-stat"><span class="smp-stat-num">{sig:,}</span><span class="smp-stat-lbl">Significant</span></div>
    <div class="smp-stat"><span class="smp-stat-num">{100 * sig / total:.1f}%</span><span class="smp-stat-lbl">Sig. share</span></div>
  </div>
  <div class="smp-divider"></div>
  <div class="smp-rows">{rows}</div>
</div>
<style>
  #sample-map-panel {{
    position: absolute; top: 16px; right: 56px; z-index: 1000;
    width: 300px; padding: 14px 16px;
    background: rgba(36, 39, 48, 0.92); color: #f7f7f7;
    font-family: ff-clan-web-pro, 'Helvetica Neue', Helvetica, sans-serif;
    font-size: 12px; border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  }}
  #sample-map-panel .smp-header {{ font-size: 14px; font-weight: 600; margin-bottom: 2px; }}
  #sample-map-panel .smp-sub {{ font-size: 11px; color: #a0a7b4; }}
  #sample-map-panel .smp-divider {{ height: 1px; background: #3a3f4b; margin: 10px 0; }}
  #sample-map-panel .smp-stats {{ display: flex; justify-content: space-between; }}
  #sample-map-panel .smp-stat {{ display: flex; flex-direction: column; }}
  #sample-map-panel .smp-stat-num {{ font-size: 16px; font-weight: 600; color: #fff; }}
  #sample-map-panel .smp-stat-lbl {{ font-size: 10px; color: #a0a7b4; text-transform: uppercase; letter-spacing: 0.5px; }}
  #sample-map-panel .lisa-row {{ display: flex; align-items: center; padding: 3px 0; }}
  #sample-map-panel .lisa-swatch {{ width: 12px; height: 12px; margin-right: 8px; border-radius: 2px; flex: 0 0 auto; }}
  #sample-map-panel .lisa-label {{ flex: 1; color: #e0e2e7; }}
  #sample-map-panel .lisa-count {{ color: #a0a7b4; font-variant-numeric: tabular-nums; }}
</style>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="GeoJSON with a LISA category column")
    ap.add_argument("output", help="output HTML path")
    ap.add_argument("--var", default="variable", help="variable name, shown in the panel header")
    ap.add_argument("--cat-col", default="LISA_CAT", help="category label column")
    ap.add_argument("--moran", type=float, default=None, help="global Moran's I, shown in the panel")
    args = ap.parse_args()

    gdf = gpd.read_file(args.input)
    if args.cat_col != "LISA_CAT":
        gdf = gdf.rename(columns={args.cat_col: "LISA_CAT"})
    gdf["LISA_IDX"] = gdf["LISA_CAT"].map(CAT_TO_IDX)

    map_1 = KeplerGl(height=700, data={DATASET: gdf}, config=build_config())
    map_1.save_to_html(file_name=args.output, center_map=True)

    # Inject the summary panel at the LAST </body>. The export embeds a literal
    # </body> inside its own template string, so a plain html.replace() would also
    # hit that one and inject the panel into the bundle JS, breaking it.
    panel = summary_panel(gdf, args.var, args.moran)
    with open(args.output, "r", encoding="utf-8") as f:
        html = f.read()
    marker = "</body>"
    i = html.rfind(marker)
    assert i != -1, "no closing </body> found"
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html[:i] + panel + "\n" + marker + html[i + len(marker):])

    print(f"wrote {args.output} | categories: {dict(Counter(gdf['LISA_CAT']))}")


if __name__ == "__main__":
    main()
