"use client";

import { useState } from "react";
import { answerApproval, type AgentEvent } from "./events";

const REASONS = {
  no_tool_calls: "the model answered without asking for a tool",
  max_iterations: "it hit the step limit, so tools were switched off for a final answer",
};

// One row in the timeline. `start` is when the turn began, to show "+0.81s".
// `answered` says whether an approval request already has its answer.
export default function Step({ event, start, answered }: { event: AgentEvent; start: number; answered: boolean }) {
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
          body={[...event.facts.map((fact) => `- ${fact}`), `skills on offer: ${event.skills.join(", ") || "none"}`].join("\n")}
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
    case "approval_request":
      return (
        <Row
          offset={offset}
          kind="approval"
          title={`Approval needed: ${event.name}`}
          meta="This changes something outside the agent, so it waits for you."
          body={JSON.stringify(event.input, null, 2)}
        >
          {!answered && <ApprovalButtons id={event.id} />}
        </Row>
      );
    case "approval_result":
      return (
        <Row
          offset={offset}
          kind={event.approved ? "approval" : "error"}
          title={event.approved ? `Approved: ${event.name}` : `Declined: ${event.name}`}
          meta={event.approved ? "the tool runs now" : "the tool does not run, and the model is told"}
        />
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
    case "consolidation_start":
      return (
        <Row offset={offset} kind="memory" title="Consolidating memory"
          meta={`reading ${event.messages} message(s) not consolidated yet, for lasting facts`} />
      );
    case "consolidation_end":
      return (
        <Row
          offset={offset}
          kind="memory"
          title={`Consolidated: ${event.facts.length} new fact(s)`}
          meta={event.messages
            ? `from ${event.messages} message(s) · ${event.usage.input} in / ${event.usage.output} out tokens · ${event.duration_ms} ms`
            : "nothing new since last time"}
          body={event.facts.map((fact) => `+ ${fact}`).join("\n") || undefined}
        />
      );
    case "error":
      return <Row offset={offset} kind="error" title="Error" body={event.message} />;
    case "eval_result":
      return (
        <Row
          offset={offset}
          kind={event.passed ? "tool" : "error"}
          title={`${event.passed ? "✓" : "✗"} ${event.message}`}
          meta={`tools: ${event.tools.join(", ") || "none"} · ${event.tokens} tokens`}
          body={event.problems.join("\n") || undefined}
        />
      );
    case "evals_end":
      return (
        <Row
          offset={offset}
          title={`Evals: ${event.passed}/${event.total} passed`}
          meta={`${event.tokens} tokens · ${(event.duration_ms / 1000).toFixed(1)}s`}
        />
      );
  }
}

// Approve or Deny: POSTs your answer, and the turn carries on.
function ApprovalButtons({ id }: { id: string }) {
  const [sending, setSending] = useState(false);
  const [problem, setProblem] = useState("");

  async function answer(approved: boolean) {
    setSending(true);
    try {
      await answerApproval(id, approved);
    } catch (err) {
      setProblem(`Could not send your answer: ${err}`);
      setSending(false);
    }
  }

  return (
    <div className="approval-buttons">
      <button disabled={sending} onClick={() => answer(true)}>Approve</button>
      <button disabled={sending} className="deny" onClick={() => answer(false)}>Deny</button>
      {problem && <span className="muted">{problem}</span>}
    </div>
  );
}

function Row(props: {
  offset: string;
  title: string;
  meta?: string;
  body?: string;
  kind?: "tool" | "memory" | "error" | "approval";
  children?: React.ReactNode;
}) {
  return (
    <li className={`step ${props.kind ?? ""}`}>
      <div className="step-head">
        <strong>{props.title}</strong>
        <span className="muted">{props.offset}</span>
      </div>
      {props.meta && <div className="muted">{props.meta}</div>}
      {props.body && <pre>{props.body}</pre>}
      {props.children}
    </li>
  );
}
