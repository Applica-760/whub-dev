"""whub boot — distribute packaged agent config to target projects.
boot/ layout (directory = operation):
  merge/   section insert   (.md → HTML, .gitignore → #, .toml → #)
  json/    recursive merge   (JSON)
  skills/  → .claude/skills + .agents/skills
"""

from __future__ import annotations

import hashlib
import json
import secrets
import shlex
import shutil
import subprocess
import tempfile
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path, PurePosixPath
from typing import Callable, Iterator

import click

from whub.commands import get_manifest
from whub.models import (
    Host,
    Manifest,
    Project,
    RemoteResource,
    SymlinkResource,
    workspace_hub_resource,
)
from whub.core.remote import run_rsync_command, run_ssh_command
from whub.core.target import TargetItem, on_targets
from whub.utils.managed_block import replace_or_prepend_block
from whub.utils.process import format_process_error

_MARKERS = {
    ".md": ("<!-- hub:managed:start -->", "<!-- hub:managed:end -->"),
    ".toml": ("# hub:managed:start", "# hub:managed:end"),
    ".gitignore": ("# hub:managed:start", "# hub:managed:end"),
}
_RENAME = {".gitignore-template": ".gitignore"}
_SKILLS_DESTS = (".claude/skills", ".agents/skills")
_WFLOW_LAYOUT_VERSION = "1"
_WFLOW_LAUNCHER = """#!/bin/sh
set -eu
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
export PYTHONPATH="$data_home/wflow/current/src"
exec "$data_home/wflow/current/venv/bin/python" -m whub.wflow "$@"
"""


# ── Merge ─────────────────────────────────────────────────────────
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


def _wflow_assets() -> Traversable:
    return files("whub").joinpath("wflow")


def _wflow_payload_files(source: Path) -> Iterator[Path]:
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if (
            "__pycache__" in relative.parts
            or path.suffix == ".pyc"
            or path.name == ".DS_Store"
        ):
            continue
        yield path


def _wflow_content_hash(source: Path) -> str:
    digest = hashlib.sha256()
    digest.update(f"layout:{_WFLOW_LAYOUT_VERSION}\0".encode())
    digest.update(_WFLOW_LAUNCHER.encode())
    for path in _wflow_payload_files(source):
        relative = path.relative_to(source).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _copy_wflow_payload(source: Path, destination: Path) -> None:
    for path in _wflow_payload_files(source):
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _remote_wflow_state(host: Host) -> tuple[str, str, str | None]:
    result = run_ssh_command(
        host,
        """set -eu
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
case "$data_home" in
  /*) ;;
  *) exit 2 ;;
esac
base="$data_home/wflow"
bin_dir="$HOME/.local/bin"
printf '%s\\n%s\\n' "$base" "$bin_dir"
if test -f "$base/current/.content-hash" \\
  && test -x "$bin_dir/wflow" \\
  && "$bin_dir/wflow" --help >/dev/null 2>&1; then
  cat "$base/current/.content-hash"
fi
""",
        timeout=30,
        check=True,
    )
    lines = result.stdout.splitlines()
    if len(lines) not in (2, 3):
        raise ValueError("invalid remote wflow state")
    base, bin_dir = lines[:2]
    if not PurePosixPath(base).is_absolute() or not PurePosixPath(bin_dir).is_absolute():
        raise ValueError("remote wflow paths must be absolute")
    return base, bin_dir, lines[2] if len(lines) == 3 else None


def _install_remote_wflow(name: str, host: Host) -> None:
    try:
        with as_file(_wflow_assets()) as source:
            content_hash = _wflow_content_hash(source)
            base, bin_dir, installed_hash = _remote_wflow_state(host)
            if installed_hash == content_hash:
                click.echo(f"  {'skip':6s}  {name} (wflow unchanged)")
                return

            staging = f"{base}/.staging-{content_hash}"
            run_ssh_command(
                host,
                f"rm -rf {shlex.quote(staging)}"
                f" && mkdir -p {shlex.quote(f'{staging}/src/whub')}"
                f" && : > {shlex.quote(f'{staging}/src/whub/__init__.py')}",
                timeout=30,
                check=True,
            )
            with tempfile.TemporaryDirectory() as temporary:
                payload = Path(temporary) / "wflow"
                _copy_wflow_payload(source, payload)
                run_rsync_command(
                    host,
                    str(payload),
                    f"{staging}/src/whub/wflow",
                    timeout=30,
                    check=True,
                )

            version = f"{base}/versions/{content_hash}-{secrets.token_hex(4)}"
            current_link = f"{base}/.current-{content_hash}"
            launcher = f"{bin_dir}/wflow"
            launcher_tmp = f"{launcher}.{content_hash}.tmp"
            requirements = f"{staging}/src/whub/wflow/requirements.txt"
            run_ssh_command(
                host,
                f"""set -eu
python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 12))'
python3 -m venv {shlex.quote(f"{staging}/venv")}
{shlex.quote(f"{staging}/venv/bin/python")} -m pip install \\
  --disable-pip-version-check --no-input -r {shlex.quote(requirements)}
printf '%s\\n' {shlex.quote(content_hash)} > {shlex.quote(f"{staging}/.content-hash")}
mkdir -p {shlex.quote(f"{base}/versions")} {shlex.quote(bin_dir)}
cat > {shlex.quote(launcher_tmp)}
chmod 755 {shlex.quote(launcher_tmp)}
mv {shlex.quote(staging)} {shlex.quote(version)}
rm -f {shlex.quote(current_link)}
ln -s {shlex.quote(version)} {shlex.quote(current_link)}
mv -Tf {shlex.quote(current_link)} {shlex.quote(f"{base}/current")}
mv -f {shlex.quote(launcher_tmp)} {shlex.quote(launcher)}
""",
                input=_WFLOW_LAUNCHER,
                timeout=180,
                check=True,
            )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        click.echo(
            f"  {'WARN':6s}  {name}: wflow install failed:"
            f" {format_process_error(error)}",
        )
        return
    click.echo(f"  {'done':6s}  {name} (wflow)")


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
        merged = replace_or_prepend_block(src.read_text(), existing, markers)
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
            f" {format_process_error(error)}",
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
            f" {format_process_error(error)}",
        )
        return
    click.echo(f"  {'init':6s}  {name} (CodeGraph)")


def _apply_local_boot(
    resource: SymlinkResource,
    project: Project,
) -> None:
    name = project.name
    target = resource._resolved_workspace_path
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
    _apply_local_boot(resource, Project(name="workspace-hub", resource=resource))


def _apply_remote_boot(
    resource: RemoteResource,
    project: Project,
) -> None:
    name = project.name
    host = resource._resolved_host
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
            f" {format_process_error(error)}",
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


def _collect_wflow_hosts(
    targets: list[TargetItem[Project]],
) -> list[tuple[str, Host]]:
    hosts: dict[str, Host] = {}
    for target in targets:
        resource = target.resource
        if isinstance(resource, RemoteResource):
            hosts.setdefault(resource.host, resource._resolved_host)
    return list(hosts.items())


# ── CLI ───────────────────────────────────────────────────────────
@click.command()
@click.pass_context
def boot(ctx: click.Context) -> None:
    """Deploy agent bootstrap config to target resources."""
    manifest = get_manifest(ctx)
    targets = _collect_boot_targets(manifest)
    _apply_workspace_boot()
    for name, host in _collect_wflow_hosts(targets):
        _install_remote_wflow(name, host)
    on_targets(targets, local=_apply_local_boot, remote=_apply_remote_boot)
