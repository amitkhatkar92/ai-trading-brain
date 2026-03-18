"""
Communication Layer — Event-Driven Agent Architecture (EDA)
============================================================
Makes 25+ agents collaborate efficiently without becoming a spaghetti
of direct function calls.

Package contents:
  events.py        — All typed event definitions (the shared language)
  event_bus.py     — Publish / subscribe backbone
  message_router.py— Point-to-point agent messaging
  agent_memory.py  — Per-agent short-term + long-term memory
  task_queue.py    — Priority-ordered work queue for agents
"""

from .events         import (Event, EventType, MarketEvent, OpportunityEvent,
                              RiskEvent, DecisionEvent, ExecutionEvent,
                              LearningEvent, SystemEvent)
from .event_bus      import EventBus, get_bus
from .message_router import MessageRouter, get_router
from .agent_memory   import AgentMemory, get_memory, purge_all_expired
from .task_queue     import TaskQueue, Task, Priority, get_task_queue

__all__ = [
    # Events
    "Event", "EventType",
    "MarketEvent", "OpportunityEvent", "RiskEvent",
    "DecisionEvent", "ExecutionEvent", "LearningEvent", "SystemEvent",
    # Event Bus
    "EventBus", "get_bus",
    # Message Router
    "MessageRouter", "get_router",
    # Agent Memory
    "AgentMemory", "get_memory", "purge_all_expired",
    # Task Queue
    "TaskQueue", "Task", "Priority", "get_task_queue",
]
