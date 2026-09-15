---
name: geoda-mcp
description: Set up and connect to GeoDa's built-in MCP server so this agent can run spatial analysis in GeoDa (spatial weights, global and local spatial autocorrelation / LISA, spatial clustering, regression, maps) over MCP, and turn a LISA result into a standalone kepler.gl map. Use when the user asks to run spatial autocorrelation, LISA, Moran's I, or spatial clustering "in GeoDa" / "with GeoDa", when they want a LISA cluster map as a portable kepler.gl HTML file, or when the geoda MCP tools are not yet available in this session.
---

# GeoDa MCP bootstrap

GeoDa is a desktop app for spatial data analysis — spatial weights, global and
local spatial autocorrelation, LISA cluster maps, spatial clustering, regression.
It hosts a **built-in MCP server** that starts with the app, binding
`http://127.0.0.1:8765/mcp` and recording the port it actually bound in
`~/.geoda/mcp.json`. Once connected, this agent drives GeoDa's analysis tools
directly and the maps and plots render in the app window.

This skill downloads, installs, launches, and registers that app. It is
**idempotent** — run the first step and skip ahead if the tools are already
available.

> The MCP server ships on the `feat-mcp-server` line (PR #2586) and is not in a
> public release yet, so Step 1 pulls the build from CI.

## Step 0 — Are we already connected?

If this session already exposes GeoDa's MCP tools (`project/status`, `file/open`,
`table/list_columns`, `weights/create`, `global/moran`, `lisa/local_moran`,
`cluster/skater`, `window/create_map`, …), setup is done: **skip to Step 5** and
answer the original request.

Check from the CLI too:

```bash
claude mcp list
```

If `geoda` is listed and connected, skip to Step 5. If it is listed but
disconnected, the app is not running — continue at Step 3.

## Step 1 — Get the MCP-enabled build

macOS only for now (the CI workflow publishes macOS `.dmg`s). Two routes, in
order:

**A. A published build** — if `GEODA_DMG_URL` is set, use it (no auth needed):

```bash
if [ -n "${GEODA_DMG_URL:-}" ]; then
  curl -fL "$GEODA_DMG_URL" -o /tmp/GeoDa.dmg
fi
```

**B. The CI artifact** (default) — needs the `gh` CLI, authenticated; artifacts
expire. `arm64` on Apple Silicon, `x86_64` on Intel:

```bash
ARCH=$(uname -m)                                  # arm64 or x86_64
REPO="${GEODA_REPO:-GeoDaCenter/geoda}"
DEST="${GEODA_DEST:-/tmp/geoda-build}"

if [ ! -f /tmp/GeoDa.dmg ]; then
  RUN="${GEODA_RUN_ID:-$(gh run list -R "$REPO" -w osx_build.yml --status success \
        -L 20 --json databaseId -q '.[0].databaseId')}"
  ART=$(gh api "repos/$REPO/actions/runs/$RUN/artifacts" -q '.artifacts[].name' \
        | grep -F "$ARCH" | head -1)
  rm -rf "$DEST" && mkdir -p "$DEST"
  gh run download "$RUN" -R "$REPO" -n "$ART" -D "$DEST"
  cp "$(find "$DEST" -name '*.dmg' | head -1)" /tmp/GeoDa.dmg
  echo "downloaded $ART from $REPO run $RUN"
fi
```

If `gh` is missing or not authenticated, ask the user for the `.dmg` path (or set
`GEODA_DMG_URL`) — do not guess a download link.

