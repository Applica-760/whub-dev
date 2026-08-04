"""Initialize CodeGraph for configured resources."""

from __future__ import annotations

import shlex
import shutil
import subprocess

from whub.core.remote import run_ssh_command
from whub.core.target import TargetItem, on_targets
from whub.models import Project, RemoteResource, SymlinkResource
from whub.services.manifest import ResolvedManifest
from whub.utils.process import format_process_error


def initialize_codegraph(manifest: ResolvedManifest) -> list[str]:
    lines: list[str] = []
    targets = [
        TargetItem(project.resource, (manifest, project))
        for project in manifest.projects
        if project.resource is not None and project.resource.codegraph
    ]

    def local(
        resource: SymlinkResource, data: tuple[ResolvedManifest, Project]
    ) -> None:
        resolved, project = data
        target = resolved.workspace_path(resource)
        if not target.exists():
            lines.append(f"  {'skip':6s}  {project.name} (not found)")
            return
        executable = shutil.which("codegraph")
        if executable is None:
            lines.append(f"  {'WARN':6s}  {project.name}: codegraph not found; skipped")
            return
        try:
            subprocess.run(
                [executable, "init", str(target)],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            lines.append(
                f"  {'WARN':6s}  {project.name}: CodeGraph init failed: {format_process_error(error)}"
            )
            return
        lines.append(f"  {'init':6s}  {project.name} (CodeGraph)")

    def remote(
        resource: RemoteResource, data: tuple[ResolvedManifest, Project]
    ) -> None:
        resolved, project = data
        try:
            run_ssh_command(
                resolved.remote_host(resource),
                f"codegraph init {shlex.quote(resolved.remote_path(resource))}",
                timeout=60,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            lines.append(
                f"  {'WARN':6s}  {project.name}: CodeGraph init failed: {format_process_error(error)}"
            )
            return
        lines.append(f"  {'init':6s}  {project.name} (CodeGraph)")

    on_targets(targets, local=local, remote=remote)
    return lines
