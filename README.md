# agent-identity

Claude's own GitHub identity for Claude Code sessions. In a repo that enables it, every session commits, pushes and comments as a GitHub App (`<app>[bot]`), never as the person running it. So GitHub, not Claude's word, can require **the person's** approval before anything Claude wrote merges.

Extracted from [claude-sdlc](https://github.com/stickleprojects/claude-sdlc) (v0.20.0, with history) so any repo can use it: [aws-build-runner#85](https://github.com/stickleprojects/aws-build-runner/issues/85).

| | |
|---|---|
| `scripts/agent-identity.sh` | `create` (one-click App via GitHub's manifest flow), `setup`, `use` (share an App), `doctor`, `rekey`, `check`, `show`, `token` (1-hour, cached in `$XDG_RUNTIME_DIR`), `git-credential`, `env` |
| `scripts/create-agent-apps.py` | The manifest flow behind `create`. `--profile sdlc` (default) or `minimal`, plus `--permission name=read\|write` |
| `scripts/session-hook.sh` + `hooks/hooks.json` | SessionStart: puts the identity's environment into every Bash command of the session. Does nothing when no App is configured |
| `skills/agent-identity/` | How to act as the agent: sign posts, no @-mentions, fetch and merge before pushing, people approve and merge |

The private key stays in the keyring (`secret-tool`, service `claude-sdlc`) or a file you name. The config (App id, slug, bot id, where the key is) lives in `~/.config/sdlc/<owner>_<repo>/agent.env`, so Apps set up by claude-sdlc keep working.

## Use it in a repo

1. In the repo's `.claude/settings.json`, add this marketplace **pinned to a commit**, and enable the plugin:
   ```json
   {
     "extraKnownMarketplaces": {
       "stickleprojects-agent-identity": {
         "source": {"source": "github", "repo": "stickleprojects/agent-identity", "ref": "<full commit sha>"}
       }
     },
     "enabledPlugins": {"agent-identity@stickleprojects-agent-identity": true}
   }
   ```
2. Create the App, once per repo, as the repo's owner: `agent-identity.sh create` (add `--profile minimal --permission workflows=write …` for a repo that isn't on claude-sdlc's pipeline). Your browser opens GitHub with everything filled in: click **Create GitHub App**, then install it on the repo.
3. `agent-identity.sh doctor`, then require a code owner's review on `main` (branch protection). That review is what makes the identity worth having.

**Names:** `AGENT_ID_*` settings are aliases for claude-sdlc's `SDLC_*` ones (`AGENT_ID_REPO` = `SDLC_AGENT_REPO`, `AGENT_ID_GITHUB_API` = `SDLC_GITHUB_API`, …). `SDLC_*` wins when both are set. Config files and the GitHub variables and secret that workflows read (`SDLC_AGENT_APP_ID`, `SDLC_AGENT_APP_SLUG`, `SDLC_AGENT_APP_KEY`) keep their names.

**Updates and the session:** `gh` and git's credential helper in a session call this plugin's scripts by their path in the plugin cache, which is versioned. If the plugin is updated while a session runs, that session's `gh` and `git push` fail until it's restarted. The token cache (`$XDG_RUNTIME_DIR/sdlc-agent-<uid>`) is shared with claude-sdlc's copy on purpose: same format, same App, one token.

**In a repo with no App** (e.g. the plugin enabled at user scope), the session hook stays silent and the session acts as you.

**Not here (stays in claude-sdlc):** `auto-merge.sh`, the production gate, the launcher half of `agent-session.sh`, and CI, which uses `actions/create-github-app-token` with the variables above.

## Tests

`python -m pytest tests` (needs `openssl`; `shellcheck` in CI). Docs: [docs/agent-identity.md](docs/agent-identity.md), [docs/setup.md](docs/setup.md).
