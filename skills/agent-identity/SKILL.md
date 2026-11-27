---
name: agent-identity
description: How Claude acts on GitHub, under its own identity or the person's: who commits, how comments are signed, and the rules that stop agents triggering each other or fighting over a branch. Apply whenever you commit, push, open or update a PR, or post a comment or reply on GitHub.
user-invocable: false
---
<!-- From claude-sdlc's .sdlc/skills/agent-identity/SKILL.md (v0.20.0), moved to stickleprojects/agent-identity (aws-build-runner#85). -->

# Acting on GitHub as the agent

Claude sessions can run under their own GitHub identity, a GitHub App that shows as `<app>[bot]` (see this plugin's `docs/agent-identity.md`). When they do, the environment has `SDLC_AGENT_IDENTITY` set, and `git` and `gh` already commit, push and comment as the App. You don't need to log in or pass tokens.

Check which applies: `echo "${SDLC_AGENT_IDENTITY:-person}"`.

## Who acts as whom

One App, the identity `agent`, serves every local Claude session and the spec workflow. It is never the person. The CI reviewer and the `@claude` bot are a different identity (`claude[bot]`, from the review and mention workflows); they aren't yours to act as. <!-- rule: identity.who-is-who -->

## Signing what you post

- **As the agent** (`SDLC_AGENT_IDENTITY` set): end each comment, reply and PR body with `— Claude`. When you record someone's decision, say whose it is, in plain text: "Product owner decided: …". <!-- rule: identity.signing -->
- **As the person** (not set): the post appears under their account, so end it with `(posted from Claude Code)`.

## Commits

As the agent, `git` already sets the author to the App. Add this trailer to the commit message, after the body and before any attribution lines:

```
Requested-by: <$SDLC_AGENT_REQUESTED_BY>
```

Add files by explicit path, never `git add -A` or `git add .`. <!-- rule: identity.explicit-add -->

## GitHub commands

Use `gh api` (REST). `gh pr create`, `gh pr view`, `gh pr edit` and `gh issue view` use GraphQL, which fails in cloud sessions and in orgs hit by the Projects (classic) deprecation. <!-- rule: identity.rest-api -->

## Right after opening a PR

If the repo has an auto-merge helper (claude-sdlc's is `.sdlc/scripts/auto-merge.sh <N>`), run it on the PR you just opened and pass on the line it prints. It turns on auto-merge only where the repo opted in and a person's approval is still required, so the approval stays the gate. Run it straight away: GitHub refuses once a PR is approved and green. Where the repo's own instructions say how to arm auto-merge, follow them; never use it to get past a required approval. <!-- rule: identity.auto-merge -->

## Rules that prevent loops and conflicts

1. **Act only when a person asks,** in this session. Never start work because a bot commented, a review finished or a check failed, unless the person asked you to watch for it. <!-- rule: identity.act-when-asked -->
2. **Never @-mention anyone** in comments, replies, commits or PR bodies, bots and people alike. Write a name without the `@`. Above all, never write `@claude`: it starts the mention bot, which is a second agent. <!-- rule: identity.no-mentions -->
3. **One actor per finding.** A review finding is handled by this session or by the GitHub bot (`@claude`), never both: two agents fixing one finding make conflicting commits. The bot owns a thread with an `@claude` comment on it, or one an `@claude` PR comment names; leave it. <!-- rule: identity.one-actor -->
4. **Before every push, fetch and merge.** Run `git fetch origin <branch>` and `git log --format='%h %an %s' HEAD..origin/<branch>`. Anything there was pushed by someone else, whoever it was: a person, the bot (`claude[bot]`, `github-actions[bot]`), or another session using this same identity. Show it, merge it (never rebase a pushed branch), re-run the repo's local checks (claude-sdlc: `make local-check`), then push. <!-- rule: identity.fetch-merge -->
5. **Never force-push** (a hook blocks it), and never delete a branch someone else pushed to. <!-- rule: identity.no-force-push -->
6. **Approving and merging stay with people.** With your own identity, branch protection requires a person's approval. Never ask for a workaround, and never approve anything, even someone else's PR. Auto-merge through `.sdlc/scripts/auto-merge.sh` doesn't change this: it merges only after a person approves. <!-- rule: identity.people-approve -->
