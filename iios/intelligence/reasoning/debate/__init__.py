"""iios/intelligence/reasoning/debate/__init__.py"""
from .argument import Argument
from .counter_argument import CounterArgument
from .debate_round import DebateRound
from .debate_session import DebateSession, DebateParticipant
from .debate_summary import DebateSummary
from .debate_engine import DebateEngine, get_debate_engine, reset_debate_engine
from .debate_manager import DebateManager, ArgumentProviderFn, get_debate_manager, reset_debate_manager

__all__ = [
    "Argument", "CounterArgument",
    "DebateRound",
    "DebateSession", "DebateParticipant",
    "DebateSummary",
    "DebateEngine", "get_debate_engine", "reset_debate_engine",
    "DebateManager", "ArgumentProviderFn", "get_debate_manager", "reset_debate_manager",
]
