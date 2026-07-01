"""whub boot — distribute packaged agent config to target projects.
boot/ layout (directory = operation):
  merge/   section insert   (.md → HTML, .gitignore → #, .toml → #)
  json/    recursive merge   (JSON)
  skills/  → .claude/skills + .agents/skills
"""

from __future__ import annotations
import click
import json
import shlex
import shutil
import subprocess
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Callable, Iterator
from whub.commands import get_manifest
from whub.models import (
    Host,
    Manifest,
    Project,
    RemoteResource,
    SymlinkResource,
    workspace_hub_resource,
)
from whub.remote import run_rsync_command, run_ssh_command
from whub.target import TargetItem, on_targets

_MARKERS = {
    ".md": ("<!-- hub:managed:start -->", "<!-- hub:managed:end -->"),
    ".toml": ("# hub:managed:start", "# hub:managed:end"),
    ".gitignore": ("# hub:managed:start", "# hub:managed:end"),
}
_RENAME = {".gitignore-template": ".gitignore"}
_SKILLS_DESTS = (".claude/skills", ".agents/skills")


# ── Merge ─────────────────────────────────────────────────────────
def _managed_range(text: str, markers: tuple[str, str]) -> tuple[int, int] | None:
    start, end = markers
    if start not in text and end not in text:
        return None
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("duplicate or unpaired managed markers")
    s, e = text.index(start), text.index(end)
    if s > e:
        raise ValueError("start marker appears after end marker")
    e += len(end)
    nl = "\r\n" if text[e : e + 2] == "\r\n" else "\n"
    if text[e : e + len(nl)] == nl:
        e += len(nl)
    return s, e


def _merge_section(new: str, existing: str | None, markers: tuple[str, str]) -> str:
    if _managed_range(new, markers) is None:
        raise ValueError("source content missing managed markers")
    if existing is None:
        return new
    rng = _managed_range(existing, markers)
    if rng is None:
        return new + "\n" + existing
    return existing[: rng[0]] + new + existing[rng[1] :]


def _merge_json(overlay_text: str, existing: str | None) -> str:
    dump = lambda d: json.dumps(d, indent=2, ensure_ascii=False) + "\n"

    def unique(items: list) -> list:
        seen: set[str] = set()
        result = []
        for item in items:
            k = json.dumps(item, sort_keys=True)
            if k not in seen:
                seen.add(k)
                result.append(item)
        return result

    def merge(base: dict, over: dict) -> dict:
        result = {**base}
        for key, value in over.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge(result[key], value)
            elif key in result and isinstance(result[key], list) and isinstance(value, list):
                result[key] = unique(result[key] + value)
            else:
                result[key] = value
        return result

    overlay = json.loads(overlay_text)
    if existing is None:
        return dump(overlay)
    base = json.loads(existing)
    merged = merge(base, overlay)
    return existing if merged == base else dump(merged)


ReadFn = Callable[[str], str | None]


def _boot_assets() -> Traversable:
    return files("whub").joinpath("boot")


def _merged_files(
    boot_assets: Path,
    read: ReadFn,
) -> Iterator[tuple[str, str]]:
    for src in (boot_assets / "merge").rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(boot_assets / "merge").as_posix()
        dst_rel = _RENAME.get(rel, rel)
        markers = next(m for s, m in _MARKERS.items() if dst_rel.endswith(s))
        existing = read(dst_rel)
        merged = _merge_section(src.read_text(), existing, markers)
        if merged != existing:
            yield dst_rel, merged
    for src in (boot_assets / "json").rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(boot_assets / "json").as_posix()
        existing = read(rel)
        merged = _merge_json(src.read_text(), existing)
        if merged != existing:
            yield rel, merged


# ── Apply ─────────────────────────────────────────────────────────
def _process_error(error: OSError | subprocess.SubprocessError) -> str:
    if isinstance(error, subprocess.TimeoutExpired):
        return f"timeout ({error.timeout}s)"
    if isinstance(error, subprocess.CalledProcessError):
        return (
            (error.stderr or "").strip()
            or (error.stdout or "").strip()
            or f"exit status {error.returncode}"
        )
    return str(error)


