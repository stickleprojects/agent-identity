import json
import re

import pytest

from conftest import REPO, identity, run

# --- agent identity -------------------------------------------------------------------------


def test_one_identity_and_no_personas():
    # One App serves every session; Claude never acts as the person. Personas were taken out
    # (claude-sdlc #61) and adding Apps back goes through the identity name.
    assert not (REPO / ".claude/personas.conf").exists()
    skill = (REPO / "skills/agent-identity/SKILL.md").read_text()
    assert "persona" not in skill.lower()
    assert "`— Claude`" in skill and "Requested-by:" in skill
    for script in ["agent-identity.sh", "session-hook.sh"]:
        assert "--persona" not in (REPO / "scripts" / script).read_text(), script


def test_token_is_minted_with_a_valid_jwt_and_cached(agent_env):
    tmp, env = agent_env
    first = identity(env, "token")
    assert first.returncode == 0, first.stderr
    assert first.stdout.strip() == "ghs_test"
    header, payload, sig = (tmp / "jwt").read_text().strip().split(".")
    pad = lambda s: s + "=" * (-len(s) % 4)  # noqa: E731
    import base64

    claims = json.loads(base64.urlsafe_b64decode(pad(payload)))
    assert claims["iss"] == "123" and claims["exp"] - claims["iat"] <= 600
    (tmp / "sig").write_bytes(base64.urlsafe_b64decode(pad(sig)))
    (tmp / "msg").write_text(f"{header}.{payload}")
    verify = run(
        [
            "openssl",
            "dgst",
            "-sha256",
            "-verify",
            str(tmp / "pub.pem"),
            "-signature",
            str(tmp / "sig"),
            str(tmp / "msg"),
        ]
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr
    calls = (tmp / "curl").read_text().count("\n")
    assert identity(env, "token").stdout.strip() == "ghs_test"
    assert (tmp / "curl").read_text().count("\n") == calls, "second call uses the cache"


def test_token_fails_rather_than_printing_null(agent_env):
    tmp, env = agent_env
    (tmp / "body-token").write_text('{"expires_at": "2099-01-01T00:00:00Z"}')
    out = identity(env, "token")
    assert out.returncode != 0 and "null" not in out.stdout


def test_git_credential_answers_only_for_github(agent_env):
    _, env = agent_env
    gh = identity(env, "git-credential", "get", stdin="protocol=https\nhost=github.com\n\n")
    assert gh.stdout == "username=x-access-token\npassword=ghs_test\n"
    other = identity(env, "git-credential", "get", stdin="protocol=https\nhost=gitlab.com\n\n")
    assert other.stdout == ""


def test_env_makes_git_act_as_the_bot(agent_env):
    _, env = agent_env
    out = identity(env, "env")
    assert out.returncode == 0, out.stderr
    assert "GIT_AUTHOR_NAME='stickle-claude[bot]'" in out.stdout
    assert "999+stickle-claude[bot]@users.noreply.github.com" in out.stdout
    assert "SDLC_AGENT_PERSONA" not in out.stdout
    assert "insteadOf" in out.stdout


def test_env_rejects_options(agent_env):
    _, env = agent_env
    assert identity(env, "env", "--persona", "build").returncode == 1


def test_env_without_setup_falls_back_to_the_person(agent_env, tmp_path):
    _, env = agent_env
    out = identity({**env, "XDG_CONFIG_HOME": str(tmp_path / "empty")}, "env")
    assert out.returncode == 0 and out.stdout == ""
    assert "acts as you" in out.stderr


def test_session_hook_writes_the_identity_into_the_session(agent_env):
    # The SessionStart hook (hooks/hooks.json) appends the identity's environment to
    # $CLAUDE_ENV_FILE, so every Bash command in the session acts as the App.
    tmp, env = agent_env
    env_file = tmp / "claude.env"
    out = run(["bash", str(REPO / "scripts/session-hook.sh")], env={**env, "CLAUDE_ENV_FILE": str(env_file)})
    assert out.returncode == 0, out.stderr
    written = env_file.read_text()
    assert "GIT_COMMITTER_NAME='stickle-claude[bot]'" in written
    assert "AGENT_ID_IDENTITY='stickle-claude[bot]'" in written and "SDLC_AGENT_IDENTITY=" in written


def test_session_hook_never_blocks_a_session(agent_env, tmp_path):
    # Not configured, or no env file: the session starts as the person, and the hook exits 0.
    _, env = agent_env
    assert run(["bash", str(REPO / "scripts/session-hook.sh")], env=env).returncode == 0
    env_file = tmp_path / "claude.env"
    out = run(["bash", str(REPO / "scripts/session-hook.sh")],
              env={**env, "SDLC_AGENT_REPO": "o/none", "CLAUDE_ENV_FILE": str(env_file)})
    assert out.returncode == 0 and (not env_file.exists() or env_file.read_text() == "")


def test_agent_id_names_are_aliases_for_sdlc_ones(agent_env):
    # AGENT_ID_* (this module) and SDLC_* (claude-sdlc) both work; SDLC_* wins when both are set.
    _, env = agent_env
    plain = {k: v for k, v in env.items() if k != "SDLC_AGENT_REPO"}
    assert identity({**plain, "AGENT_ID_REPO": "o/r"}, "show").stdout.strip() == "123 stickle-claude"
    both = identity({**plain, "AGENT_ID_REPO": "o/none", "SDLC_AGENT_REPO": "o/r"}, "show")
    assert both.stdout.strip() == "123 stickle-claude"


def test_not_configured_points_at_this_module_or_the_given_docs(agent_env):
    _, env = agent_env
    other = {**env, "SDLC_AGENT_REPO": "o/none"}
    assert "stickleprojects/agent-identity" in identity(other, "env").stderr
    assert ".sdlc/docs/agent-identity.md" in identity({**other, "AGENT_ID_DOCS": ".sdlc/docs/agent-identity.md"}, "env").stderr


def test_each_repo_has_its_own_apps(agent_env):
    # An App made for o/r doesn't leak into another repo on the same machine.
    _, env = agent_env
    assert identity(env, "show").stdout.strip() == "123 stickle-claude"
    other = identity({**env, "SDLC_AGENT_REPO": "o/jobhunt-app"}, "show")
    assert other.returncode == 1
    assert identity({**env, "SDLC_AGENT_REPO": "o/jobhunt-app"}, "env").stdout == ""


def test_check_points_at_the_docs_setting_too(agent_env):
    # agent-identity#1 review: `check` said .sdlc/docs/... after the move; it follows AGENT_ID_DOCS like `env`.
    _, env = agent_env
    other = {**env, "SDLC_AGENT_REPO": "o/none"}
    out = identity(other, "check")
    assert out.returncode == 1 and "stickleprojects/agent-identity" in out.stdout and ".sdlc/" not in out.stdout


def test_session_hook_is_silent_in_a_repo_without_an_app(agent_env, tmp_path):
    # agent-identity#1 review: at user scope the hook runs in every repo; where there's no App it says nothing.
    _, env = agent_env
    env_file = tmp_path / "claude.env"
    out = run(["bash", str(REPO / "scripts/session-hook.sh")],
              env={**env, "SDLC_AGENT_REPO": "o/none", "CLAUDE_ENV_FILE": str(env_file)})
    assert out.returncode == 0 and out.stderr == "" and out.stdout == ""
    assert not env_file.exists() or env_file.read_text() == ""

