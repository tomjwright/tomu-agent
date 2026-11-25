"""The Telegram gateway answers only you, and asks with buttons before acting."""

from tomu import telegram

YOU, STRANGER, CHAT = 42, 99, 7


class FakeTelegram:
    """Records every Bot API call. `press` is the button you press when asked."""

    def __init__(self, press=None, presser=YOU):
        self.calls, self.press, self.presser, self.bot = [], press, presser, None

    def __call__(self, method, **params):
        self.calls.append((method, params))
        if self.press and "reply_markup" in params:
            data = params["reply_markup"]["inline_keyboard"][0][0]["callback_data"]
            call_id = data.rpartition(":")[0]
            self.bot.handle(
                {
                    "update_id": 2,
                    "callback_query": {
                        "id": "cb1",
                        "from": {"id": self.presser},
                        "data": f"{call_id}:{self.press}",
                        "message": {"chat": {"id": CHAT}, "message_id": 9, "text": params["text"]},
                    },
                }
            )
        return {}

    def texts(self, method):
        return [params["text"] for name, params in self.calls if name == method]


def bot_with(fake):
    fake.bot = telegram.Bot(YOU, send=fake)
    return fake.bot


def agent_that_sends(answers):
    def fake_run_agent(message, emit, approve):
        emit({"type": "llm_call"})
        emit({"type": "tool_call", "name": "send_email"})
        answers.append(approve("toolu_1", "send_email", {"to": "bob@example.com"}))
        emit({"type": "llm_call"})
        return "Done."

    return fake_run_agent


def test_your_message_gets_the_reply_and_a_line_of_steps(monkeypatch):
    def fake_run_agent(message, emit, approve):
        for event in [
            {"type": "llm_call"},
            {"type": "tool_call", "name": "get_current_time"},
            {"type": "llm_call"},
        ]:
            emit(event)
        return f"You said: {message}"

    monkeypatch.setattr(telegram, "run_agent", fake_run_agent)
    fake = FakeTelegram()

    bot_with(fake).run_turn(CHAT, "what time is it?")

    reply = fake.texts("sendMessage")[0]
    assert reply.startswith("You said: what time is it?\n\nsteps: get_current_time · 2 model calls")


def test_messages_from_anyone_else_are_ignored(capsys):
    fake = FakeTelegram()

    bot_with(fake).handle(
        {
            "update_id": 1,
            "message": {"from": {"id": STRANGER}, "chat": {"id": 1}, "text": "read my email"},
        }
    )

    assert fake.calls == []
    assert "99" in capsys.readouterr().out


def test_approve_button_lets_the_tool_run(monkeypatch):
    answers = []
    monkeypatch.setattr(telegram, "run_agent", agent_that_sends(answers))
    fake = FakeTelegram(press="yes")

    bot = bot_with(fake)
    bot.run_turn(CHAT, "email bob")

    assert answers == [True]
    assert fake.texts("editMessageText")[0].endswith("Approved.")
    assert bot.waiting == {}


def test_deny_button_stops_the_tool(monkeypatch):
    answers = []
    monkeypatch.setattr(telegram, "run_agent", agent_that_sends(answers))
    fake = FakeTelegram(press="no")

    bot_with(fake).run_turn(CHAT, "email bob")

    assert answers == [False]
    assert fake.texts("editMessageText")[0].endswith("Declined.")


def test_no_press_in_time_counts_as_no(monkeypatch):
    answers = []
    monkeypatch.setattr(telegram, "run_agent", agent_that_sends(answers))
    monkeypatch.setattr(telegram, "APPROVAL_TIMEOUT", 0.05)

    bot_with(FakeTelegram()).run_turn(CHAT, "email bob")

    assert answers == [False]


def test_someone_else_pressing_approve_does_not_count(monkeypatch):
    answers = []
    monkeypatch.setattr(telegram, "run_agent", agent_that_sends(answers))
    monkeypatch.setattr(telegram, "APPROVAL_TIMEOUT", 0.05)
    fake = FakeTelegram(press="yes", presser=STRANGER)

    bot_with(fake).run_turn(CHAT, "email bob")

    assert answers == [False]
    assert fake.texts("editMessageText") == []
