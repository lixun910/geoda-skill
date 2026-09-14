# Confirm the tool's parameters before running it

Every GeoDa analysis tool takes parameters that change the result — which
variable, which weights, how many clusters, how many classes. A wrong guess
wastes a run and can leave the user with a map they did not want. So **confirm
the parameters first, then compute.**

## The rule

1. **Confirm before every analysis call**, not just LISA. Histograms, maps,
   clustering, global autocorrelation, regression — all of them.
2. **Ask only for what the request left unspecified.** A fully specified prompt
   ("run LISA on HR90 with queen weights") needs no prompt — just run it. Ask
   about the gaps, and nothing else.
3. **Ask sequentially — one decision per question card.** Variable first, then
   weights, then any tool-specific parameter (clustering `k`, classification
   `num_categories`, …). Do not bundle them into one many-part card.
4. **Offer the real choices as options**, with sensible defaults marked. The
   user should be able to accept the default, not retype it.

## How to ask

Use the client's structured question tool — in Claude Code that is
`AskUserQuestion` (renders as a multiple-choice card, which can also render as a
plain question). If the client has no such tool (e.g. Codex CLI), ask the same
question in plain text and **stop until the user answers**.

Derive the options from the open project, not from memory:

- Variables → `table/list_columns` (skip id / name / label fields; offer the
  numeric fields, and use `table/univariate_stats` if a name is cryptic).
- Weights → the id returned by the earlier `weights/create` (`weights/list`).
- Anything already set in the app → `project/status`.

## Recommended order (the LISA example)

> "Run a LISA analysis using `~/Downloads/natregimes/natregimes.shp` in GeoDa."

1. Open/confirm the project (`project/status`, launching with the path if needed).
2. `table/list_columns` → **ask: which variable?** (e.g. HR90, HR80, RD90…)
3. **ask: which spatial weights?** — Queen (default), Rook, K-Nearest Neighbors,
   Distance band, Kernel; then the follow-up for the chosen type (KNN `k`,
   distance threshold).
4. `weights/create` → keep the id.
5. `lisa/local_moran` → the result.
6. **ask: build a portable kepler.gl map?** (see Step 7 of `SKILL.md`) — only if
   the user did not already ask for one.

## Per-tool parameters to confirm

Parameter names below are the MCP tool's own keys. "(default …)" marks the value
to pre-select and state when asking.

### Spatial weights — `weights/create`

| Parameter | Ask for | Options / default |
|-----------|---------|-------------------|
| `type` | weights type | queen (used when omitted), rook, knn, distance, kernel |
| `order` | contiguity order | 1 (used when omitted), 2 … — only when a higher order matters |
| `k` | neighbors per observation | 6 (used when omitted) — knn only |
| `distance_threshold` | distance band | e.g. the min distance keeping all units connected — distance only |
| `kernel` | kernel function | triangular (used when omitted), uniform, epanechnikov, quartic, gaussian — kernel only |
| `is_arc` / `is_mile` | distance units | both false (used when omitted) — great-circle vs planar, miles vs map units |

### Global spatial autocorrelation — `global/moran`, `global/geary`, `global/general_g`

| Parameter | Ask for | Default |
|-----------|---------|---------|
| `column` | variable | — (required) |
| `weights` | weights id | — (required) |
| `permutations` | permutation count | 999 |

### Local spatial autocorrelation (LISA) — `lisa/local_moran`, `lisa/local_geary`, `lisa/local_g`

| Parameter | Ask for | Default |
|-----------|---------|---------|
| `column` | variable | — (required) |
| `weights` | weights id | — (required) |
| `lisa_type` | univariate / bivariate / differential / eb_rate_standardized | univariate |
| `second_column` | the second variable | required for bivariate / differential |
| `permutations` | permutation count | 999 |
| `significance_cutoff` | significance level | 0.05 |
| `row_standardize` | row-standardize? | true |
| `gstar` | G or G* (self included) | false (`lisa/local_g` only) |

> **Cluster counts:** `local_moran`'s `cluster` field reports *unfiltered*
> quadrants. Filter by the `significance` field before reporting counts (see
> [lisa-kepler-map.md](lisa-kepler-map.md)).

### Spatial clustering — `cluster/skater`, `cluster/redcap`, `cluster/schc`, `cluster/azp`, `cluster/maxp`, `cluster/spatial_kmeans`, `cluster/spectral`

