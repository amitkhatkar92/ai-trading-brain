"""tests/unit/investment/strategy/debate/test_argument_manager.py"""
import pytest
from iios.investment.strategy.debate.debate_constants import (
    ArgumentType, ParticipantRole, RebuttalType,
)
from iios.investment.strategy.debate.argument_manager import (
    Argument, ArgumentManager, Rebuttal,
    make_argument, make_rebuttal,
)


class TestMakeArgument:
    def test_creates_argument(self, session_id):
        arg = make_argument(
            session_id, "agent-1", ParticipantRole.TECHNICAL_ANALYST,
            ArgumentType.SUPPORTING, "Price is bullish", "RSI confirms", 80.0,
        )
        assert arg.argument_type == ArgumentType.SUPPORTING
        assert arg.confidence == 80.0
        assert arg.session_id == session_id

    def test_confidence_clamped(self, session_id):
        arg = make_argument(
            session_id, "a", ParticipantRole.RISK_ANALYST,
            ArgumentType.OPPOSING, "Too risky", "High VaR", 150.0,
        )
        assert arg.confidence == 100.0

    def test_argument_has_unique_id(self, session_id):
        a1 = make_argument(session_id, "a", ParticipantRole.TECHNICAL_ANALYST,
                           ArgumentType.SUPPORTING, "X", "Y", 70.0)
        a2 = make_argument(session_id, "a", ParticipantRole.TECHNICAL_ANALYST,
                           ArgumentType.SUPPORTING, "X", "Y", 70.0)
        assert a1.argument_id != a2.argument_id

    def test_argument_is_frozen(self, session_id):
        arg = make_argument(session_id, "a", ParticipantRole.RISK_ANALYST,
                            ArgumentType.OPPOSING, "X", "Y", 60.0)
        with pytest.raises((AttributeError, TypeError)):
            arg.confidence = 99.0  # type: ignore

    def test_to_dict(self, session_id):
        arg = make_argument(session_id, "a", ParticipantRole.MACRO_ANALYST,
                            ArgumentType.NEUTRAL, "Neutral", "Balanced", 50.0)
        d = arg.to_dict()
        assert d["argument_type"] == "neutral"
        assert "claim" in d


class TestMakeRebuttal:
    def test_creates_rebuttal(self, session_id):
        r = make_rebuttal(
            session_id, "agent-2", ParticipantRole.RISK_ANALYST,
            "target-arg-001", RebuttalType.DIRECT_COUNTER,
            "Counter claim", "Evidence challenges this", 70.0,
        )
        assert r.target_arg_id == "target-arg-001"
        assert r.rebuttal_type == RebuttalType.DIRECT_COUNTER

    def test_to_dict(self, session_id):
        r = make_rebuttal(
            session_id, "a", ParticipantRole.MACRO_ANALYST,
            "t", RebuttalType.EVIDENCE_CHALLENGE, "X", "Y", 55.0,
        )
        d = r.to_dict()
        assert "rebuttal_id" in d
        assert "target_arg_id" in d


class TestArgumentManager:
    def test_add_and_count(self, session_id):
        mgr = ArgumentManager(session_id)
        arg = make_argument(session_id, "a", ParticipantRole.TECHNICAL_ANALYST,
                            ArgumentType.SUPPORTING, "X", "Y", 70.0)
        mgr.add_argument(arg)
        assert mgr.argument_count() == 1

    def test_all_arguments(self, argument_manager):
        assert len(argument_manager.all_arguments()) == 2

    def test_by_type(self, argument_manager):
        sup = argument_manager.arguments_by_type(ArgumentType.SUPPORTING)
        opp = argument_manager.arguments_by_type(ArgumentType.OPPOSING)
        assert len(sup) == 1
        assert len(opp) == 1

    def test_by_participant(self, argument_manager):
        args = argument_manager.arguments_by_participant("agent-1")
        assert len(args) == 1

    def test_by_round(self, session_id):
        mgr = ArgumentManager(session_id)
        a1  = make_argument(session_id, "a", ParticipantRole.TECHNICAL_ANALYST,
                            ArgumentType.SUPPORTING, "X", "Y", 70.0)
        a2  = make_argument(session_id, "b", ParticipantRole.RISK_ANALYST,
                            ArgumentType.OPPOSING, "Z", "W", 60.0)
        mgr.add_argument(a1, round_num=1)
        mgr.add_argument(a2, round_num=2)
        assert len(mgr.arguments_by_round(1)) == 1
        assert len(mgr.arguments_by_round(2)) == 1

    def test_rebuttals(self, argument_manager, session_id):
        args = argument_manager.all_arguments()
        r    = make_rebuttal(session_id, "x", ParticipantRole.MACRO_ANALYST,
                             args[0].argument_id, RebuttalType.DIRECT_COUNTER,
                             "Counter", "Evidence", 60.0)
        argument_manager.add_rebuttal(r)
        found = argument_manager.rebuttals_for(args[0].argument_id)
        assert len(found) == 1

    def test_weighted_support_score_positive(self, session_id):
        mgr = ArgumentManager(session_id)
        for _ in range(3):
            mgr.add_argument(make_argument(
                session_id, "a", ParticipantRole.TECHNICAL_ANALYST,
                ArgumentType.SUPPORTING, "Buy", "RSI", 80.0, weight=1.0,
            ))
        mgr.add_argument(make_argument(
            session_id, "b", ParticipantRole.RISK_ANALYST,
            ArgumentType.OPPOSING, "Risk", "VaR", 60.0, weight=1.0,
        ))
        score = mgr.weighted_support_score()
        assert score > 0

    def test_weighted_support_score_negative(self, session_id):
        mgr = ArgumentManager(session_id)
        for _ in range(3):
            mgr.add_argument(make_argument(
                session_id, "b", ParticipantRole.RISK_ANALYST,
                ArgumentType.OPPOSING, "Risk", "VaR", 80.0, weight=1.0,
            ))
        score = mgr.weighted_support_score()
        assert score < 0

    def test_supporting_and_opposing_helpers(self, argument_manager):
        assert len(argument_manager.supporting_arguments()) == 1
        assert len(argument_manager.opposing_arguments()) == 1
