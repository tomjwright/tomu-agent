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
  | { type: "error"; message: string }
);

const API_URL = process.env.NEXT_PUBLIC_TOMU_API ?? "http://localhost:8000";

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
export async function streamChat(message: string, onEvent: (event: AgentEvent) => void) {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message }),
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
