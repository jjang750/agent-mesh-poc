# Agent Mesh PoC 진입점 — JWT 발급, intra 카드 등록 후 디스커버리+핸드오프 실행
import asyncio
import sys

from agent_mesh_poc.common import registry
from agent_mesh_poc.common.jwt_utils import issue_token
from agent_mesh_poc.orchestrator import hr_agent
from agent_mesh_poc.orchestrator.graph import build_mesh_graph


async def run(prompt: str):
    # intra 에이전트는 오케스트레이터 프로세스가 자기등록한다.
    registry.register(hr_agent.CARD)

    token = issue_token(subject="user-001", roles=["employee"])
    graph = build_mesh_graph()
    state = {
        "prompt": prompt,
        "jwt": token,
        "context": {},
        "chunks": [],
        "hops": [],
    }
    final = await graph.ainvoke(state)

    print(f"질의: {prompt}")
    print(f"디스커버리된 에이전트: {[c['name'] for c in final['catalog']]}")
    print(f"핸드오프 경로(hops): {' → '.join(final['hops'])}")
    if final.get("handoff_reason"):
        print(f"핸드오프 사유: {final['handoff_reason']}")
    print(f"응답: {final['answer']}")


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "휴가 규정 알려줘"
    asyncio.run(run(prompt))
