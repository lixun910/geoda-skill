# GeoDa — agent skill

Bootstrap skill for **GeoDa**: it downloads and launches the app and gives the
agent GeoDa's spatial-analysis tools (spatial weights, global and local spatial
autocorrelation / LISA, spatial clustering, regression, maps).

The skill is published in the formats clients load: a **Claude Code plugin**
(via a marketplace), a portable **Agent Plugin** (the cross-vendor format
Codex/ChatGPT read), and a plain **agent skill** for clients with no plugin
loader.

## Claude Code

```bash
claude plugin marketplace add lixun910/geoda-skill
claude plugin install geoda-mcp@geoda-skill
```

Restart Claude Code to load the skill.

## Codex

Codex installs skills with its built-in `$skill-installer` — point it at this
repo's skill directory, in a Codex session:

```
$skill-installer install https://github.com/lixun910/geoda-skill/tree/main/.agents/skills/geoda-mcp
```

Restart Codex afterwards. (The installer aborts if the skill is already
installed; remove the existing skill directory first to reinstall.)

If `$skill-installer` isn't available, copy the skill files by hand:

```bash
curl -fsSL --create-dirs -o ~/.agents/skills/geoda-mcp/SKILL.md https://raw.githubusercontent.com/lixun910/geoda-skill/main/.agents/skills/geoda-mcp/SKILL.md
```

```bash
curl -fsSL --create-dirs -o ~/.agents/skills/geoda-mcp/agents/openai.yaml https://raw.githubusercontent.com/lixun910/geoda-skill/main/.agents/skills/geoda-mcp/agents/openai.yaml
```

## One command for both clients

```bash
curl -fsSL https://raw.githubusercontent.com/lixun910/geoda-skill/main/install.sh | bash
```

## Then

Restart the client and prompt, e.g. *"run a LISA analysis in GeoDa on
`~/data/nyc.geojson`."* The skill gets the GeoDa build, installs and launches the
app, and drives its tools.

## Layout

```
.claude-plugin/marketplace.json                          Claude Code marketplace
plugins/geoda-mcp/.claude-plugin/plugin.json             Claude Code plugin manifest
plugins/geoda-mcp/skills/geoda-mcp/SKILL.md              the skill
.agents/skills/geoda-mcp/SKILL.md                        the skill (Codex copy)
install.sh                                               installs the skill for both clients
```

## Notes

- **Builds:** GeoDa's MCP server is on the `feat-mcp-server` line and is not in a
  public release yet, so the skill pulls the macOS build from CI. Builds run on
  `GeoDaCenter/geoda`'s own branches are signed and notarized; fork-PR builds are
  unsigned, so the skill clears the quarantine flag only if a launch is blocked.
- **Updating:** bump `version` in both
  `plugins/geoda-mcp/.claude-plugin/plugin.json` and
  `plugins/geoda-mcp/plugin.json`, then users run
  `claude plugin update geoda-mcp`.