The default `REPO` is `GeoDaCenter/geoda`. Builds it runs on its own branches and
tags are **signed and notarized**; builds produced by a fork's pull request are
unsigned, because secrets are withheld from fork PRs. The auto-start change lives
on `feat-mcp-server` (PR #2586), so until that merges into `master` the newest
successful run in that repo is the one to take. To be explicit, pin `GEODA_RUN_ID`
to a run (and `GEODA_REPO` if you are building from a fork).

## Step 2 — Install

```bash
hdiutil attach /tmp/GeoDa.dmg -nobrowse -mountpoint /tmp/geoda-dmg
rm -rf "/Applications/GeoDa.app"
cp -R /tmp/geoda-dmg/GeoDa.app /Applications/
hdiutil detach /tmp/geoda-dmg
```

Builds from `GeoDaCenter/geoda`'s own branches are signed and notarized (`spctl -a
-vv -t exec` says `accepted` / `Notarized Developer ID`) and launch normally;
fork-PR builds are unsigned. A file fetched with `gh` or `curl` carries no
quarantine flag, so this is usually a no-op — only if the launch in Step 3 is
blocked, clear it and say in your summary that this bypassed Gatekeeper:

```bash
xattr -dr com.apple.quarantine "/Applications/GeoDa.app"
```

(After the app has run once, `codesign --verify` reports a broken seal: GeoDa
writes `logger.txt` into its own `Contents/Resources` at startup. That is normal
and does not stop it launching.)

## Step 3 — Launch, opening the data set

GeoDa takes the data set path as a command-line argument, which avoids the native
file dialog an agent cannot drive:

```bash
open -a GeoDa "/absolute/path/to/data.geojson"
```

If GeoDa is already running, `open` routes the file to the running app (the same
path "Open With" uses) and it opens as a new project. If you have no data set
yet, ask the user for one, or use any GeoJSON / Shapefile on disk.

Starting the app also starts the MCP server. Wait for it and read the port it
bound:

```bash
for i in $(seq 1 30); do [ -f ~/.geoda/mcp.json ] && break; sleep 1; done
cat ~/.geoda/mcp.json 2>/dev/null || echo "discovery file not written yet"
```

If the discovery file never appears, the build predates the auto-start change —
relaunch passing the port explicitly (works on every MCP-enabled build):

```bash
osascript -e 'quit app "GeoDa"' 2>/dev/null; sleep 2
open -a GeoDa --args --mcp-port 8765 "/absolute/path/to/data.geojson"
```

## Step 4 — Confirm the MCP URL

The default URL is `http://127.0.0.1:8765/mcp`. The app records the port it
actually bound in `~/.geoda/mcp.json` — if 8765 was taken it falls back to a
nearby port, so read the file (or probe):

```bash
URL=$(sed -n 's/.*"url":"\([^"]*\)".*/\1/p' ~/.geoda/mcp.json 2>/dev/null)
if [ -z "$URL" ]; then
  for p in $(seq 8765 8774); do
    code=$(curl -s -m 1 -o /dev/null -w '%{http_code}' -X POST \
      -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' \
      -d '{"jsonrpc":"2.0","id":1,"method":"ping"}' "http://127.0.0.1:$p/mcp")
    [ "$code" = "200" ] && { URL="http://127.0.0.1:$p/mcp"; break; }
  done
fi
echo "$URL"
```

Verify the server answers before registering — a plain `GET /` replies
`GeoDa MCP server running` and a `ping` returns `{}`:

```bash
curl -s http://127.0.0.1:8765/          # GeoDa MCP server running
curl -s -X POST -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}' \
  "http://127.0.0.1:8765/mcp"           # {"jsonrpc":"2.0","id":1,"result":{}}
```

## Step 5 — Register with this client

```bash
claude mcp add --transport http geoda http://127.0.0.1:8765/mcp
```

```bash
codex mcp add geoda --url http://127.0.0.1:8765/mcp
```

Use the real URL from Step 4. Then **tell the user to restart the client** (Codex
requires a full restart; Claude Code needs a restart or an in-session `/mcp`
reconnect) so the new server is loaded. After that restart, re-run the original
request — there are no more manual steps.

## Step 6 — Drive it

Once GeoDa's tools are available:

**Confirm the parameters first — one decision at a time.** Every tool below takes
parameters that change the result, so ask the user before calling it. Ask **only**
for what the request left unspecified — a fully specified prompt ("LISA on HR90,
queen weights") needs no question. Ask **sequentially**, one card per decision,
using the client's structured question tool (`AskUserQuestion` in Claude Code;
plain text, then wait, in clients that have none). The canonical LISA order is
**variable → spatial weights → run**; other analyses follow the same shape
(clustering asks for `k`, a choropleth for `num_categories`, a scatter plot for
its x/y variables). Derive the options from the open project — variables from
`table/list_columns`, weights from the `weights/create` id. The full per-tool
list of what to confirm, with defaults, is in
[confirm-parameters.md](skill-references/confirm-parameters.md).

**If the request names no analysis, ask for that first.** A vague prompt ("run
exploratory data analysis on HR60", "look at crime in the south") fixes the data
and maybe the variable but not the tool, and the per-tool list cannot be
consulted until one is chosen. So make the *analysis* the first card — offer the
few that fit the request (for a single variable, typically histogram, boxplot,
choropleth, and Moran's I / LISA) — then confirm that tool's parameters as above.
`confirm-parameters.md` has the same rule with the candidate set spelled out.

1. `project/status` — confirm a data set is open (title, path, dimensions). If
   nothing is open, re-launch with the path (Step 3), or call `file/open` and ask
   the user to pick the file in the dialog.
2. `table/list_columns` — see the fields; `table/univariate_stats` for a column.
3. `weights/create` (`{"type":"queen"}`) — build a spatial weights matrix and
   keep its id; the spatial-statistics tools take that id.
4. Global autocorrelation: `global/moran`, `global/geary`, `global/general_g`.
   Local: `lisa/local_moran`, `lisa/local_geary`, `lisa/local_g`.
5. Clustering: `cluster/skater`, `cluster/redcap`, `cluster/maxp`, `cluster/azp`,
   `cluster/spatial_kmeans`, `cluster/dbscan`, `cluster/hdbscan`, …; classical
   `cluster/kmeans`, `cluster/pca`, `cluster/tsne`, `cluster/hierarchical`.
6. Maps and plots render in the app window: `map/quantile`,
   `map/natural_breaks`, `map/rates_eb`, `explore/histogram`,
   `explore/scatterplot`, `window/create_map`, `window/create_lisa_map`, …
7. Export results with `table/export` or `file/export` (GeoJSON, GeoPackage,
   Shapefile, CSV, KML).

The GeoDa tools are **GUI-bound**: they act on the project open in the app window,
and maps and plots appear there. Read `tools/list` for the full set and each
tool's parameters.

## Step 7 — Visualize a LISA result as a standalone kepler.gl map

GeoDa draws LISA cluster maps in its own window. When the user wants a **portable,
interactive map** — or one colored with GeoDa's exact LISA palette — build a
standalone kepler.gl HTML file from the same LISA result. This needs no kepler.gl
plugin: the reference is self-contained.

**Ask first.** When a LISA result comes back, if the user did not already ask for
a portable map, **ask whether they want one** (a simple yes/no) before building
it — do not generate the HTML unprompted.

- Full procedure, GeoDa's palette, the kepler layer config, and the traps that make
  an export render uniformly or not mount at all:
  [lisa-kepler-map.md](skill-references/lisa-kepler-map.md)
- Runnable generator: [make_lisa_kepler_map.py](examples/make_lisa_kepler_map.py)

## Notes

- **Port:** the server binds 8765 by default, falling back to 8765–8774 and then
  an OS-assigned port; `~/.geoda/mcp.json` always records the real one, and it is
  removed when the app quits — so a missing file means the app is not running. On
  Windows the file is `%USERPROFILE%\.geoda\mcp.json`.
- **Turning it off:** launch with `--no-mcp`, or set `GEODA_MCP_ENABLED=0`.
  Override the port with `--mcp-port N` or `GEODA_MCP_PORT=N`.
- **Auth:** the MCP listener is loopback-only (127.0.0.1) with no token — anyone
  with local access to the machine can drive the app while it is running.
- **Installing this skill:** an agent-skills client loads a skill from a
  `<skills-dir>/<name>/SKILL.md` directory, so fetch this file into that shape:

```bash
mkdir -p ~/.claude/skills/geoda-mcp
curl -fsSL https://raw.githubusercontent.com/lixun910/geoda-skill/main/.agents/skills/geoda-mcp/SKILL.md \
  -o ~/.claude/skills/geoda-mcp/SKILL.md
# Codex / other agent-skills clients read the same file:
mkdir -p ~/.agents/skills/geoda-mcp
cp ~/.claude/skills/geoda-mcp/SKILL.md ~/.agents/skills/geoda-mcp/SKILL.md
```

If you already have this repo checked out, copying `.agents/skills/geoda-mcp/`
to either of those directories works the same way.
