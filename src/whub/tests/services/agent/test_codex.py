from pathlib import PurePosixPath
import tomllib

import pytest

from whub.models.agent.auth import (
    ApprovalGrants,
    CommandDecision,
    EffectiveAuth,
    ExtensionTool,
    FilesystemGrants,
)
from whub.services.agent.adapters.codex import (
    CodexAdapterError,
    render,
)


def _auth() -> EffectiveAuth:
    return EffectiveAuth.model_validate(
        {
            "variables": {"project": {"source": "registered_project"}},
            "grants": {
                "commands": {
                    "prefixes": [
                        {
                            "executable": "whub",
                            "arguments": [
                                "task",
                                "--project",
                                "$project",
                                "check",
                            ],
                        }
                    ],
                    "exact": [{"executable": "git", "arguments": ["diff"]}],
                },
                "filesystem": {
                    "read": [],
                    "write": ["current_worktree"],
                },
                "network": {"policy": "deny_all"},
                "extension_tools": ["codegraph"],
            },
        }
    )


def _codegraph() -> ExtensionTool:
    return ExtensionTool.model_validate(
        {
            "id": "codegraph",
            "protocol": "mcp",
            "transport": "stdio",
            "command": "codegraph",
            "args": ["serve", "--mcp"],
            "tools": ["explore", "node"],
        }
    )


def test_render_generates_project_rules_and_mcp_config() -> None:
    plan = render(_auth(), [_codegraph()], {"project": "whub-dev"})

    assert plan[PurePosixPath(".codex/rules/whub.rules")] == (
        'prefix_rule(\n    pattern = ["whub", "task", "--project", "whub-dev", "check"],\n'
        '    decision = "prompt",\n)\n'
    )
    config = tomllib.loads(plan[PurePosixPath(".codex/config.toml")])
    assert config["sandbox_mode"] == "workspace-write"
    assert config["approval_policy"] == "on-request"
    assert config["approvals_reviewer"] == "user"
    assert config["sandbox_workspace_write"] == {
        "network_access": False,
        "exclude_tmpdir_env_var": False,
        "exclude_slash_tmp": False,
    }
    assert config["mcp_servers"] == {
        "codegraph": {
            "command": "codegraph",
            "args": ["serve", "--mcp"],
            "enabled_tools": ["codegraph_explore", "codegraph_node"],
        }
    }


def test_render_generates_sandbox_config_without_extension_tools() -> None:
    auth = _auth().model_copy(
        update={"grants": _auth().grants.model_copy(update={"extension_tools": []})}
    )

    plan = render(auth, [], {"project": "whub-dev"})

    config = tomllib.loads(plan[PurePosixPath(".codex/config.toml")])
    assert "mcp_servers" not in config


def test_render_allows_explicitly_allowed_command_rules() -> None:
    auth = _auth()
    rule = auth.grants.commands.prefixes[0].model_copy(
        update={"decision": CommandDecision.ALLOW}
    )
    grants = auth.grants.model_copy(
        update={
            "commands": auth.grants.commands.model_copy(update={"prefixes": [rule]})
        }
    )

    plan = render(
        auth.model_copy(update={"grants": grants}),
        [_codegraph()],
        {"project": "whub-dev"},
    )

    assert 'decision = "allow"' in plan[PurePosixPath(".codex/rules/whub.rules")]


def test_render_never_generates_legacy_attention_hooks() -> None:
    variables = {
        "project": "whub-dev",
        "current_worktree.project": "whub-dev",
        "current_worktree.task": "TASK-104",
        "current_worktree.path": "/workspace/worktree",
    }

    plan = render(_auth(), [_codegraph()], variables)

    config = tomllib.loads(plan[PurePosixPath(".codex/config.toml")])
    assert "features" not in config
    assert "hooks" not in config
    assert PurePosixPath(".codex/hooks/whub_attention.py") not in plan


def test_render_derives_codex_permissions_from_effective_auth() -> None:
    grants = _auth().grants.model_copy(
        update={
            "filesystem": FilesystemGrants(read=[], write=[]),
            "approval": ApprovalGrants(policy="never", reviewer="auto_review"),
        }
    )

    plan = render(
        _auth().model_copy(update={"grants": grants}),
        [_codegraph()],
        {"project": "whub-dev"},
    )

    config = tomllib.loads(plan[PurePosixPath(".codex/config.toml")])
    assert config["sandbox_mode"] == "read-only"
    assert config["approval_policy"] == "never"
    assert config["approvals_reviewer"] == "auto_review"


def test_render_rejects_unresolved_variables() -> None:
    with pytest.raises(CodexAdapterError, match="unresolved command variable: project"):
        render(_auth(), [_codegraph()], {})


def test_render_rejects_unresolved_extension_tools() -> None:
    with pytest.raises(
        CodexAdapterError, match="unresolved extension tools: codegraph"
    ):
        render(_auth(), [], {"project": "whub-dev"})
