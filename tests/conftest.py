"""Test helpers for agent-identity, taken from claude-sdlc's tests/conftest.py and tests/scripts/ (v0.20.0):
only what the identity tests use."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def run(cmd, cwd=REPO, env=None, input=None, check=False):
    """Run a command, returning CompletedProcess with text output."""
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, cwd=cwd, env=full_env, input=input, text=True, capture_output=True, check=check
    )


def identity(env, *args, stdin=None):
    return run(["bash", str(REPO / "scripts/agent-identity.sh"), *args], env=env, input=stdin)


@pytest.fixture
def agent_env(tmp_path):
    key = tmp_path / "app.pem"
    run(["openssl", "genrsa", "-out", str(key), "2048"], check=True)
    run(
        ["openssl", "rsa", "-in", str(key), "-pubout", "-out", str(tmp_path / "pub.pem")],
        check=True,
    )
    cfg = tmp_path / "config"
    (cfg / "sdlc" / "o_r").mkdir(parents=True)
    (cfg / "sdlc" / "o_r" / "agent.env").write_text(
        "SDLC_AGENT_APP_ID=123\nSDLC_AGENT_APP_SLUG=stickle-claude\nSDLC_AGENT_BOT_ID=999\n"
    )
    fake = tmp_path / "bin"
    fake.mkdir()
    # curl stub that answers like GitHub; see the fixture for how tests steer it.
    shutil.copy(REPO / "tests/fixtures/fake-github-curl.sh", fake / "curl")
    (fake / "curl").chmod(0o755)
    env = {
        "PATH": f"{fake}:{os.environ['PATH']}",
        "XDG_CONFIG_HOME": str(cfg),
        "XDG_RUNTIME_DIR": str(tmp_path / "run"),
        "SDLC_AGENT_KEY_FILE": str(key),
        "SDLC_AGENT_REPO": "o/r",
        "LOG": str(tmp_path),
        "SDLC_RETRY_DELAY": "0",
    }
    return tmp_path, env
