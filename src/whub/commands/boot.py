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
from pathlib import Path
from typing import Callable, Iterator
from whub.commands import get_manifest
from whub.models import Host, RemoteResource, SymlinkResource
from whub.remote import run_rsync_command, run_ssh_command

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


def _merged_files(
    source: Path,
    read: ReadFn,
) -> Iterator[tuple[str, str]]:
    for src in (source / "merge").rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(source / "merge").as_posix()
        dst_rel = _RENAME.get(rel, rel)
        markers = next(m for s, m in _MARKERS.items() if dst_rel.endswith(s))
        existing = read(dst_rel)
        merged = _merge_section(src.read_text(), existing, markers)
        if merged != existing:
            yield dst_rel, merged
    for src in (source / "json").rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(source / "json").as_posix()
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


def _apply_local_boot(
    source: Path,
    targets: list[tuple[str, Path]],
    codegraph: str | None,
) -> None:
    if codegraph is None:
        click.echo("  WARN    codegraph not found; skipped for local resources")

    for name, target in targets:
        if not target.exists():
            click.echo(f"  {'skip':6s}  {name} (not found)")
            continue
        try:
            def read(rel: str) -> str | None:
                path = target / rel
                return path.read_text() if path.exists() else None

            for rel, content in _merged_files(source, read):
                destination = target / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content)
            for dest in _SKILLS_DESTS:
                shutil.copytree(
                    source / "skills",
                    target / dest,
                    dirs_exist_ok=True,
                )
        except (OSError, ValueError) as error:
            click.echo(f"  {'WARN':6s}  {name}: deploy failed: {error}")
            continue
        click.echo(f"  {'done':6s}  {name}")

        if codegraph is None:
            continue
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
            continue
        click.echo(f"  {'init':6s}  {name} (CodeGraph)")

def _apply_remote_boot(
    source: Path,
    targets: list[tuple[str, RemoteResource]],
    hosts: dict[str, Host],
) -> None:
    for name, resource in targets:
        host = hosts[resource.host]
        try:
            def read(rel: str) -> str | None:
                full = shlex.quote(f"{resource.path}/{rel}")
                result = run_ssh_command(
                    host,
                    f"test ! -f {full} || cat {full}",
                    timeout=30,
                    check=True,
                )
                return result.stdout or None

            for rel, content in _merged_files(source, read):
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
                    str(source / "skills"),
                    f"{resource.path}/{dest}",
                    timeout=30,
                    check=True,
                )
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            click.echo(
                f"  {'WARN':6s}  {name}: deploy failed:"
                f" {_process_error(error)}",
            )
            continue
        click.echo(f"  {'done':6s}  {name}")

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
            continue
        click.echo(f"  {'init':6s}  {name} (CodeGraph)")


# ── CLI ───────────────────────────────────────────────────────────
@click.command()
@click.pass_context
def boot(ctx: click.Context) -> None:
    """Deploy agent bootstrap config to target resources."""
    manifest = get_manifest(ctx)
    local_targets = [("workspace-hub", manifest.workspace_root)]
    remote_targets = []
    for project in manifest.projects:
        resource = project.resource
        if isinstance(resource, SymlinkResource) and resource.boot:
            local_targets.append((
                project.name,
                manifest.resolve_path(resource.workspace_path),
            ))
        elif isinstance(resource, RemoteResource) and resource.boot:
            remote_targets.append((project.name, resource))

    with as_file(files("whub").joinpath("boot")) as source:
        _apply_local_boot(
            source,
            local_targets,
            shutil.which("codegraph"),
        )
        _apply_remote_boot(source, remote_targets, manifest.hosts)
