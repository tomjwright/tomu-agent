from tomu.skills import Skill, load_skills, parse_skill, use_skill_tool

MEETINGS = Skill("meeting-planner", "Schedule a meeting.", "Ask where everyone is.")


def test_parse_skill_reads_the_header_and_instructions():
    skill = parse_skill("---\nname: greet\ndescription: Say hello: politely\n---\nWave.\n")

    assert skill == Skill("greet", "Say hello: politely", "Wave.")


def test_the_bundled_skills_all_load():
    names = [skill.name for skill in load_skills()]

    assert "meeting-planner" in names


def test_use_skill_returns_the_instructions_of_the_named_skill():
    tool = use_skill_tool([MEETINGS])

    assert tool.run(name="meeting-planner") == "Ask where everyone is."
