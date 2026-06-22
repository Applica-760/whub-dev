"""whub boot — distribute packaged agent config to target projects."""

from __future__ import annotations
import json
import shutil
import subprocess
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
import click
from whub.commands import get_manifest

def _managed_range(
    text: str, markers: tuple[str, str], path: str | Path,
) -> tuple[int, int] | None:
    start, end = markers
    if start not in text and end not in text:
        return None
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"invalid managed markers: {path}")
    first, last = text.index(start), text.index(end)
    if first > last:
        raise ValueError(f"invalid managed markers: {path}")
    last += len(end)
    newline = "\r\n" if text.startswith("\r\n", last) else "\n"
    return first, last + (len(newline) if text.startswith(newline, last) else 0)


def _deploy_marked(
    block: str,
    dst: Path,
    markers: tuple[str, str],
    source: str,
) -> None:
    if _managed_range(block, markers, source) is None:
        raise ValueError(f"managed markers are missing: {source}")
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        existing = dst.read_text()
        managed = _managed_range(existing, markers, dst)
        new = (
            block + "\n" + existing
            if managed is None
            else existing[:managed[0]] + block + existing[managed[1]:]
        )
    else:
        existing, new = None, block

    if new != existing:
        dst.write_text(new)


def _merge_settings(common: dict, dst: Path) -> None:
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


def _clean_apple_double(target: Path) -> None:
    """Remove macOS AppleDouble (._*) files generated on FUSE mounts."""
    for path in target.rglob("._*"):
        path.unlink(missing_ok=True)


def _copy_tree(src: Traversable, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_dir():
            _copy_tree(item, dst / item.name)
        else:
            (dst / item.name).write_bytes(item.read_bytes())


def _deploy_to_project(boot_source: Traversable, target: Path) -> None:
    for relative in (".codex/config.toml", ".mcp.json"):
        dst = target / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(boot_source.joinpath(relative).read_bytes())

    for skill_target in (target / ".claude/skills", target / ".agents/skills"):
        _copy_tree(boot_source.joinpath("skills"), skill_target)

    for relative in (".claude/CLAUDE.md", "AGENTS.md"):
        _deploy_marked(
            boot_source.joinpath(relative).read_text(),
            target / relative,
            ("<!-- hub:managed:start -->", "<!-- hub:managed:end -->"),
            relative,
        )

    gitignore = "\n".join((
        "# hub:managed:start",
        ".agents/",
        ".claude/",
        ".codex/",
        ".codegraph/",
        ".mcp.json",
        "AGENTS.md",
        "# hub:managed:end",
    )) + "\n"
    _deploy_marked(
        gitignore,
        target / ".gitignore",
        ("# hub:managed:start", "# hub:managed:end"),
        "generated .gitignore",
    )

    _merge_settings(
        json.loads(boot_source.joinpath(".claude/settings.json").read_text()),
        target / ".claude/settings.json",
    )
    _clean_apple_double(target)


def _init_codegraph(executable: str, target: Path) -> str | None:
    try:
        result = subprocess.run(
            [executable, "init", str(target)],
            capture_output=True,
            text=True,
        )
    except OSError as error:
        return str(error)
    if result.returncode == 0:
        return None
    return (
        result.stderr.strip()
        or result.stdout.strip()
        or f"exit status {result.returncode}"
    )


@click.command()
@click.pass_context
def boot(ctx: click.Context) -> None:
    """Deploy agent bootstrap config to target resources."""
    manifest = get_manifest(ctx)
    targets = [("workspace-hub", manifest.root)] + [
        (r.name, manifest.resolve_path(r.path))
        for r in manifest.resources if r.boot
    ]

    boot_source = files("whub").joinpath("boot")
    codegraph = shutil.which("codegraph")
    if codegraph is None:
        click.echo("  WARN    codegraph not found; initialization skipped")

    for name, path in targets:
        ok = path.exists()
        if ok:
            _deploy_to_project(boot_source, path)
        click.echo(
            f"  {'done':6s}  {name}"
            if ok else f"  {'skip':6s}  {name} (not found)"
        )
        if ok and codegraph:
            error = _init_codegraph(codegraph, path)
            click.echo(
                f"  {'init':6s}  {name} (CodeGraph)"
                if error is None
                else f"  {'WARN':6s}  {name}: CodeGraph init failed: {error}"
            )
