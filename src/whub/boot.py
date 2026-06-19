"""Boot deploy — distribute .my-boot config to target projects."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

MARKER_START = "<!-- hub:managed:start -->"
MARKER_END = "<!-- hub:managed:end -->"

_MARKER_FILES = {"CLAUDE.md", "AGENTS.md"}
_MERGE_FILES = {"settings.json"}
_SKIP = {".DS_Store", ".git"}
_GITIGNORE_ENTRIES = [".claude/", ".codex/", ".codegraph/", "AGENTS.md", ".mcp.json"]
_REMAP = {"mcp.json": ".mcp.json"}
_ROOT_MARKERS = {"codex/AGENTS.md": "AGENTS.md"}
_BOOT_SOURCE = "my-boot"
_SELF_TARGET = "workspace-hub"


def deploy_marked(src: Path, dst: Path) -> None:
    block = src.read_text()
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not dst.exists():
        dst.write_text(block)
        return

    existing = dst.read_text()
    if MARKER_START in existing:
        before = existing[: existing.index(MARKER_START)]
        after = existing[existing.index(MARKER_END) + len(MARKER_END) :]
        new = before + block + after
    else:
        new = block + "\n" + existing

    if new != existing:
        dst.write_text(new)


def _merge_settings(src: Path, dst: Path) -> None:
    common = json.loads(src.read_text())
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not dst.exists():
        dst.write_text(json.dumps(common, indent=2, ensure_ascii=False) + "\n")
        return

    proj = json.loads(dst.read_text())
    original = json.dumps(proj, sort_keys=True)

    src_allow = common.get("permissions", {}).get("allow", [])
    dst_allow = proj.setdefault("permissions", {}).setdefault("allow", [])
    proj["permissions"]["allow"] = list(dict.fromkeys(dst_allow + src_allow))

    if "hooks" in common:
        proj["hooks"] = common["hooks"]

    if json.dumps(proj, sort_keys=True) != original:
        dst.write_text(json.dumps(proj, indent=2, ensure_ascii=False) + "\n")


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*_SKIP))
    else:
        shutil.copy2(src, dst)


def _deploy_file(src: Path, dst: Path) -> None:
    if src.name in _MARKER_FILES:
        deploy_marked(src, dst)
    elif src.name in _MERGE_FILES:
        _merge_settings(src, dst)
    else:
        _copy(src, dst)


def _ensure_gitignore(target: Path) -> None:
    path = target / ".gitignore"
    existing = path.read_text() if path.exists() else ""
    lines = existing.splitlines()
    added = [e for e in _GITIGNORE_ENTRIES if e not in lines]
    if added:
        with path.open("a") as f:
            for e in added:
                f.write(e + "\n")


def deploy_all(m) -> list[tuple[str, bool]]:
    """Deploy boot config to all boot-enabled resources + workspace-hub itself."""
    boot_res = next((r for r in m.resources if r.name == _BOOT_SOURCE), None)
    if not boot_res:
        raise RuntimeError(f"{_BOOT_SOURCE} not found in manifest")

    boot_src = m.resolve_path(boot_res.path)
    targets = [(r.name, m.resolve_path(r.path)) for r in m.resources if r.boot and r.name != _BOOT_SOURCE]
    targets.append((_SELF_TARGET, m.root))

    results = []
    for name, path in targets:
        if not path.exists():
            results.append((name, False))
            continue
        deploy_to_project(boot_src, path)
        results.append((name, True))
    return results


def deploy_to_project(boot_source: Path, target: Path) -> None:
    claude, codex = boot_source / "claude", boot_source / "codex"

    for item in sorted(claude.iterdir()):
        if item.name in _SKIP:
            continue
        dst = target / _REMAP.get(item.name, f".claude/{item.name}")
        _deploy_file(item, dst)

    _copy(codex, target / ".codex")
    for src_rel, dst_name in _ROOT_MARKERS.items():
        deploy_marked(boot_source / src_rel, target / dst_name)

    _ensure_gitignore(target)
