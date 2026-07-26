export function stateColor(state: string | null | undefined): string {
  if (state === "completed") {
    return "green";
  }
  if (state === "in_progress") {
    return "blue";
  }
  return "gray";
}
