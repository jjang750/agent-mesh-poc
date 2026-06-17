# Orchestrator(Coordinator) 그래프 — intra/inter 도메인 라우팅 메인 mesh 그래프
from langgraph.graph import END, START, StateGraph

from agent_mesh_poc.common.state import MeshState
from agent_mesh_poc.orchestrator.grpc_client import call_remote
from agent_mesh_poc.orchestrator.hr_agent import build_hr_subgraph

# 이 키워드가 있으면 타 도메인(Finance)으로 위임한다.
_INTER_KEYWORDS = ("finance", "재무", "예산", "비용", "급여", "회계")


def _route(state: MeshState) -> dict:
    route = "inter" if any(k in state["prompt"] for k in _INTER_KEYWORDS) else "intra"
    return {"route": route}


def _branch(state: MeshState) -> str:
    return state["route"]


def build_mesh_graph():
    g = StateGraph(MeshState)
    g.add_node("router", _route)
    g.add_node("hr_agent", build_hr_subgraph())   # Intra-domain: 인메모리 subgraph
    g.add_node("finance_remote", call_remote)     # Inter-domain: gRPC 스트리밍
    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router", _branch, {"intra": "hr_agent", "inter": "finance_remote"}
    )
    g.add_edge("hr_agent", END)
    g.add_edge("finance_remote", END)
    return g.compile()
