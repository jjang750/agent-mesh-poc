# 에이전트 공통 추상 — respond 함수를 단일 노드 LangGraph로 감싸는 빌더
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph


class AgentState(TypedDict):
    prompt: str
    context: dict
    answer: str
    handoff_to: str        # 채워지면 답변 대신 핸드오프
    handoff_reason: str


def build_agent_graph(respond_fn: Callable[[str, dict], dict]):
    """respond_fn(prompt, context) -> {"answer"} 또는 {"handoff_to","handoff_reason"}."""

    def _run(state: AgentState) -> dict:
        result = respond_fn(state["prompt"], state.get("context", {}))
        return {
            "answer": result.get("answer", ""),
            "handoff_to": result.get("handoff_to", ""),
            "handoff_reason": result.get("handoff_reason", ""),
        }

    g = StateGraph(AgentState)
    g.add_node("run", _run)
    g.add_edge(START, "run")
    g.add_edge("run", END)
    return g.compile()
