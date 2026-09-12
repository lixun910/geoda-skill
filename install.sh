#!/usr/bin/env bash
# Install the GeoDa MCP bootstrap skill for Claude Code and Codex.
set -euo pipefail

RAW="https://raw.githubusercontent.com/GeoDaCenter/geoda-skill/main"
SKILL_DIR="skills/geoda-mcp"
MCP_URL="${GEODA_MCP_URL:-http://127.0.0.1:8765/mcp}"

# Claude Code reads ~/.claude/skills; Codex reads $HOME/.agents/skills.
for base in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  dir="$base/geoda-mcp"
  mkdir -p "$dir"
  curl -fsSL "$RAW/.agents/$SKILL_DIR/SKILL.md" -o "$dir/SKILL.md"
  echo "installed skill -> $dir/SKILL.md"
done

# Codex-only: agents/openai.yaml declares the MCP dependency, so Codex can
# install and wire the server itself.
CODEX_DIR="$HOME/.agents/skills/geoda-mcp"
mkdir -p "$CODEX_DIR/agents"
curl -fsSL "$RAW/.agents/$SKILL_DIR/agents/openai.yaml" -o "$CODEX_DIR/agents/openai.yaml"

# Fallback for clients that do not auto-wire: register the server directly.
if command -v codex >/dev/null 2>&1; then
  codex mcp add geoda --url "$MCP_URL" 2>/dev/null \
    || echo "codex mcp: 'geoda' may already be registered"
fi

if command -v claude >/dev/null 2>&1; then
  claude mcp add --transport http geoda "$MCP_URL" 2>/dev/null \
    || echo "claude mcp: 'geoda' may already be registered"
fi

echo "Done. Restart your client, then prompt e.g. \"run a LISA analysis in GeoDa on this shapefile.\""
