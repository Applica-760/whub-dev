package manifest

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

type Manifest struct {
	Version  string          `yaml:"version" json:"version"`
	Hosts    map[string]Host `yaml:"hosts" json:"hosts"`
	Projects []Project       `yaml:"projects" json:"projects"`
}

type Host struct {
	Hostname     string `yaml:"hostname" json:"hostname"`
	User         string `yaml:"user" json:"user"`
	Port         int    `yaml:"port" json:"port"`
	IdentityFile string `yaml:"identity_file" json:"identity_file"`
	MountRoot    string `yaml:"mount_root" json:"mount_root"`
	WorktreeRoot string `yaml:"worktree_root" json:"worktree_root"`
	AutoMount    bool   `yaml:"auto_mount" json:"auto_mount"`
}

type Project struct {
	Name     string    `yaml:"name" json:"name"`
	Resource *Resource `yaml:"resource" json:"resource"`
}

type Resource struct {
	Type          string   `yaml:"type" json:"type"`
	WorkspacePath string   `yaml:"workspace_path" json:"workspace_path"`
	Source        string   `yaml:"source" json:"source,omitempty"`
	Host          string   `yaml:"host" json:"host,omitempty"`
	Path          string   `yaml:"path" json:"path,omitempty"`
	Git           *GitInfo `yaml:"git" json:"git,omitempty"`
	Codegraph     bool     `yaml:"codegraph" json:"codegraph"`
	Status        bool     `yaml:"status" json:"status"`
}

type GitInfo struct {
	URL    string `yaml:"url" json:"url"`
	Branch string `yaml:"branch" json:"branch,omitempty"`
}

func DefaultPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("resolve home directory: %w", err)
	}
	return filepath.Join(home, ".whub", "manifest.yaml"), nil
}

func LoadDefault() (Manifest, error) {
	path, err := DefaultPath()
	if err != nil {
		return Manifest{}, err
	}
	return Load(path)
}

func Load(path string) (Manifest, error) {
	file, err := os.Open(path)
	if err != nil {
		return Manifest{}, fmt.Errorf("read manifest %s: %w", path, err)
	}
	defer file.Close()

	decoder := yaml.NewDecoder(file)
	decoder.KnownFields(true)
	var manifest Manifest
	if err := decoder.Decode(&manifest); err != nil {
		return Manifest{}, fmt.Errorf("decode manifest %s: %w", path, err)
	}
	if manifest.Version == "" {
		manifest.Version = "2"
	}
	if manifest.Projects == nil {
		manifest.Projects = []Project{}
	}
	if err := manifest.Validate(); err != nil {
		return Manifest{}, fmt.Errorf("invalid manifest %s: %w", path, err)
	}
	return manifest, nil
}

func (manifest Manifest) Validate() error {
	if manifest.Version != "2" {
		return fmt.Errorf("version must be 2")
	}

	names := make(map[string]struct{}, len(manifest.Projects))
	paths := make(map[string]struct{}, len(manifest.Projects))
	for _, project := range manifest.Projects {
		if strings.TrimSpace(project.Name) == "" {
			return fmt.Errorf("project name must not be empty")
		}
		if _, exists := names[project.Name]; exists {
			return fmt.Errorf("duplicate project name: %s", project.Name)
		}
		names[project.Name] = struct{}{}

		if project.Resource == nil {
			continue
		}
		if err := project.Resource.validate(manifest.Hosts); err != nil {
			return fmt.Errorf("project %s: %w", project.Name, err)
		}
		if _, exists := paths[project.Resource.WorkspacePath]; exists {
			return fmt.Errorf("duplicate workspace path: %s", project.Resource.WorkspacePath)
		}
		paths[project.Resource.WorkspacePath] = struct{}{}
	}
	return nil
}

func (resource Resource) validate(hosts map[string]Host) error {
	if err := validateRelativePath(resource.WorkspacePath); err != nil {
		return fmt.Errorf("workspace_path: %w", err)
	}

	switch resource.Type {
	case "symlink":
		if !filepath.IsAbs(resource.Source) {
			return fmt.Errorf("source must be an absolute path")
		}
	case "remote":
		if _, exists := hosts[resource.Host]; !exists {
			return fmt.Errorf("unknown host: %s", resource.Host)
		}
		if err := validateRelativePath(resource.Path); err != nil {
			return fmt.Errorf("path: %w", err)
		}
	default:
		return fmt.Errorf("unknown resource type: %s", resource.Type)
	}
	return nil
}

func validateRelativePath(value string) error {
	if value == "" || filepath.IsAbs(value) {
		return fmt.Errorf("must be a relative path")
	}
	clean := filepath.Clean(value)
	if clean == ".." || strings.HasPrefix(clean, ".."+string(filepath.Separator)) {
		return fmt.Errorf("must not escape its root")
	}
	return nil
}
