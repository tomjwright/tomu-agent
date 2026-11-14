import type { AgentEvent } from "./events";

type Stage =
  | "gateway" | "working" | "agent" | "tools" | "reply"
  | "gate" | "semantic" | "procedural" | "episodic";

// The boxes in the diagram that each event belongs to.
function stagesOf(event: AgentEvent): Stage[] {
  switch (event.type) {
    case "turn_start":
      return ["gateway"];
    case "memory_recall":
      return [
        "gate", "episodic", "working",
        ...(event.gate === "retrieve" ? ["semantic" as const] : []),
        ...(event.skills.length ? ["procedural" as const] : []),
      ];
    case "llm_call":
      return ["agent"];
    case "tool_call":
    case "tool_result":
      return event.name === "remember" ? ["tools", "semantic"] : ["tools"];
    case "turn_end":
      return ["reply"];
    case "memory_save":
      return ["episodic"];
    case "error":
      return [];
  }
}

// What the agent is doing right now, judged from the last event it sent.
function activeStage(events: AgentEvent[]): Stage | null {
  const last = events.at(-1);
  switch (last?.type) {
    case "turn_start":
      return "gate"; // deciding what to pull from memory
    case "memory_recall":
    case "tool_result":
      return "agent"; // waiting for the model to answer
    case "llm_call":
      return last.stop_reason === "tool_use" ? "tools" : "reply";
    case "tool_call":
      return "tools";
    case "turn_end":
      return "episodic"; // saving the turn
    default:
      return null; // idle, finished or failed
  }
}

// Where each box sits in the drawing (x, y, width). Every box is 54 high.
const H = 54;
const BOX: Record<Stage, [number, number, number]> = {
  gateway: [30, 85, 120],
  working: [190, 85, 130],
  agent: [355, 60, 120],
  tools: [355, 140, 120],
  reply: [515, 85, 95],
  gate: [190, 270, 130], // drawn as a diamond
  semantic: [20, 400, 150],
  procedural: [180, 400, 150],
  episodic: [340, 400, 150],
};

// The links between boxes. A link lights up once both of its ends have been
// visited, and flows while its target is the active box.
type Link = { from: Stage; to: Stage; path: string; label?: [string, number, number] };
const LINKS: Link[] = [
  { from: "gateway", to: "working", path: "M150 112 H186" },
  { from: "working", to: "agent", path: "M320 112 H336" },
  { from: "agent", to: "tools", path: "M410 114 V136" },
  { from: "tools", to: "agent", path: "M420 140 V118" },
  { from: "agent", to: "reply", path: "M490 112 H511" },
  { from: "gate", to: "working", path: "M255 270 V143", label: ["assembled per turn", 261, 165] },
  { from: "semantic", to: "gate", path: "M95 400 V370 H245 V326", label: ["search facts", 101, 390] },
  { from: "procedural", to: "gate", path: "M255 400 V332", label: ["match skills", 261, 392] },
  { from: "episodic", to: "gate", path: "M415 400 V370 H265 V326", label: ["last 20 messages", 421, 390] },
  { from: "reply", to: "episodic", path: "M562 139 V427 H494", label: ["save turn", 568, 300] },
];

// The architecture diagram: one connected system. Boxes the turn has passed
// through are lit, and the box the agent is working in right now glows.
export default function Architecture({ events }: { events: AgentEvent[] }) {
  const active = activeStage(events);
  const visited = new Set(events.flatMap(stagesOf));
  const count = (type: AgentEvent["type"]) => events.filter((e) => e.type === type).length;
  const recall = events.find((e) => e.type === "memory_recall");
  const saved = events.filter((e) => e.type === "tool_result" && e.name === "remember" && !e.is_error).length;

  const DETAIL: Record<Stage, string> = {
    gateway: "web page · terminal",
    working: recall ? `${recall.history} msgs · ${recall.facts.length} facts` : "prompt + context",
    agent: `reasons · ${count("llm_call")} call(s)`,
    tools: `acts · ${count("tool_call")} call(s)`,
    reply: "back to you",
    gate: recall ? recall.gate : "retrieve or skip",
    semantic: `facts · ${recall?.facts.length ?? 0} found · ${saved} saved`,
    procedural: `SKILL.md · ${recall?.skills.length ?? 0} loaded`,
    episodic: recall ? `history · ${recall.history} loaded` : "history",
  };
  const TITLE: Record<Stage, string> = {
    gateway: "Gateway", working: "Working memory", agent: "LLM agent", tools: "Tools",
    reply: "Reply", gate: "Retrieval gate", semantic: "Semantic", procedural: "Procedural",
    episodic: "Episodic",
  };

  const state = (stage: Stage) => `${visited.has(stage) ? "visited" : ""} ${active === stage ? "active" : ""}`;

  return (
    <svg className="arch" viewBox="0 0 780 490">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0 0 L10 5 L0 10 z" />
        </marker>
      </defs>

      <Group x={10} y={10} w={620} h={210} label="Harness: one turn, from your message to the reply" />
      <Group x={340} y={35} w={150} h={175} label="Loop: up to 10 steps" solid />
      <Group x={10} y={240} w={620} h={240} label="Memory: one SQLite file on your machine" />
      <Group x={640} y={10} w={130} h={210} label="LLM Ops: coming soon" />

      {LINKS.map(({ from, to, path, label }) => {
        const lit = visited.has(from) && visited.has(to);
        const flowing = active === to && visited.has(from);
        return (
          <g key={path} className={`link ${lit ? "lit" : ""} ${flowing ? "flowing" : ""}`}>
            <path d={path} markerEnd="url(#arrow)" />
            {label && <text x={label[1]} y={label[2]}>{label[0]}</text>}
          </g>
        );
      })}
      <path className="link planned" d="M610 112 H630 V82 H646" markerEnd="url(#arrow)" />

      {(Object.keys(BOX) as Stage[]).map((stage) => {
        const [x, y, w] = BOX[stage];
        return (
          <g key={stage} className={`node ${state(stage)}`}>
            {stage === "gate" ? (
              <polygon points={`${x + w / 2},${y} ${x + w},${y + 30} ${x + w / 2},${y + 60} ${x},${y + 30}`} />
            ) : (
              <rect x={x} y={y} width={w} height={H} rx={8} />
            )}
            <text x={x + w / 2} y={y + (stage === "gate" ? 28 : 23)} className="title">{TITLE[stage]}</text>
            <text x={x + w / 2} y={y + (stage === "gate" ? 43 : 40)}>{DETAIL[stage]}</text>
          </g>
        );
      })}

      {["Trace", "Evals"].map((name, i) => (
        <g key={name} className="node planned">
          <rect x={650} y={55 + i * 80} width={110} height={H} rx={8} />
          <text x={705} y={87 + i * 80} className="title">{name}</text>
        </g>
      ))}
    </svg>
  );
}

function Group(props: { x: number; y: number; w: number; h: number; label: string; solid?: boolean }) {
  return (
    <g className={`group ${props.solid ? "solid" : ""}`}>
      <rect x={props.x} y={props.y} width={props.w} height={props.h} rx={10} />
      <text x={props.x + 12} y={props.y + 18}>{props.label.toUpperCase()}</text>
    </g>
  );
}
