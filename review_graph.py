"""Recommend a curriculum expression and wait for the learner's decision."""
from collections import Counter
from threading import Lock
from time import monotonic
from typing import TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ReviewState(TypedDict, total=False):
    attempts: list[dict]
    plan: dict | None
    approved: bool


def recommend(state):
    attempts = Counter()
    misses = Counter()
    for attempt in state["attempts"]:
        expression_id = attempt["expression_id"]
        attempts[expression_id] += 1
        if attempt["outcome"] in ("incorrect", "partial"):
            misses[expression_id] += 1
    if not misses:
        return {"plan": None}
    # Input is newest first. Ties favor the expression with the most recent miss.
    expression_id = max(misses, key=lambda key: (misses[key], misses[key] / attempts[key]))
    return {"plan": {
        "expression_id": expression_id,
        "attempts": attempts[expression_id],
        "misses": misses[expression_id],
        "size": 3,
    }}


def wait_for_decision(state):
    return {"approved": interrupt(state["plan"]) is True}


_checkpoints = InMemorySaver()
_graph = (
    StateGraph(ReviewState)
    .add_node("recommend", recommend)
    .add_node("wait_for_decision", wait_for_decision)
    .add_edge(START, "recommend")
    .add_conditional_edges("recommend", lambda state: "preview" if state["plan"] else "empty",
                           {"preview": "wait_for_decision", "empty": END})
    .add_edge("wait_for_decision", END)
    .compile(checkpointer=_checkpoints)
)
_pending = {}
_lock = Lock()
_TTL = 15 * 60
_MAX_PENDING = 1000


def _drop(thread_id):
    _pending.pop(thread_id, None)
    _checkpoints.delete_thread(thread_id)


def propose(user_id, attempts):
    thread_id = uuid4().hex
    with _lock:
        now = monotonic()
        for key, (_, expiry) in list(_pending.items()):
            if expiry <= now:
                _drop(key)
        config = {"configurable": {"thread_id": thread_id}}
        result = _graph.invoke({"attempts": attempts}, config)
        if not result.get("__interrupt__"):
            _drop(thread_id)
            return None
        if len(_pending) >= _MAX_PENDING:
            _drop(next(iter(_pending)))
        _pending[thread_id] = (user_id, now + _TTL)
        return {"thread_id": thread_id, **result["__interrupt__"][0].value}


def decide(user_id, thread_id, approved):
    with _lock:
        pending = _pending.get(thread_id)
        if not pending or pending[0] != user_id:
            return None
        if pending[1] <= monotonic():
            _drop(thread_id)
            return None
        result = _graph.invoke(Command(resume=approved), {"configurable": {"thread_id": thread_id}})
        _drop(thread_id)
        return {"approved": result["approved"], "plan": result["plan"] if result["approved"] else None}
