# Manifest reference

`~/.whub/manifest.yaml` はworkspaceに公開するProjectとResource、remote hostを定義する。

```yaml
version: "2"

hosts:
  host-name:
    hostname: "..."
    user: "..."
    identity_file: "~/.ssh/id_rsa"
    mount_root: /remote
    auto_mount: false

projects:
  - name: whub-dev
    resource:
      type: symlink
      workspace_path: whub-dev
      source: /path/to/whub
      codegraph: true

  - name: remote-project
    resource:
      type: remote
      host: host-name
      path: sub/dir
      workspace_path: projects/remote-project
      status: false
      codegraph: true
```

## Rules

- Projectで必須のフィールドは `name` だけである。
- Resourceはtop-levelではなく、対応するProjectの `resource` 配下に定義する。
- 全Resourceに `workspace_path` が必要である。
- remoteの `path` はhostの `mount_root` からの相対pathであり、絶対pathは指定しない。
- `auto_mount` は無引数 `whub remote mount` の対象をhost単位で制御する。
- `status: false` は `whub status` の対象から除外する。
