# LISA result → standalone kepler.gl map

Turn a GeoDa LISA result (from this skill's MCP tools) into an interactive,
sharable kepler.gl HTML map — colored with **GeoDa's own LISA palette** so it
matches the cluster map GeoDa draws.

Nothing else needs installing: this reference carries the whole procedure,
including the two places kepler.gl's published docs get it wrong for our case.

## Why kepler.gl

GeoDa already draws a LISA cluster map in its app window (`window/create_lisa_map`).
kepler.gl is for when you want a **portable HTML file** the user can open, pan and
zoom, and read with tooltips — or when you want to color the map with GeoDa's
palette outside GeoDa. Compose it with the `keplergl` Python package.

## 1. Get the LISA result from GeoDa

```
weights/create   {"type": "queen"}                              -> weights id
lisa/local_moran {"weights_id": …, "variable": "HR90", "permutations": 999}
```

The result gives, per observation **in dataset row order**, a **cluster code**
(1 = High-High, 2 = Low-Low, 3 = Low-High, 4 = High-Low; 5/6 = neighborless /
undefined) plus a **significance** flag (p ≤ 0.05). Treat every non-significant
observation — and the neighborless/undefined ones — as **Not significant**.

## 2. Attach the result to the dataset — row order matters

Build one category label and one stable integer index per feature, keeping features
in the **same order** GeoDa used (attach the arrays positionally; do not sort or
join):

| category        | index | source                                  |
|-----------------|-------|-----------------------------------------|
| High-High       | 1     | code 1, significant                     |
| Low-Low         | 2     | code 2, significant                     |
| Low-High        | 3     | code 3, significant                     |
| High-Low        | 4     | code 4, significant                     |
| Not significant | 5     | not significant, or neighborless/undefined |

Write that out as GeoJSON (e.g. GeoDa's `table/export`, or serialize it yourself).
The **integer index** is what makes kepler's palette map 1:1 — see step 4.

## 3. GeoDa's LISA palette (authoritative)

Use these exact colors so the kepler map matches the GeoDa cluster map. They are
`GdaColorUtils::GetLISAColors` from GeoDa's source (`GeoDa/GenUtils.cpp`):

| category        | hex       |
|-----------------|-----------|
| High-High       | `#ff0000` |
| Low-Low         | `#0000ff` |
| Low-High        | `#9696ff` |
| High-Low        | `#ff9696` |
| Not significant | `#f0f0f0` |

## 4. Build the map

```bash
pip install keplergl geopandas
```

A ready-to-adapt generator is at
[examples/make_lisa_kepler_map.py](../examples/make_lisa_kepler_map.py). The config
points that matter:

```python
layer = {
    "type": "geojson",
    "config": {
        "dataId": "lisa",                          # must equal the data dict key
        "label": "Local Moran's I",
        "columns": {"geojson": "geometry"},        # see gotcha 1
        "visConfig": {
            "opacity": 0.9, "filled": True, "stroked": True, "thickness": 0.5,
            "strokeColor": [60, 60, 60],
            "colorRange": {
                "type": "custom",                  # see gotcha 2
                "name": "LISA cluster",
                "category": "Custom",
                "colors": ["#ff0000", "#0000ff", "#9696ff", "#ff9696", "#f0f0f0"],
            },
        },
    },
    "visualChannels": {                            # sibling of config, NOT inside it
        "colorField": {"name": "LISA_IDX", "type": "integer"},
        "colorScale": "ordinal",
    },
}

map_1 = KeplerGl(height=700, data={"lisa": gdf}, config=config)
map_1.save_to_html(file_name="lisa_map.html", center_map=True)
```

## Gotchas

1. **A GeoDataFrame's geometry column is `geometry`, not `_geojson`.**
   kepler.gl's docs — and the kepler.gl skill — say `columns.geojson` must be
   `"_geojson"`. That is true only for GeoJSON **dict/string** input. A
   `GeoDataFrame` serializes its geometry under the column's own name
   (`geometry`). If the name does not match, kepler does **not** raise — it
   silently renders a default layer with a **uniform fill and no color mapping**,
   which looks like "the colors didn't apply". Confirm the real name by reading it
   back out of the exported HTML:
   `window.__keplerglDataConfig.data.<name>.columns`.

2. **A custom palette needs `colorRange.type: "custom"`.**
   Using `"ordinal"` with an arbitrary `name` makes kepler fall back to a built-in
   ramp (a brown sequential gradient), not your colors.

3. **Inject the info panel at the *last* `</body>`.**
   The export embeds a literal `</body>` inside its own HTML-template string, so
   `html.replace("</body>", panel + "</body>")` hits **two** spots and injects the
   panel HTML *into the bundle JS* → `SyntaxError: Invalid or unexpected token`,
   and the map never mounts. Inject at the real closing tag instead:

   ```python
   i = html.rfind("</body>")
   html = html[:i] + panel + "</body>" + html[i + len("</body>"):]
   ```

## 5. Summary panel (optional)

Inject an HTML/CSS overlay just before the final `</body>` with the cluster counts
and the global Moran's I. The pattern (position `right: 56px` to clear kepler's
controls) is the kepler.gl skill's `summary-panel.md`; the example script includes a
ready version.

## 6. Verify it actually rendered

The map is only done when the polygons paint. In a normal browser just open the
file. In a **headless or hidden** browser pane it will look blank for a
non-obvious reason: maplibre and deck.gl paint only inside
`requestAnimationFrame`, and a hidden pane fires **zero** rAF callbacks — so the
canvas is empty even though the map is fine. Verify by injecting two shims before
the bundle runs, then reading the canvas:

```js
// 1) let WebGL keep the frame   2) drive renders without rAF
const g = HTMLCanvasElement.prototype.getContext;
HTMLCanvasElement.prototype.getContext = function (t, a) {
  if (String(t).indexOf('webgl') === 0) a = Object.assign({}, a, {preserveDrawingBuffer: true});
  return g.call(this, t, a);
};
window.requestAnimationFrame = cb => setTimeout(() => cb(performance.now()), 16);
```

Then `canvas.toDataURL('image/png')` (or `gl.readPixels`) returns the real frame —
compare it against the polygon counts. If the polygons come out a single uniform
color, re-check `columns.geojson` (gotcha 1).

## Notes

- keplergl's export embeds a Google Analytics beacon. On `file://` or a localhost
  origin it logs a harmless CORS error. Don't try to strip it by text surgery — the
  same snippet also appears inside the bundle, so the edit corrupts the file.
- The default `dark-matter` basemap is dark, and GeoDa's "Not significant" is a
  near-white `#f0f0f0`, so the map reads light-on-dark. Use `positron` to match
  GeoDa's white background more closely.
