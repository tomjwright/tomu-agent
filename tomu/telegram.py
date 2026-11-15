"""Telegram gateway: chat with Tomu from your phone. Run `uv run tomu-telegram`.

It asks Telegram for new messages in a loop ("long polling"), so it needs no
public address. It talks to Telegram's Bot API over plain HTTPS with Python's
built-in urllib, so there is nothing extra to install.

Set in .env:
    TELEGRAM_BOT_TOKEN     from @BotFather (/newbot); it controls the bot
    TELEGRAM_ALLOWED_USER  your numeric Telegram user id. The agent can read your
                           email, so it only answers you. Message the bot once and
                           your id is printed in the terminal.
"""

import json
import os
import queue
import threading
import time
import urllib.error
import urllib.request

from dotenv import load_dotenv

from tomu.agent import run_agent

APPROVAL_TIMEOUT = 300  # seconds to wait for a button press before counting it as no
POLL_SECONDS = 30  # how long each getUpdates call waits for a new message
MAX_TEXT = 4000  # Telegram rejects messages over 4096 characters


def call(method: str, **params):
    """One Bot API call, e.g. call("sendMessage", chat_id=1, text="hi")."""
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}",
        data=json.dumps(params).encode(),
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=POLL_SECONDS + 10) as response:
        return json.load(response)["result"]


def summary(events: list[dict], seconds: float) -> str:
    """One line under each reply: "steps: search_email -> read_email · 2 model calls · 3.1s"."""
    tools = " -> ".join(e["name"] for e in events if e["type"] == "tool_call") or "no tools"
    calls = sum(e["type"] == "llm_call" for e in events)
    return f"steps: {tools} · {calls} model call{'' if calls == 1 else 's'} · {seconds:.1f}s"


class Bot:
    def __init__(self, allowed_user: int, send=call):
        self.allowed_user = allowed_user
        self.send = send
        self.waiting: dict[str, queue.Queue] = {}  # call id -> where your button press goes

    def handle(self, update: dict) -> None:
        """One update from Telegram: a message to answer, or a button you pressed."""
        if press := update.get("callback_query"):
            self.answer_button(press)
        elif (message := update.get("message")) and "text" in message:
            if message["from"]["id"] != self.allowed_user:
                print(f"Ignored a message from Telegram user {message['from']['id']}. "
                      "If that's you, set TELEGRAM_ALLOWED_USER to it.")
                return
            # a thread per turn, so button presses still arrive while a turn waits for one
            turn = threading.Thread(target=self.run_turn,
                                    args=(message["chat"]["id"], message["text"]), daemon=True)
            turn.start()

    def run_turn(self, chat_id: int, text: str) -> None:
        self.send("sendChatAction", chat_id=chat_id, action="typing")
        started, events = time.perf_counter(), []
        reply = run_agent(text, events.append,
                          approve=lambda id, name, input: self.ask(chat_id, id, name, input))
        errors = [e["message"] for e in events if e["type"] == "error"]
        reply = reply or f"Error: {errors[0] if errors else 'no reply'}"
        footer = summary(events, time.perf_counter() - started)
        self.send("sendMessage", chat_id=chat_id, text=f"{reply[:MAX_TEXT]}\n\n{footer}")

    def ask(self, chat_id: int, id: str, name: str, input: dict) -> bool:
        """Send the exact action with Approve and Deny buttons, and wait for a press."""
        self.waiting[id] = queue.Queue(maxsize=1)  # ready before the buttons can be pressed
        buttons = [[{"text": "Approve", "callback_data": f"{id}:yes"},
                    {"text": "Deny", "callback_data": f"{id}:no"}]]
        self.send("sendMessage", chat_id=chat_id,
                  text=f"Allow {name}?\n{json.dumps(input, indent=2)}"[:MAX_TEXT],
                  reply_markup={"inline_keyboard": buttons})
        try:
            return self.waiting[id].get(timeout=APPROVAL_TIMEOUT)
        except queue.Empty:
            return False
        finally:
            self.waiting.pop(id, None)

    def answer_button(self, press: dict) -> None:
        id, _, answer = press["data"].rpartition(":")
        box = self.waiting.get(id)
        if press["from"]["id"] != self.allowed_user or box is None:
            note = "Nothing is waiting for that."
        else:
            try:
                box.put_nowait(answer == "yes")
                note = "Approved" if answer == "yes" else "Declined"
                # replace the buttons with the answer, so they can't be pressed twice
                self.send("editMessageText", chat_id=press["message"]["chat"]["id"],
                          message_id=press["message"]["message_id"],
                          text=f"{press['message']['text']}\n\n{note}.")
            except queue.Full:
                note = "That was already answered."
        self.send("answerCallbackQuery", callback_query_id=press["id"], text=note)


def main() -> None:
    load_dotenv()
    bot = Bot(int(os.getenv("TELEGRAM_ALLOWED_USER") or 0))
    if bot.allowed_user:
        print(f"Tomu is on Telegram. Only user {bot.allowed_user} can talk to it. Ctrl-C to stop.")
    else:
        print("TELEGRAM_ALLOWED_USER isn't set, so the bot answers nobody yet. "
              "Message it, and your id is printed here.")
    offset = 0  # tells Telegram which updates we've already handled
    while True:
        try:
            updates = call("getUpdates", offset=offset, timeout=POLL_SECONDS,
                           allowed_updates=["message", "callback_query"])
        except urllib.error.HTTPError as error:
            raise SystemExit(f"Telegram refused the request ({error}). "
                             "Check TELEGRAM_BOT_TOKEN.") from None
        except OSError as error:  # offline or a timeout: try again shortly
            print(f"Couldn't reach Telegram ({error}). Retrying in 5s.")
            time.sleep(5)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            bot.handle(update)


if __name__ == "__main__":
    main()