| Tool | Ask for | Default |
|------|---------|---------|
| `skater` | `columns` (variables), `weights`, `k` regions, `boundary` (optional) | k = 3; no method choice |
| `redcap` | `columns`, `weights`, `k`, `method` (firstorder, fullorder_ward, fullorder_alk, fullorder_clk, singlelink, avglink, completelink) | k = 3; `method` uses firstorder when omitted |
| `schc` | `columns`, `weights`, `k`, `method` (singlelink / avglink / completelink) | k = 3; `method` uses singlelink when omitted |
| `azp` | `columns`, `weights`, `k`, `method` (greedy / tabu / sa) | k = 3; `method` uses greedy when omitted |
| `maxp` | `columns`, `weights`, `bound_variable`, `min_bound` | — (bound variable + min bound required) |
| `spatial_kmeans` | `columns`, `weights`, `k`, `init` (kmeans++ / random) | k = 3; `init` uses random when omitted (GeoDa's desktop dialog offers KMeans++, worth mentioning) |
| `spectral` | `columns`, `weights`, `k` | k = 3 |

### Density clustering — `cluster/dbscan`, `cluster/hdbscan`

| Parameter | Ask for | Default |
|-----------|---------|---------|
| `columns` | variables | — (required) |
| `eps` | neighborhood radius (dbscan) | estimated from data if omitted — ask whether to estimate or set it |
| `minpts` | min points per core | 4 |

### Classical clustering — `cluster/kmeans`, `cluster/kmedians`, `cluster/pam`, `cluster/hierarchical`, `cluster/pca`, `cluster/mds`, `cluster/tsne`

| Tool | Ask for | Default |
|------|---------|---------|
| `kmeans` / `kmedians` / `pam` | `columns`, `k` | k = 3 |
| `hierarchical` | `columns`, `k`, `method` (single / complete / average / ward) | k = 3; `method` uses average when omitted |
| `pca` / `mds` | `columns` | — |
| `tsne` | nothing (no parameters) | — |

### Maps and classification — `window/create_map`, `map/quantile`, `map/natural_breaks`, `map/equal_intervals`, `map/percentile`, `map/stddev`, `map/unique_values`, `map/rates_*`

| Parameter | Ask for | Default |
|-----------|---------|---------|
| `column` | variable | — (required) |
| `theme` | classification | quantile (used when omitted) / natural_breaks / equal_intervals / percentile / stddev / unique_values / no_theme |
| `num_categories` | number of classes | 5 |
| `smoothing` | rate smoothing | no_smoothing (used when omitted), raw_rate, excess_risk, empirical_bayes, spatial_rate, spatial_empirical_bayes |
| `weights` | weights id | required when `smoothing` needs neighbors |

### LISA map — `window/create_lisa_map`

Same parameters as `lisa/local_moran`, plus `map_type` (cluster — default — or
significance). Confirm the variable, weights, and map type.

### EDA plots — `explore/histogram`, `explore/boxplot`, `explore/scatterplot`, `explore/bubble_chart`, `explore/3d_scatter`, `explore/pcp`, `explore/scatterplot_matrix`, `explore/line_chart`

| Tool | Ask for |
|------|---------|
| `histogram` / `boxplot` | one variable |
| `scatterplot` | two variables (x, y) |
| `bubble_chart` | three variables (x, y, size) |
| `3d_scatter` | three variables (x, y, z) |
| `pcp` | the set of variables to compare |
| `scatterplot_matrix` / `line_chart` | nothing (no parameters) |

> **Histograms and bin count.** GeoDa's histogram chooses its own bins — the MCP
> tool has no bin-count parameter, so there is nothing to ask beyond the
> variable. Do not invent a `bins` argument; it does not exist. (Class counts
> that *are* configurable live on the map tools, as `num_categories`.)

### Regression — `regress/classic`

| Parameter | Ask for | Default |
|-----------|---------|---------|
| `dependent` | the y variable | — (required) |
| `independent` | the x variable(s) | — (required) |
| `include_constant` | include an intercept? | true |

## After the analysis

When a LISA result comes back, and the user did not already ask for a portable
map, **ask whether to build a kepler.gl HTML map** before doing it — see Step 7
of `SKILL.md` and [lisa-kepler-map.md](lisa-kepler-map.md).
