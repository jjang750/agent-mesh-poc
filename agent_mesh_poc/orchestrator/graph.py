# Orchestrator — 디스커버리(레지스트리) + 핸드오프 루프 메인 mesh 그래프
from langgraph.graph import END, START, StateGraph

from agent_mesh_poc.common import registry
from agent_mesh_poc.common.selection import select_agent
from agent_mesh_poc.common.state import MeshState
from agent_mesh_poc.orchestrator import hr_agent
from agent_mesh_poc.orchestrator.grpc_client import call_remote
from agent_mesh_poc.orchestrator.handoff import resolve_handoff

# 오케스트레이터 프로세스가 직접 보유한 intra 에이전트(인메모리 그래프).
_LOCAL_AGENTS = {hr_agent.CARD["name"]: hr_agent.build_graph()}


def _discover(state: MeshState) -> dict:
    # 하드코딩 대신 레지스트리에서 등록된 에이전트 카드를 조회한다.
    return {"catalog": registry.discover()}


def _select(state: MeshState) -> dict:
    # 카드 skills 매칭으로 최초 처리 에이전트를 동적으로 고른다.
    return {"target": select_agent(state["prompt"], state["catalog"])}


async def _dispatch(state: MeshState) -> dict:
    name = state["target"]
    card = registry.lookup(name)
    if card is None:
        msg = f"[Orchestrator] 레지스트리에 에이전트 없음: {name}"
        return {"hops": [str(name)], "chunks": [msg], "answer": msg, "handoff_to": ""}

    if card["domain"] == "intra":
        # Intra-domain: 인메모리 그래프 직접 호출(네트워크 없음).
        out = _LOCAL_AGENTS[name].invoke(
            {"prompt": state["prompt"], "context": state.get("context", {})}
        )
        answer = out.get("answer", "")
        result = {
            "answer": answer,
            "chunks": [answer] if answer else [],
            "handoff_to": out.get("handoff_to", ""),
            "handoff_reason": out.get("handoff_reason", ""),
        }
    else:
        # Inter-domain: gRPC 스트리밍.
        result = await call_remote(
            card, state["prompt"], state.get("context", {}), state["jwt"]
        )

    update = {
        "hops": [name],
        "chunks": result["chunks"],
        "answer": result["answer"],
        "handoff_to": result.get("handoff_to", ""),
        "handoff_reason": result.get("handoff_reason", ""),
    }

    # 사이클(이미 방문) / 카드 수 소진을 판정해 루프 종료를 보장한다.
    visited = state["hops"] + [name]
    decision = resolve_handoff(
        visited, result.get("handoff_to", ""), len(state.get("catalog") or [])
    )
    if decision["action"] == "continue":
        update["target"] = decision["target"]  # handoff_to 유지 → 다시 dispatch
    else:
        update["handoff_to"] = ""  # 종료
        if decision["message"]:
            # 핸드오프였으나 진행 불가 → 빈 답변 대신 명시적 실패 메시지로 덮어쓴다.
            update["answer"] = decision["message"]
            update["chunks"] = [decision["message"]]
    return update


def _after_dispatch(state: MeshState) -> str:
    # 종료 판정은 _dispatch가 handoff_to를 비우는 것으로 끝낸다(사이클/소진 포함).
    return "dispatch" if state.get("handoff_to") else END


def build_mesh_graph():
    g = StateGraph(MeshState)
    g.add_node("discover", _discover)
    g.add_node("select", _select)
    g.add_node("dispatch", _dispatch)
    g.add_edge(START, "discover")
    g.add_edge("discover", "select")
    g.add_edge("select", "dispatch")
    g.add_conditional_edges(
        "dispatch", _after_dispatch, {"dispatch": "dispatch", END: END}
    )
    return g.compile()
