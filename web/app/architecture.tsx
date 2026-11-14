import type { AgentEvent } from "./events";

type Stage = "gateway" | "agent" | "tools" | "reply";

// The box in the diagram that each event belongs to.
function stageOf(event: AgentEvent): Stage | null {
  switch (event.type) {
    case "turn_start":
      return "gateway";
    case "llm_call":
      return "agent";
    case "tool_call":
    case "tool_result":
      return "tools";
    case "turn_end":
      return "reply";
    case "error":
      return null;
  }
}

// What the agent is doing right now, judged from the last event it sent.
function activeStage(events: AgentEvent[]): Stage | null {
  const last = events.at(-1);
  switch (last?.type) {
    case "turn_start":
    case "tool_result":
      return "agent"; // waiting for the model to answer
    case "llm_call":
      return last.stop_reason === "tool_use" ? "tools" : "reply";
    case "tool_call":
      return "tools";
    default:
      return null; // idle, finished or failed
  }
}

// The architecture diagram. Boxes the turn has passed through are lit,
// and the box the agent is working in right now glows.
export default function Architecture({ events }: { events: AgentEvent[] }) {
  const active = activeStage(events);
  const visited = new Set(events.map(stageOf));
  const count = (type: AgentEvent["type"]) => events.filter((e) => e.type === type).length;

  const box = (stage: Stage, title: string, detail: string) => (
    <div className={`box ${visited.has(stage) ? "visited" : ""} ${active === stage ? "active" : ""}`}>
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );

  return (
    <div className="arch">
      <div className="group">
        <h3>Harness: one turn, from your message to the reply</h3>
        <div className="flow">
          {box("gateway", "Gateway", "web page · terminal")}
          <span className="arrow">→</span>
          <div className="group loop">
            <h3>Loop: up to 10 steps</h3>
            {box("agent", "LLM agent", `reasons · ${count("llm_call")} call(s)`)}
            <span className="arrow">↓ ↑</span>
            {box("tools", "Tools", `acts · ${count("tool_call")} call(s)`)}
          </div>
          <span className="arrow">→</span>
          {box("reply", "Reply", "back to you")}
        </div>
      </div>
      <div className="planned">
        <Planned title="Memory" boxes={["Working memory", "Retrieval gate", "Facts"]} />
        <Planned title="LLM Ops" boxes={["Trace", "Evals"]} />
      </div>
    </div>
  );
}

function Planned({ title, boxes }: { title: string; boxes: string[] }) {
  return (
    <div className="group">
      <h3>{title}: coming soon</h3>
      <div className="flow">
        {boxes.map((name) => (
          <div key={name} className="box planned-box">
            <strong>{name}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}
