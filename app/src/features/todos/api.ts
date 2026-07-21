import { requestJson } from "../../api/client";
import type { TodosResponse } from "../../api/client";
import type { components } from "../../api/generated/schema";

export type TodoItem = components["schemas"]["TodoResponse"];
export type TodoCreateInput = components["schemas"]["CreateTodoRequest"];

export async function listTodos(): Promise<TodosResponse> {
  return requestJson<TodosResponse>("/api/todos");
}

export async function createTodo(input: TodoCreateInput): Promise<TodoItem> {
  return requestJson<TodoItem>("/api/todos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function completeTodo(todoId: number): Promise<TodoItem> {
  return requestJson<TodoItem>(`/api/todos/${todoId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ done: true }),
  });
}

export async function deleteTodo(todoId: number): Promise<void> {
  await requestJson<void>(`/api/todos/${todoId}`, { method: "DELETE" });
}
