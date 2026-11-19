import pytest

from inconnu import redact


@pytest.mark.parametrize("name", ["张伟", "Мария Иванова", "अनन्या शर्मा", "มาเรีย สมิธ"])
def test_non_latin_mentions_use_original_codepoint_offsets(name):
    text = f"Assigned to {name}, please review."
    output, findings = redact(text)
    assert output == "Assigned to [PERSON], please review."
    start = text.index(name)
    assert [(f["start"], f["end"]) for f in findings] == [(start, start + len(name))]


def test_mark_heavy_explicit_name_and_ambiguous_values():
    name = "ณัฐธิดา ศรีสวัสดิ์"
    assert redact(name, key="users.full_name")[0] == "[PERSON]"
    assert redact(name, key="organizations.name") == (name, [])
    assert redact(name) == (name, [])


def test_fullwidth_name_delimiter_stays_in_output():
    assert redact("Contact: 张伟。")[0] == "Contact: [PERSON]。"


@pytest.mark.parametrize(
    "text",
    [
        "Assigned to Security Team yesterday.",
        "Reviewed by Build System today.",
        "Hi @platform-team, your scan finished.",
        "Assigned to the delivery guild yesterday.",
        "Reviewed by SRE Group.",
        "Contact: SRE.",
        "Reviewed by Observability Squads.",
        "Contact: platform-team.",
        "Assigned to sec/infra.",
        "Contact: 安全团队。",
        "Reviewed by सुरक्षा टीम.",
        "Assigned to Служба Поддержки.",
        "Assigned to Команда платформы.",
        "Contact: فريق المراجعة.",
        "Assigned to Equipo de seguridad.",
        "Assigned to Team Alpha.",
        "Reviewed by Squad Seven.",
    ],
)
def test_team_mentions_stay_visible(text):
    assert redact(text) == (text, [])


@pytest.mark.parametrize(
    "name",
    [
        "Maya Group",
        "Jordan Crew",
        "Nora Team",
        "Juan Williams",
        "ALICE CREW",
        "JON Crew",
        "Morgan-Crew",
        "nora-team",
        "Алина Группа",
        "Ольга Команда",
        "Dr. Maya Crew",
    ],
)
def test_team_word_in_person_name_is_redacted(name):
    text = f"Reviewed by {name}, please review."
    result, findings = redact(text)
    assert result == "Reviewed by [PERSON], please review."
    assert [(f["start"], f["end"]) for f in findings] == [(12, 12 + len(name))]


def test_two_cues_in_one_clause_see_each_subject():
    assert redact("Assigned to Security Team and reviewed by Maya Group.")[0] == (
        "Assigned to Security Team and reviewed by [PERSON]."
    )


def test_numeric_contact_value_is_not_a_person_mention():
    assert redact("owner: 3611218499") == ("owner: 3611218499", [])


@pytest.mark.parametrize("cue", ["hi ", "hi\x1c", "HI\t", "Hı\u00a0"])
def test_cue_whitespace_and_case_keep_person_spans(cue):
    assert redact(f"{cue}maya group, please review.")[0] == (
        f"{cue}[PERSON], please review."
    )


@pytest.mark.parametrize("key", ["team_name", "groups.name", "squadDisplayName"])
def test_team_column_allows_ambiguous_label_without_affecting_secrets(key):
    assert redact("Morgan Stanley", key=key) == ("Morgan Stanley", [])
    assert redact("sk_live_demo", key=key)[0] == "[SECRET:stripe-key]"


@pytest.mark.parametrize(
    "key", ["teams.members.name", "teams.owner.name", "groups.users.display_name"]
)
def test_person_nested_under_team_column_is_redacted(key):
    assert redact("John Smith", key=key)[0] == "[PERSON]"


@pytest.mark.parametrize(
    "text",
    [
        "Thanks for your help.",
        "Hi there, how are you?",
        "Hi There, how are you?",
        "Contact: please review.",
        "Hi all, quick update.",
        "Thanks so much!",
        "Dear customer, your order shipped.",
        "Assigned to nobody yet.",
        "Done by the script.",
    ],
)
def test_ordinary_prose_after_a_cue_stays_visible(text):
    assert redact(text) == (text, [])


def test_untrusted_prefixless_payment_intent_has_no_new_exemption():
    value = "X9kZN0fW6VoYqD1rThI3N5LUj4Ps2mGz"
    assert redact(value)[0] == "[SECRET:entropy]"
    assert redact(value, key="payment_intent")[0] == "[SECRET:entropy]"
