from tomu.skills import Skill, load_skills, parse_skill, pick_skills

MEETINGS = Skill("meeting-planner", "Schedule a meeting with people in other cities.", "...")


def test_parse_skill_reads_the_header_and_instructions():
    skill = parse_skill("---\nname: greet\ndescription: Say hello: politely\n---\nWave.\n")

    assert skill == Skill("greet", "Say hello: politely", "Wave.")


def test_the_bundled_skills_all_load():
    names = [skill.name for skill in load_skills()]

    assert "meeting-planner" in names


def test_a_skill_is_picked_when_the_message_shares_a_word_with_its_description():
    assert pick_skills("Can you schedule meetings with Sarah?", [MEETINGS]) == [MEETINGS]
    assert pick_skills("What time is it in Tokyo?", [MEETINGS]) == []
    assert pick_skills("hi, thanks!", [MEETINGS]) == []
