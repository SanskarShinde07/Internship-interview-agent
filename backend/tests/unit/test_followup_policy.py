from app.adaptive.followup_policy import is_followup_eligible, is_near_duplicate_question
from app.db.models import QuestionRound


def test_project_discussion_always_eligible_within_cap() -> None:
    decision = is_followup_eligible(
        round_=QuestionRound.PROJECT_DISCUSSION,
        composite_score=10,  # score irrelevant for project round
        mentioned_concepts=[],
        followups_used_for_topic=0,
        max_followups_per_topic=3,
    )
    assert decision.eligible is True


def test_project_discussion_blocked_once_cap_reached() -> None:
    decision = is_followup_eligible(
        round_=QuestionRound.PROJECT_DISCUSSION,
        composite_score=100,
        mentioned_concepts=[],
        followups_used_for_topic=3,
        max_followups_per_topic=3,
    )
    assert decision.eligible is False


def test_technical_round_requires_strong_score_and_new_concept() -> None:
    decision = is_followup_eligible(
        round_=QuestionRound.MACHINE_LEARNING,
        composite_score=70,
        mentioned_concepts=["random_forest"],
        followups_used_for_topic=0,
        max_followups_per_topic=2,
    )
    assert decision.eligible is True
    assert decision.concept == "random_forest"


def test_technical_round_ineligible_on_weak_answer() -> None:
    decision = is_followup_eligible(
        round_=QuestionRound.MACHINE_LEARNING,
        composite_score=30,
        mentioned_concepts=["random_forest"],
        followups_used_for_topic=0,
        max_followups_per_topic=2,
    )
    assert decision.eligible is False


def test_technical_round_ineligible_without_mentioned_concepts() -> None:
    decision = is_followup_eligible(
        round_=QuestionRound.MACHINE_LEARNING,
        composite_score=90,
        mentioned_concepts=[],
        followups_used_for_topic=0,
        max_followups_per_topic=2,
    )
    assert decision.eligible is False


def test_zero_max_followups_disables_round_entirely() -> None:
    decision = is_followup_eligible(
        round_=QuestionRound.HR,
        composite_score=100,
        mentioned_concepts=["anything"],
        followups_used_for_topic=0,
        max_followups_per_topic=0,
    )
    assert decision.eligible is False


def test_near_duplicate_detected() -> None:
    assert is_near_duplicate_question(
        "Can you tell me more about random forest?",
        ["can you tell me more about RANDOM FOREST"],
    )


def test_distinct_questions_not_duplicate() -> None:
    assert not is_near_duplicate_question(
        "Can you tell me more about random forest?",
        ["What is the time complexity of quicksort?"],
    )
