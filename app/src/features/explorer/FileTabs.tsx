type FileTabsProps = {
  paths: string[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onClose: (path: string) => void;
};

export function FileTabs({
  paths,
  selectedPath,
  onClose,
  onSelect,
}: FileTabsProps) {
  if (!paths.length) return null;
  return (
    <div className="explorer-file-tabs">
      {paths.map((path) => (
        <div
          className="explorer-file-tab"
          data-active={path === selectedPath || undefined}
          key={path}
          title={path}
        >
          <button onClick={() => onSelect(path)} type="button">
            {path.split("/").at(-1)}
          </button>
          <button
            aria-label={`${path}を閉じる`}
            className="explorer-file-tab-close"
            onClick={() => onClose(path)}
            type="button"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
