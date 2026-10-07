---
name: geoda-mcp
description: Set up and connect to GeoDa's built-in MCP server so this agent can run spatial analysis in GeoDa (spatial weights, global and local spatial autocorrelation / LISA, spatial clustering, regression, maps) over MCP, open a local data set (shapefile, GeoJSON, GeoPackage) in the running app, and turn a LISA result into a standalone kepler.gl map. Use when the user asks to run spatial autocorrelation, LISA, Moran's I, or spatial clustering "in GeoDa" / "with GeoDa", when they ask GeoDa to load a local data file, when they want a LISA cluster map as a portable kepler.gl HTML file, or when the geoda MCP tools are not yet available in this session.
---

# GeoDa MCP bootstrap

GeoDa is a desktop app for spatial data analysis — spatial weights, global and
local spatial autocorrelation, LISA cluster maps, spatial clustering, regression.
It hosts a **built-in MCP server** that starts with the app, binding
`http://127.0.0.1:8765/mcp` and recording the port it actually bound in
`~/.geoda/mcp.json`. Once connected, this agent drives GeoDa's analysis tools
directly and the maps and plots render in the app window.

This skill downloads, installs, launches, and registers that app, and opens the
data set in it. It is **idempotent** — run the first step and skip ahead if the
tools are already available.

> The MCP server merged into `master` for 1.22.2 (PR #2586), but `file/open` —
> the tool that opens a data set in the running app — is newer than that release
> (PR #2595), so until it merges the build to take is the fork's: run Step 1
> with `GEODA_REPO=lixun910/geoda`. Either build works — Step 6 says how to tell
> which one you have, and what to do on one without `file/open`.

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

## Step 3 — Launch GeoDa

The app hosts the MCP server, and the server starts with the app. Launch the
executable directly, with **no data set** — the client opens that in Step 6, so
one instance can switch data sets without a restart. If GeoDa is already running
(the usual case, when the user started it themselves) leave it be:

```bash
if ! pgrep -x GeoDa >/dev/null; then
  /Applications/GeoDa.app/Contents/MacOS/GeoDa --mcp-port 8765 >/dev/null 2>&1 &
fi
```

Redirect the app's output: GeoDa logs to stdout, so backgrounding it without that
leaves the pipe open and a non-interactive shell never returns.

Wait for the server and read the port it bound:

```bash
for i in $(seq 1 30); do [ -f ~/.geoda/mcp.json ] && break; sleep 1; done
cat ~/.geoda/mcp.json 2>/dev/null || echo "discovery file not written yet"
```

`--mcp-port` above pins the server to the default port, so this works on a build
that predates the auto-start change too; such a build writes no discovery file,
and Step 4's probe finds the server anyway.

If no server answers at all (no discovery file, and Step 4's probe finds
nothing), the running copy was started with `--no-mcp` or `GEODA_MCP_ENABLED=0`.
Ask the user to start it from GeoDa's **Options → MCP → Start MCP Server…** menu
— that menu entry also shows the URL to register — or quit the app and launch it
again as above.

### If this build has no `file/open`

Releases up to 1.22.2 register `file/open` against a "requires the GeoDa GUI"
stub, so a data set can only reach them on the command line. GeoDa reads that
argument **only at launch**, so quit any running copy first and run the
executable directly:

```bash
osascript -e 'quit app "GeoDa"' 2>/dev/null; sleep 2
if pgrep -x GeoDa >/dev/null; then
  echo "GeoDa is still running - dismiss any dialog it is showing, then retry"
else
  /Applications/GeoDa.app/Contents/MacOS/GeoDa \
    --mcp-port 8765 "/absolute/path/to/data.geojson" >/dev/null 2>&1 &
fi
```

Do not use `open -a GeoDa <path>` for this. Against an already-running instance it
exits 0 and opens nothing — the project already loaded stays put, so every tool
call after it answers from the wrong data set. Launching through `open` also hands
the app a bare command line (the path travels in an Apple event instead), which is
why the check below cannot see it; and with a second copy of the bundle on disk,
`open -a GeoDa` can start that copy, leaving the MCP client talking to the wrong
build.

Confirm the launch took by looking for the path in the process's own command line:

```bash
ps -o command= -p "$(pgrep -x GeoDa | head -1)" \
  | grep -F "/absolute/path/to/data.geojson"
```

`project/status` reports the title and dimensions but leaves `path` empty, so this
is the only way to confirm which file is loaded. If the check fails, the old
instance never exited (a modal dialog blocks the quit): ask the user to dismiss
it, then launch again rather than continuing against the stale project.

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

1. **Open the data set.** `project/status` first: if nothing is open, ask the
   user which file to use (or take the one their request named) and open it with
   `file/open`, which takes an absolute path — `~` and `${VAR}` are expanded:

   ```json
   {"name": "file/open", "arguments": {"path": "~/Downloads/natregimes.shp"}}
   ```

   The result reports the `path`, `title`, `num_records` and `num_columns` it
   opened, the analysis tools then act on that project, and the map window
   appears in the app. GeoDa holds **one project at a time**: opening while one is
   open is refused, so call `file/close` first to switch data sets — add
   `{"force": true}` only if the user agrees to discard unsaved edits.

   On a build whose `file/open` has no `path` parameter (the 1.22.x releases and
   older CI builds, where the tool is only a stub), load the data set at launch
   instead, as in "If this build has no `file/open`" under Step 3; `tools/list`
   says which build you have.

   A shapefile needs its `.dbf` beside it — one missing its `.dbf` opens with no
   columns at all, so the variable you are about to ask for won't be there.
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
