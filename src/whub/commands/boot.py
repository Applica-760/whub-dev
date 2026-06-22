"""whub boot — distribute packaged agent config to target projects.

boot/ layout (directory = operation):
  merge/   section insert   (.md → HTML, .gitignore → #, .toml → #)
  json/    recursive merge   (JSON)
  skills/  → .claude/skills + .agents/skills
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Callable, Iterator

import click

from whub.commands import build_rsync_command, build_ssh_command, get_manifest
from whub.models import Host, MountResource

_MARKERS = {
    ".md": ("<!-- hub:managed:start -->", "<!-- hub:managed:end -->"),
    ".toml": ("# hub:managed:start", "# hub:managed:end"),
    ".gitignore": ("# hub:managed:start", "# hub:managed:end"),
}
_RENAME = {".gitignore-template": ".gitignore"}
_SKILLS_DESTS = (".claude/skills", ".agents/skills")


# ── Merge logic ───────────────────────────────────────────────────


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


# ── Helpers ───────────────────────────────────────────────────────


def _walk(root: Traversable) -> Iterator[tuple[Traversable, str]]:
    def _inner(node: Traversable, prefix: str) -> Iterator[tuple[Traversable, str]]:
        for item in node.iterdir():
            rel = f"{prefix}{item.name}"
            if item.is_dir():
                yield from _inner(item, f"{rel}/")
            else:
                yield item, rel
    try:
        yield from _inner(root, "")
    except (FileNotFoundError, NotADirectoryError):
        return


def _copy_tree(src: Traversable, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_dir():
            _copy_tree(item, dst / item.name)
        else:
            (dst / item.name).write_bytes(item.read_bytes())


def _run_command(command: list[str], timeout: int) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"timeout ({timeout}s)"
    except OSError as error:
        return str(error)
    if result.returncode == 0:
        return None
    return result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"


# ── Deploy (shared loop) ─────────────────────────────────────────

ReadFn = Callable[[str], str | None]
WriteFn = Callable[[str, str], None]


def _deploy_merged(boot: Traversable, read: ReadFn, write: WriteFn) -> None:
    for src, rel in _walk(boot / "merge"):
        dst_rel = _RENAME.get(rel, rel)
        markers = next(m for s, m in _MARKERS.items() if dst_rel.endswith(s))
        existing = read(dst_rel)
        merged = _merge_section(src.read_text(), existing, markers)
        if merged != existing:
            write(dst_rel, merged)
    for src, rel in _walk(boot / "json"):
        existing = read(rel)
        merged = _merge_json(src.read_text(), existing)
        if merged != existing:
            write(rel, merged)


def _deploy_local(
    boot: Traversable, target: Path, codegraph: str | None,
) -> tuple[str | None, str | None]:
    def read(rel: str) -> str | None:
        p = target / rel
        return p.read_text() if p.exists() else None

    def write(rel: str, content: str) -> None:
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        (target / rel).write_text(content)

    _deploy_merged(boot, read, write)
    for dest in _SKILLS_DESTS:
        _copy_tree(boot / "skills", target / dest)

    cg_err: str | None | bool = (
        _run_command([codegraph, "init", str(target)], 60) if codegraph else False
    )
    return None, cg_err


def _deploy_remote(
    boot: Traversable, host: Host, remote_path: str,
) -> tuple[str | None, str | None]:
    def read(rel: str) -> str | None:
        r = subprocess.run(
            build_ssh_command(host, f"cat {shlex.quote(f'{remote_path}/{rel}')}"),
            capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None

    def write(rel: str, content: str) -> None:
        full = f"{remote_path}/{rel}"
        subprocess.run(
            build_ssh_command(host, f'mkdir -p "$(dirname {shlex.quote(full)})" && cat > {shlex.quote(full)}'),
            input=content, capture_output=True, text=True, timeout=30)

    _deploy_merged(boot, read, write)

    boot_dir = str(boot)

    def rsync(src: str, dest: str) -> str | None:
        r = subprocess.run(
            build_rsync_command(host, src, dest),
            capture_output=True, text=True, timeout=30)
        return (r.stderr.strip() or f"exit status {r.returncode}") if r.returncode else None

    for dest in _SKILLS_DESTS:
        if err := rsync(f"{boot_dir}/skills", f"{remote_path}/{dest}"):
            return err, None

    cg_err = _run_command(build_ssh_command(
        host, f'source "$HOME/.nvm/nvm.sh" 2>/dev/null;'
        f" codegraph init {shlex.quote(remote_path)}"), 60)
    return None, cg_err


# ── CLI ───────────────────────────────────────────────────────────


@click.command()
@click.pass_context
def boot(ctx: click.Context) -> None:
    """Deploy agent bootstrap config to target resources."""
    manifest = get_manifest(ctx)
    boot_source = files("whub").joinpath("boot")
    codegraph = shutil.which("codegraph")
    if codegraph is None:
        click.echo("  WARN    codegraph not found; skipped for local resources")

    targets = [("workspace-hub", manifest.root, None)] + [
        (r.name, manifest.resolve_path(r.path), r)
        for r in manifest.resources if r.boot
    ]
    for name, path, resource in targets:
        if isinstance(resource, MountResource):
            host = manifest.hosts[resource.host]
            deploy_err, cg_err = _deploy_remote(boot_source, host, resource.remote_path)
        elif path.exists():
            deploy_err, cg_err = _deploy_local(boot_source, path, codegraph)
        else:
            click.echo(f"  {'skip':6s}  {name} (not found)")
            continue

        if deploy_err:
            click.echo(f"  {'WARN':6s}  {name}: deploy failed: {deploy_err}")
            continue
        click.echo(f"  {'done':6s}  {name}")
        if isinstance(cg_err, str):
            click.echo(f"  {'WARN':6s}  {name}: CodeGraph init failed: {cg_err}")
        elif cg_err is None:
            click.echo(f"  {'init':6s}  {name} (CodeGraph)")
