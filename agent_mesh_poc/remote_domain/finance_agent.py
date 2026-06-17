# Inter-domain Finance_Agent — 원격 프로세스에서 동작하는 재무 도메인 에이전트(stub)
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class FinanceState(TypedDict):
    prompt: str
    context: dict
    answer: str


def _respond(state: FinanceState) -> dict:
    q = state["prompt"]
    return {
        "answer": (
            f"[Finance_Agent] 재무 도메인 분석 결과: '{q}' 에 대한 예산/비용 검토 응답입니다."
        )
    }


def build_finance_graph():
    g = StateGraph(FinanceState)
    g.add_node("finance_respond", _respond)
    g.add_edge(START, "finance_respond")
    g.add_edge("finance_respond", END)
    return g.compile()
