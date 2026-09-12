package manifest

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoad(t *testing.T) {
	path := filepath.Join(t.TempDir(), "manifest.yaml")
	content := `version: "2"
hosts:
  home:
    hostname: ssh.example.test
    user: whub
    identity_file: /Users/whub/.ssh/id_ed25519
    mount_root: /srv/whub
projects:
  - name: local
    resource:
      type: symlink
      workspace_path: projects/local
      source: /Users/whub/local
  - name: remote
    resource:
      type: remote
      host: home
      path: remote
      workspace_path: projects/remote
  - name: no-resource
`
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}

	manifest, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(manifest.Projects) != 3 {
		t.Fatalf("projects = %d, want 3", len(manifest.Projects))
	}
	if manifest.Projects[1].Resource.Host != "home" {
		t.Fatalf("remote host = %q, want home", manifest.Projects[1].Resource.Host)
	}
}

func TestLoadRejectsUnsafeWorkspacePath(t *testing.T) {
	path := filepath.Join(t.TempDir(), "manifest.yaml")
	content := `version: "2"
projects:
  - name: local
    resource:
      type: symlink
      workspace_path: ../outside
      source: /Users/whub/local
`
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}

	if _, err := Load(path); err == nil {
		t.Fatal("Load() succeeded for an unsafe workspace path")
	}
}
