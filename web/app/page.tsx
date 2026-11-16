"use client";

import { useEffect, useRef, useState } from "react";
import Architecture from "./architecture";
import { listPastTurns, replayTurn, streamChat, streamConsolidate, type AgentEvent, type PastTurn } from "./events";
import Step from "./step";

type Turn = { message: string; events: AgentEvent[] };

export default function Home() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [pastTurns, setPastTurns] = useState<PastTurn[]>([]);
  const latest = turns.at(-1)?.events ?? [];
  const bottom = useRef<HTMLDivElement>(null);

  // Keep the newest step in view as the chat grows.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  // Load the saved turns once when the page opens (nothing to show if the API is down).
  useEffect(() => {
    listPastTurns().then(setPastTurns).catch(() => {});
  }, []);

  // Append an event to the newest turn, so the page updates as steps arrive.
  function addEvent(event: AgentEvent) {
    setTurns((all) =>
      all.map((turn, i) => (i === all.length - 1 ? { ...turn, events: [...turn.events, event] } : turn)),
    );
  }

  function send(e: React.FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || running) return;
    setInput("");
    run(message, (onEvent) => streamChat(message, onEvent));
  }

  // Start a new entry in the chat and stream the agent's events into it.
  async function run(title: string, stream: (onEvent: (event: AgentEvent) => void) => Promise<void>) {
    setRunning(true);
    setTurns((all) => [...all, { message: title, events: [] }]);
    try {
      await stream(addEvent);
    } catch (err) {
      addEvent({ type: "error", message: `Could not reach the agent: ${err}`, at: Date.now() / 1000 });
    } finally {
      setRunning(false);
      listPastTurns().then(setPastTurns).catch(() => {}); // the turn just finished is saved now
    }
  }

  return (
    <div className="app">
      <main className="overview">
        <h1>Tomu</h1>
        <p className="muted">A local agent that shows every step it takes. Watch the boxes light up.</p>
        <Stats events={latest} />
        <h2>Architecture</h2>
        <Architecture events={latest} />
        <h2>Past turns</h2>
        {pastTurns.length === 0 && <p className="muted">Nothing saved yet. Ask Tomu something first.</p>}
        <ul className="past-turns">
          {pastTurns.map((turn) => (
            <li key={turn.id}>
              <span className="muted">{new Date(turn.saved_at * 1000).toLocaleString()}</span>
              <span className="past-message">{turn.message}</span>
              <button
                className="secondary"
                disabled={running}
                onClick={() => run(`Replay: ${turn.message}`, (onEvent) => replayTurn(turn.id, onEvent))}
              >
                Replay
              </button>
            </li>
          ))}
        </ul>
      </main>

      <aside className="chat">
        <h2>Chat</h2>
        <div className="messages">
          {turns.map((turn, i) => {
            const end = turn.events.find((e) => e.type === "turn_end");
            return (
              <section key={i} className="turn">
                <div className="bubble user">{turn.message}</div>
                <ol className="timeline">
                  {turn.events.map((event, j) => (
                    <Step key={j} event={event} start={turn.events[0].at} answered={isAnswered(turn.events, event)} />
                  ))}
                </ol>
                {end && <div className="bubble agent">{end.reply}</div>}
              </section>
            );
          })}
          {running && <p className="muted">thinking...</p>}
          <div ref={bottom} />
        </div>
        <form onSubmit={send}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="What time is it in Tokyo?"
            disabled={running}
            autoFocus
          />
          <button disabled={running || !input.trim()}>Send</button>
          <button
            type="button"
            className="secondary"
            onClick={() => run("Consolidate memory", streamConsolidate)}
            disabled={running}
            title="Turn messages not consolidated yet into lasting facts"
          >
            Consolidate
          </button>
        </form>
      </aside>
    </div>
  );
}

// Whether an approval request already has its approval_result.
function isAnswered(events: AgentEvent[], event: AgentEvent) {
  return event.type === "approval_request" && events.some((e) => e.type === "approval_result" && e.id === event.id);
}

// Totals for the latest turn.
function Stats({ events }: { events: AgentEvent[] }) {
  let modelCalls = 0, toolCalls = 0, tokens = 0;
  for (const e of events) {
    if (e.type === "llm_call") {
      modelCalls += 1;
      tokens += e.usage.input + e.usage.output;
    }
    if (e.type === "tool_call") toolCalls += 1;
  }
  const seconds = events.length > 1 ? (events.at(-1)!.at - events[0].at).toFixed(1) : "0.0";

  return (
    <div className="stats">
      <Stat value={`${seconds}s`} label="turn time" />
      <Stat value={modelCalls} label="model calls" />
      <Stat value={toolCalls} label="tool calls" />
      <Stat value={tokens} label="tokens" />
    </div>
  );
}

function Stat({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="stat">
      <strong>{value}</strong>
      <span className="muted">{label}</span>
    </div>
  );
}
