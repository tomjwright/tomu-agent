// The events the Python agent streams, one per step (see tomu/events.py).

export type AgentEvent = { at: number } & (
  | { type: "turn_start"; message: string }
  | { type: "memory_recall"; history: number; gate: "retrieve" | "skip"; facts: string[]; skills: string[] }
  | {
      type: "llm_call";
      iteration: number;
      text: string;
      stop_reason: string;
      usage: { input: number; output: number };
      duration_ms: number;
    }
  | { type: "tool_call"; iteration: number; id: string; name: string; input: object }
  | { type: "approval_request"; id: string; name: string; input: object }
  | { type: "approval_result"; id: string; name: string; approved: boolean }
  | { type: "tool_result"; id: string; name: string; output: string; is_error: boolean; duration_ms: number }
  | { type: "turn_end"; reply: string; iterations: number; reason: "no_tool_calls" | "max_iterations" }
  | { type: "memory_save" }
  | { type: "consolidation_start"; messages: number }
  | { type: "consolidation_end"; messages: number; facts: string[]; usage: { input: number; output: number }; duration_ms: number }
  | { type: "error"; message: string }
  | { type: "eval_result"; message: string; passed: boolean; problems: string[]; tools: string[]; reply: string; tokens: number; model_calls: number }
  | { type: "evals_end"; passed: number; total: number; tokens: number; duration_ms: number }
);

export type PastTurn = { id: number; message: string; saved_at: number };

const API_URL = process.env.NEXT_PUBLIC_TOMU_API ?? "http://localhost:8000";

// The latest saved turns, newest first, from any front door (web, terminal or Telegram).
export async function listPastTurns(): Promise<PastTurn[]> {
  const response = await fetch(`${API_URL}/api/traces`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

// Play a saved turn's events back at their original pace, with long pauses cut to 1 second.
// Nothing runs again: no model calls and no tools.
export async function replayTurn(id: number, onEvent: (event: AgentEvent) => void) {
  const response = await fetch(`${API_URL}/api/traces/${id}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const events: AgentEvent[] = await response.json();
  for (const [i, event] of events.entries()) {
    const pause = i === 0 ? 0 : Math.min(event.at - events[i - 1].at, 1);
    await new Promise((resolve) => setTimeout(resolve, pause * 1000));
    onEvent(event);
  }
}

// Tell the waiting turn your answer to an approval_request.
export async function answerApproval(id: string, approved: boolean) {
  const response = await fetch(`${API_URL}/api/approve`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ id, approved }),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
}

// POST the message and call onEvent for each `data: {...}` block as it arrives.
export function streamChat(message: string, onEvent: (event: AgentEvent) => void) {
  return streamEvents("/api/chat", { message }, onEvent);
}

// The Consolidate button: turns messages not yet consolidated into facts.
export function streamConsolidate(onEvent: (event: AgentEvent) => void) {
  return streamEvents("/api/consolidate", {}, onEvent);
}

// The Evals button: sends every message in evals/cases.json and streams one result per case.
export function streamEvals(onEvent: (event: AgentEvent) => void) {
  return streamEvents("/api/evals", {}, onEvent);
}

async function streamEvents(path: string, body: object, onEvent: (event: AgentEvent) => void) {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? ""; // keep any half-received block for the next read
    for (const block of blocks) {
      if (block.startsWith("data: ")) onEvent(JSON.parse(block.slice("data: ".length)));
    }
  }
}
