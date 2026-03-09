const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface StepLog {
  step: number;
  type: "tool_call" | "tool_result" | "final" | "start" | "done" | "error";
  content: string;
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  task_id?: number;
}

export interface Task {
  id: number;
  task: string;
  tools: string[] | null;
  status: "pending" | "running" | "completed" | "failed";
  result: string | null;
  steps: StepLog[];
  error: string | null;
  created_at: string;
}

export interface Tool {
  name: string;
  description: string;
  icon: string;
}

export async function getTools(): Promise<Tool[]> {
  const res = await fetch(`${API_BASE}/tools`);
  const data = await res.json();
  return data.tools;
}

export async function getTasks(): Promise<Task[]> {
  const res = await fetch(`${API_BASE}/tasks`);
  const data = await res.json();
  return data.tasks;
}

export async function getTask(id: number): Promise<Task> {
  const res = await fetch(`${API_BASE}/tasks/${id}`);
  return res.json();
}

/**
 * Run a task with SSE streaming.
 * Calls onStep for each streamed event, onDone when finished.
 */
export async function runTaskStream(
  task: string,
  tools: string[] | null,
  onStep: (step: StepLog) => void,
  onDone: () => void,
  onError: (msg: string) => void
) {
  const res = await fetch(`${API_BASE}/run/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, tools }),
  });

  if (!res.ok || !res.body) {
    onError("Failed to connect to agent.");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const payload: StepLog = JSON.parse(line.slice(6));
        if (payload.type === "done") {
          onDone();
        } else if (payload.type === "error") {
          onError(payload.content);
        } else {
          onStep(payload);
        }
      } catch {
        // malformed chunk, skip
      }
    }
  }
}
