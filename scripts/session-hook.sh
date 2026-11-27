#!/usr/bin/env bash
# SessionStart hook (hooks/hooks.json): every Bash command in the session commits, pushes and
# comments as the agent's GitHub App, by appending agent-identity.sh's environment to
# $CLAUDE_ENV_FILE. When the identity isn't configured it adds nothing, and the session acts as the
# person. It never blocks a session from starting.
#
# This is the --hook half of claude-sdlc's .sdlc/scripts/agent-session.sh. Its launcher half (start
# `claude` with the identity, and claude-sdlc's tests-locked note) stays in claude-sdlc.
set -euo pipefail

[[ -n "${CLAUDE_ENV_FILE:-}" ]] || exit 0
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || true
"$here/agent-identity.sh" env >> "$CLAUDE_ENV_FILE" || true
