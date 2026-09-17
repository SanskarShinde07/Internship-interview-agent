from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import BankRound, Base, QuestionBankItem
from app.question_bank.loader import SEED_FILES, _load_seed_file, seed_question_bank


def _fresh_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_seed_loads_all_items_and_is_idempotent() -> None:
    db = _fresh_session()
    results = seed_question_bank(db)
    total_from_files = sum(len(_load_seed_file(f)) for f in SEED_FILES)
    assert sum(results.values()) == total_from_files

    stored = db.execute(select(QuestionBankItem)).scalars().all()
    assert len(stored) == total_from_files

    second_pass = seed_question_bank(db)
    assert sum(second_pass.values()) == 0


def test_each_round_has_active_questions_at_multiple_difficulties() -> None:
    db = _fresh_session()
    seed_question_bank(db)

    for bank_round in BankRound:
        items = (
            db.execute(select(QuestionBankItem).where(QuestionBankItem.round == bank_round))
            .scalars()
            .all()
        )
        assert items, f"no questions seeded for round {bank_round}"
        assert all(item.is_active for item in items)
        difficulties = {item.difficulty for item in items}
        assert len(difficulties) >= 2, f"round {bank_round} lacks difficulty variety"
