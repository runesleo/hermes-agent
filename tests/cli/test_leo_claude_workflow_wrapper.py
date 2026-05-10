from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml


SCRIPT_PATH = Path("/Users/zhangxu/.local/bin/hermes-claude-workflow")
CONFIG_PATH = Path("/Users/zhangxu/.hermes/config.yaml")


def test_wrapper_today_dry_run_exposes_claude_lane_metadata():
    result = subprocess.run(
        [str(SCRIPT_PATH), "--dry-run", "today"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["workflow"] == "today"
    assert payload["model"] == "opus"
    assert payload["effort"] == "medium"
    assert payload["spec_path"].endswith("/.claude/skills/today/SKILL.md")
    assert payload["command"][0] == "claude"
    assert "--model" in payload["command"]
    assert "-p" in payload["command"]


def test_config_quick_commands_route_to_wrapper():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    quick_commands = config.get("quick_commands") or {}
    for workflow in ("today", "morning", "next", "status"):
        entry = quick_commands.get(workflow)
        assert entry is not None
        assert entry.get("type") == "exec"
        assert entry.get("command") == f"/Users/zhangxu/.local/bin/hermes-claude-workflow {workflow}"