def _init_local_codegraph(name: str, target: Path) -> None:
    codegraph = shutil.which("codegraph")
    if codegraph is None:
        click.echo(f"  {'WARN':6s}  {name}: codegraph not found; skipped")
        return
    try:
        subprocess.run(
            [codegraph, "init", str(target)],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        click.echo(
            f"  {'WARN':6s}  {name}: CodeGraph init failed:"
            f" {_process_error(error)}",
        )
        return
    click.echo(f"  {'init':6s}  {name} (CodeGraph)")


def _init_remote_codegraph(
    name: str,
    resource: RemoteResource,
    host: Host,
) -> None:
    try:
        run_ssh_command(
            host,
            f'source "$HOME/.nvm/nvm.sh" 2>/dev/null;'
            f" codegraph init {shlex.quote(resource.path)}",
            timeout=60,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        click.echo(
            f"  {'WARN':6s}  {name}: CodeGraph init failed:"
            f" {_process_error(error)}",
        )
        return
    click.echo(f"  {'init':6s}  {name} (CodeGraph)")


def _apply_local_boot(
    resource: SymlinkResource,
    project: Project,
) -> None:
    name = project.name
    target = resource._resolved_workspace_path
    if target is None:
        click.echo(f"  {'WARN':6s}  {name}: workspace path is unresolved")
        return
    if not target.exists():
        click.echo(f"  {'skip':6s}  {name} (not found)")
        return

    try:
        with as_file(_boot_assets()) as boot_assets:
            def read(rel: str) -> str | None:
                path = target / rel
                return path.read_text() if path.exists() else None

            for rel, content in _merged_files(boot_assets, read):
                destination = target / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content)
            for dest in _SKILLS_DESTS:
                shutil.copytree(
                    boot_assets / "skills",
                    target / dest,
                    dirs_exist_ok=True,
                )
    except (OSError, ValueError) as error:
        click.echo(f"  {'WARN':6s}  {name}: deploy failed: {error}")
        return
    click.echo(f"  {'done':6s}  {name}")
    _init_local_codegraph(name, target)


def _apply_workspace_boot() -> None:
    resource = workspace_hub_resource()
    resource._resolved_workspace_path = Path.cwd()
    _apply_local_boot(resource, Project(name="workspace-hub", resource=resource))


def _apply_remote_boot(
    resource: RemoteResource,
    project: Project,
) -> None:
    name = project.name
    host = resource._resolved_host
    if host is None:
        click.echo(f"  {'WARN':6s}  {name}: remote host is unresolved")
        return

    try:
        with as_file(_boot_assets()) as boot_assets:
            def read(rel: str) -> str | None:
                full = shlex.quote(f"{resource.path}/{rel}")
                result = run_ssh_command(
                    host,
                    f"test ! -f {full} || cat {full}",
                    timeout=30,
                    check=True,
                )
                return result.stdout or None

            for rel, content in _merged_files(boot_assets, read):
                full = f"{resource.path}/{rel}"
                run_ssh_command(
                    host,
                    f'mkdir -p "$(dirname {shlex.quote(full)})"'
                    f" && cat > {shlex.quote(full)}",
                    input=content,
                    timeout=30,
                    check=True,
                )
            for dest in _SKILLS_DESTS:
                run_rsync_command(
                    host,
                    str(boot_assets / "skills"),
                    f"{resource.path}/{dest}",
                    timeout=30,
                    check=True,
                )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        click.echo(
            f"  {'WARN':6s}  {name}: deploy failed:"
            f" {_process_error(error)}",
        )
        return
    click.echo(f"  {'done':6s}  {name}")
    _init_remote_codegraph(name, resource, host)


def _collect_boot_targets(manifest: Manifest) -> list[TargetItem[Project]]:
    targets: list[TargetItem[Project]] = []
    for project in manifest.projects:
        resource = project.resource
        if resource is None or not resource.boot:
            continue
        targets.append(TargetItem(resource, project))
    return targets


# ── CLI ───────────────────────────────────────────────────────────
@click.command()
@click.pass_context
def boot(ctx: click.Context) -> None:
    """Deploy agent bootstrap config to target resources."""
    manifest = get_manifest(ctx)
    targets = _collect_boot_targets(manifest)
    _apply_workspace_boot()
    on_targets(targets, local=_apply_local_boot, remote=_apply_remote_boot)
