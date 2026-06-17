# Agent Mesh PoC 진입점 — JWT 발급 후 오케스트레이터 그래프 실행, 스트림 청크 출력
import asyncio
import sys

from agent_mesh_poc.common.jwt_utils import issue_token
from agent_mesh_poc.orchestrator.graph import build_mesh_graph


async def run(prompt: str):
    token = issue_token(subject="user-001", roles=["employee"])
    graph = build_mesh_graph()
    state = {"prompt": prompt, "jwt": token, "context": {}, "chunks": []}

    print(f"질의: {prompt}")
    final = await graph.ainvoke(state)

    route_label = "Inter-domain(gRPC)" if final["route"] == "inter" else "Intra-domain(subgraph)"
    print(f"라우팅: {final['route']} → {route_label}")
    print(f"수신 청크 수: {len(final['chunks'])}")
    print(f"응답: {final['answer']}")


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "휴가 규정 알려줘"
    asyncio.run(run(prompt))
