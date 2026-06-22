"""whub boot — distribute packaged agent config to target projects."""

from __future__ import annotations
import json
import shlex
import shutil
import subprocess
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
import click
from whub.commands import build_ssh_command, get_manifest
from whub.models import Host, MountResource

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


def _copy_tree(src: Traversable, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_dir():
            _copy_tree(item, dst / item.name)
        else:
            (dst / item.name).write_bytes(item.read_bytes())


def _deploy_merged(boot_source: Traversable, target: Path) -> None:
    for relative in (".claude/CLAUDE.md", "AGENTS.md"):
        _deploy_marked(
            boot_source.joinpath(relative).read_text(),
            target / relative,
            ("<!-- hub:managed:start -->", "<!-- hub:managed:end -->"),
            relative,
        )
    gitignore = "\n".join((
        "# hub:managed:start", ".agents/", ".claude/", ".codex/",
        ".codegraph/", ".mcp.json", "AGENTS.md", "# hub:managed:end",
    )) + "\n"
    _deploy_marked(
        gitignore, target / ".gitignore",
        ("# hub:managed:start", "# hub:managed:end"), "generated .gitignore",
    )
    _merge_settings(
        json.loads(boot_source.joinpath(".claude/settings.json").read_text()),
        target / ".claude/settings.json",
    )


def _deploy_to_project(boot_source: Traversable, target: Path) -> None:
    for relative in (".codex/config.toml", ".mcp.json"):
        dst = target / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(boot_source.joinpath(relative).read_bytes())
    for skill_target in (target / ".claude/skills", target / ".agents/skills"):
        _copy_tree(boot_source.joinpath("skills"), skill_target)
    _deploy_merged(boot_source, target)


def _deploy_to_remote(
    boot_source: Traversable, host: Host, remote_path: str, local_path: Path,
) -> str | None:
    src = str(boot_source)
    identity = str(Path(host.identity_file).expanduser())
    ssh_opt = f"ssh -i {shlex.quote(identity)} -p {host.port}"
    dest = f"{host.user}@{host.hostname}:{remote_path}"
    for args in (
        [f"{src}/.codex", f"{src}/.mcp.json", f"{dest}/"],
        [f"{src}/skills/", f"{dest}/.claude/skills/"],
        [f"{src}/skills/", f"{dest}/.agents/skills/"],
    ):
        result = subprocess.run(
            ["rsync", "-a", "-e", ssh_opt, *args],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return result.stderr.strip() or f"exit status {result.returncode}"
    _deploy_merged(boot_source, local_path)
    return None


def _init_codegraph(executable: str, target: Path) -> str | None:
    try:
        result = subprocess.run(
            [executable, "init", str(target)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return "timeout (60s)"
    except OSError as error:
        return str(error)
    if result.returncode == 0:
        return None
    return (
        result.stderr.strip()
        or result.stdout.strip()
        or f"exit status {result.returncode}"
    )


def _init_codegraph_remote(host: Host, remote_path: str) -> str | None:
    """Run codegraph init on the remote host via SSH."""
    rp = shlex.quote(remote_path)
    cmd = build_ssh_command(
        host,
        f'source "$HOME/.nvm/nvm.sh" 2>/dev/null; codegraph init {rp}',
    )
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return "timeout (60s)"
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
    boot_source = files("whub").joinpath("boot")
    codegraph = shutil.which("codegraph")
    if codegraph is None:
        click.echo("  WARN    codegraph not found; skipped for local resources")

    targets = [("workspace-hub", manifest.root, None)] + [
        (r.name, manifest.resolve_path(r.path), r)
        for r in manifest.resources if r.boot
    ]

    for name, path, resource in targets:
        ok = path.exists()
        if not ok:
            click.echo(f"  {'skip':6s}  {name} (not found)")
            continue

        is_remote = isinstance(resource, MountResource)
        if is_remote:
            host = manifest.hosts[resource.host]
            err = _deploy_to_remote(boot_source, host, resource.remote_path, path)
            if err:
                click.echo(f"  {'WARN':6s}  {name}: remote deploy failed: {err}")
                continue
        else:
            _deploy_to_project(boot_source, path)
        click.echo(f"  {'done':6s}  {name}")

        if is_remote:
            error = _init_codegraph_remote(host, resource.remote_path)
        elif codegraph:
            error = _init_codegraph(codegraph, path)
        else:
            continue
        click.echo(
            f"  {'init':6s}  {name} (CodeGraph)"
            if error is None
            else f"  {'WARN':6s}  {name}: CodeGraph init failed: {error}"
        )
