import { Anchor, Stack } from "@mantine/core";
import { NavLink, useParams } from "react-router";

import { PageFrame } from "../../components/PageFrame";
import { TaskDetailWidget } from "./TaskDetailWidget";
import { TaskFlowGraphWidget } from "./TaskFlowGraphWidget";

export function TaskDetailPage() {
  const { project, taskId } = useParams();

  return (
    <PageFrame>
      <Stack gap="md">
        {taskId && <TaskFlowGraphWidget project={project} taskId={taskId} />}
        <TaskDetailWidget
          action={
            <Anchor component={NavLink} size="sm" to="/tasks">
              一覧へ戻る
            </Anchor>
          }
          emptyMessage="Task IDがありません"
          project={project}
          taskId={taskId}
        />
      </Stack>
    </PageFrame>
  );
}
