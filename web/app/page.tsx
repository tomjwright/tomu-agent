"use client";

import { useState } from "react";
import { streamChat, type AgentEvent } from "./events";
import Step from "./step";

type Turn = { message: string; events: AgentEvent[] };

export default function Home() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);

  // Append an event to the newest turn, so the timeline grows as steps arrive.
  function addEvent(event: AgentEvent) {
    setTurns((all) =>
      all.map((turn, i) => (i === all.length - 1 ? { ...turn, events: [...turn.events, event] } : turn)),
    );
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || running) return;
    setInput("");
    setRunning(true);
    setTurns((all) => [...all, { message, events: [] }]);
    try {
      await streamChat(message, addEvent);
    } catch (err) {
      addEvent({ type: "error", message: `Could not reach the agent: ${err}`, at: Date.now() / 1000 });
    } finally {
      setRunning(false);
    }
  }

  return (
    <main>
      <h1>Tomu</h1>
      <p className="muted">Ask something and watch each step the agent takes.</p>

      {turns.map((turn, i) => {
        const end = turn.events.find((e) => e.type === "turn_end");
        return (
          <section key={i} className="turn">
            <div className="bubble user">{turn.message}</div>
            <ol className="timeline">
              {turn.events.map((event, j) => (
                <Step key={j} event={event} start={turn.events[0].at} />
              ))}
            </ol>
            {end && <div className="bubble agent">{end.reply}</div>}
          </section>
        );
      })}

      <form onSubmit={send}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="What time is it in Tokyo?"
          disabled={running}
          autoFocus
        />
        <button disabled={running || !input.trim()}>{running ? "Thinking..." : "Send"}</button>
      </form>
    </main>
  );
}
