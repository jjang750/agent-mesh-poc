# Intra-domain HR_Agent — 인메모리 subgraph로 동작하는 인사 도메인 에이전트
from langgraph.graph import END, START, StateGraph

from agent_mesh_poc.common.state import MeshState


def _respond(state: MeshState) -> dict:
    # 동일 프로세스 내 Python 객체 참조로 state를 주고받는다(네트워크 I/O 없음).
    q = state["prompt"]
    answer = f"[HR_Agent] 인사 도메인 처리 결과: '{q}' 에 대한 사내 규정 안내입니다."
    return {"chunks": [answer], "answer": answer}


def build_hr_subgraph():
    """부모 MeshState를 그대로 공유하는 subgraph. 메인 그래프의 노드로 삽입된다."""
    g = StateGraph(MeshState)
    g.add_node("hr_respond", _respond)
    g.add_edge(START, "hr_respond")
    g.add_edge("hr_respond", END)
    return g.compile()
