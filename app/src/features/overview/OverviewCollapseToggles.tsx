import { ActionIcon } from "@mantine/core";
import {
  IconLayoutSidebarLeftCollapse,
  IconLayoutSidebarLeftExpand,
  IconLayoutSidebarRightCollapse,
  IconLayoutSidebarRightExpand,
} from "@tabler/icons-react";

import type {
  OverviewCollapseState,
  OverviewSideName,
} from "./useOverviewCollapse";

type OverviewCollapseTogglesProps = {
  collapsed: OverviewCollapseState;
  onToggle: (side: OverviewSideName) => void;
};

const SIDES: OverviewSideName[] = ["left", "right"];

const SIDE_LABEL: Record<OverviewSideName, string> = {
  left: "左サイド",
  right: "右サイド",
};

const SIDE_ICON = {
  left: {
    collapse: IconLayoutSidebarLeftCollapse,
    expand: IconLayoutSidebarLeftExpand,
  },
  right: {
    collapse: IconLayoutSidebarRightCollapse,
    expand: IconLayoutSidebarRightExpand,
  },
} as const;

export function OverviewCollapseToggles({
  collapsed,
  onToggle,
}: OverviewCollapseTogglesProps) {
  return SIDES.map((side) => {
    const isCollapsed = collapsed[side];
    const Icon = SIDE_ICON[side][isCollapsed ? "expand" : "collapse"];
    const label = `${SIDE_LABEL[side]}を${isCollapsed ? "展開する" : "折りたたむ"}`;

    return (
      <ActionIcon
        aria-expanded={!isCollapsed}
        aria-label={label}
        key={side}
        onClick={() => onToggle(side)}
        title={label}
        variant="subtle"
      >
        <Icon aria-hidden size={18} stroke={1.5} />
      </ActionIcon>
    );
  });
}
