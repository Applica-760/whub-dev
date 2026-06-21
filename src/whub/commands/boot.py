"""whub boot deploy — distribute .my-boot config to target projects."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import click

from whub.commands import get_manifest

MARKERS = ("<!-- hub:managed:start -->", "<!-- hub:managed:end -->")
GITIGNORE_MARKERS = ("# hub:managed:start", "# hub:managed:end")

_MARKER_FILES = {"CLAUDE.md", "AGENTS.md"}
_MERGE_FILES = {"settings.json"}
_SKIP = {".DS_Store", ".git"}
_REMAP = {"mcp.json": ".mcp.json"}
_ROOT_MARKERS = {"codex/AGENTS.md": "AGENTS.md"}
_GITIGNORE = (".gitignore", ".gitignore")
_BOOT_SOURCE = "my-boot"
_SELF_TARGET = "workspace-hub"


def _managed_range(
    text: str, markers: tuple[str, str], path: Path,
) -> tuple[int, int] | None:
    start, end = markers
    if start not in text and end not in text:
        return None
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"invalid managed markers: {path}")
    first, last = text.index(start), text.index(end)
    if first > last:
        raise ValueError(f"invalid managed markers: {path}")
    return first, last + len(end)


def _deploy_marked(
    src: Path,
    dst: Path,
    markers: tuple[str, str] = MARKERS,
) -> None:
    block = src.read_text()
    if _managed_range(block, markers, src) is None:
        raise ValueError(f"managed markers are missing: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not dst.exists():
        dst.write_text(block)
        return

    existing = dst.read_text()
    managed = _managed_range(existing, markers, dst)
    new = (
        block + "\n" + existing
        if managed is None
        else existing[:managed[0]] + block + existing[managed[1]:]
    )

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
        proj["hooks"] = {**proj.get("hooks", {}), **common["hooks"]}

    if json.dumps(proj, sort_keys=True) != original:
        dst.write_text(json.dumps(proj, indent=2, ensure_ascii=False) + "\n")


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(
            src, dst, ignore=shutil.ignore_patterns(*_SKIP), dirs_exist_ok=True,
        )
    else:
        shutil.copy2(src, dst)


def _deploy_file(src: Path, dst: Path) -> None:
    if src.name in _MARKER_FILES:
        _deploy_marked(src, dst)
    elif src.name in _MERGE_FILES:
        _merge_settings(src, dst)
    else:
        _copy(src, dst)


def _clean_apple_double(target: Path) -> None:
    """Remove macOS AppleDouble (._*) files generated on FUSE mounts."""
    for d in (target / ".claude", target / ".codex"):
        if d.exists():
            for f in d.rglob("._*"):
                f.unlink(missing_ok=True)
    for f in target.glob("._*"):
        f.unlink(missing_ok=True)


def _deploy_to_project(boot_source: Path, target: Path) -> None:
    claude, codex = boot_source / "claude", boot_source / "codex"

    for item in sorted(claude.iterdir()):
        if item.name in _SKIP:
            continue
        dst = target / _REMAP.get(item.name, f".claude/{item.name}")
        _deploy_file(item, dst)

    _copy(codex, target / ".codex")
    for src_rel, dst_name in _ROOT_MARKERS.items():
        _deploy_marked(boot_source / src_rel, target / dst_name)

    src_name, dst_name = _GITIGNORE
    _deploy_marked(
        boot_source / src_name,
        target / dst_name,
        GITIGNORE_MARKERS,
    )
    _clean_apple_double(target)


def _deploy_all(m) -> list[tuple[str, bool]]:
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
        _deploy_to_project(boot_src, path)
        results.append((name, True))
    return results


@click.group()
def boot() -> None:
    """Manage agent bootstrap configuration."""


@boot.command("deploy")
@click.pass_context
def boot_deploy(ctx: click.Context) -> None:
    """Deploy agent bootstrap config to target resources."""
    for name, ok in _deploy_all(get_manifest(ctx)):
        click.echo(f"  {'done':6s}  {name}" if ok else f"  {'skip':6s}  {name} (not found)")
