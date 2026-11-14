import type { AgentEvent } from "./events";

const REASONS = {
  no_tool_calls: "the model answered without asking for a tool",
  max_iterations: "it hit the step limit, so tools were switched off for a final answer",
};

// One row in the timeline. `start` is when the turn began, to show "+0.81s".
export default function Step({ event, start }: { event: AgentEvent; start: number }) {
  const offset = `+${(event.at - start).toFixed(2)}s`;

  switch (event.type) {
    case "turn_start":
      return <Row offset={offset} title="Message received" />;
    case "memory_recall":
      return (
        <Row
          offset={offset}
          kind="memory"
          title="Working memory assembled"
          meta={`${event.history} past messages · retrieval gate: ${event.gate === "skip" ? "skipped, nothing worth searching for" : `searched facts, ${event.facts.length} found`}`}
          body={event.facts.map((fact) => `- ${fact}`).join("\n")}
        />
      );
    case "llm_call":
      return (
        <Row
          offset={offset}
          title={`Model call #${event.iteration}`}
          meta={`stop: ${event.stop_reason} · ${event.usage.input} in / ${event.usage.output} out tokens · ${event.duration_ms} ms`}
          body={event.text}
        />
      );
    case "tool_call":
      return (
        <Row offset={offset} kind="tool" title={`Tool call: ${event.name}`} body={JSON.stringify(event.input, null, 2)} />
      );
    case "tool_result":
      return (
        <Row
          offset={offset}
          kind={event.is_error ? "error" : "tool"}
          title={`Tool result: ${event.name}`}
          meta={`${event.duration_ms} ms`}
          body={event.output}
        />
      );
    case "turn_end":
      return (
        <Row
          offset={offset}
          title="Finished"
          meta={`after ${event.iterations} model call(s): ${REASONS[event.reason]}`}
        />
      );
    case "memory_save":
      return <Row offset={offset} kind="memory" title="Saved to history" meta="your message and the reply" />;
    case "error":
      return <Row offset={offset} kind="error" title="Error" body={event.message} />;
  }
}

function Row(props: { offset: string; title: string; meta?: string; body?: string; kind?: "tool" | "memory" | "error" }) {
  return (
    <li className={`step ${props.kind ?? ""}`}>
      <div className="step-head">
        <strong>{props.title}</strong>
        <span className="muted">{props.offset}</span>
      </div>
      {props.meta && <div className="muted">{props.meta}</div>}
      {props.body && <pre>{props.body}</pre>}
    </li>
  );
}
