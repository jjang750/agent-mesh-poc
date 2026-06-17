# Remote 도메인 gRPC 서버 — 호스팅 에이전트를 server-streaming으로 노출 + 카드 자기등록
import argparse
import asyncio

import grpc

from agent_mesh_poc.common import registry
from agent_mesh_poc.generated import agent_mesh_pb2, agent_mesh_pb2_grpc
from agent_mesh_poc.remote_domain import finance_agent, legal_agent
from agent_mesh_poc.remote_domain.interceptor import JWTAuthInterceptor

# 이 서버 바이너리가 호스팅할 수 있는 에이전트 카탈로그.
_AGENTS = {
    finance_agent.CARD["name"]: (finance_agent.CARD, finance_agent.build_graph),
    legal_agent.CARD["name"]: (legal_agent.CARD, legal_agent.build_graph),
}


class AgentServicer(agent_mesh_pb2_grpc.AgentServiceServicer):
    def __init__(self, hosted: dict):
        self._graphs = {name: build() for name, (_card, build) in hosted.items()}

    async def Invoke(self, request, context):
        # 인터셉터에서 JWT 검증을 통과한 요청만 도달한다.
        graph = self._graphs.get(request.agent_name)
        if graph is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND, f"호스팅하지 않는 에이전트: {request.agent_name}"
            )
        result = await graph.ainvoke(
            {"prompt": request.prompt, "context": dict(request.context)}
        )
        # 핸드오프면 답변 없이 핸드오프 지시만 done 청크로 전달.
        if result.get("handoff_to"):
            yield agent_mesh_pb2.AgentChunk(
                text="",
                done=True,
                handoff_to=result["handoff_to"],
                handoff_reason=result.get("handoff_reason", ""),
            )
            return
        for token in result["answer"].split(" "):
            yield agent_mesh_pb2.AgentChunk(text=token + " ", done=False)
            await asyncio.sleep(0.02)
        yield agent_mesh_pb2.AgentChunk(text="", done=True)


async def serve(port: int, agent_names: list[str]):
    hosted = {name: _AGENTS[name] for name in agent_names}
    # 기동 시 호스팅 에이전트 카드를 레지스트리에 자기등록(디스커버리 가능하게).
    for _name, (card, _build) in hosted.items():
        registry.register(card)
    server = grpc.aio.server(interceptors=[JWTAuthInterceptor()])
    agent_mesh_pb2_grpc.add_AgentServiceServicer_to_server(AgentServicer(hosted), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    print(f"[Remote] gRPC 서버 :{port} 시작, 호스팅 에이전트: {agent_names}")
    await server.wait_for_termination()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--agents", nargs="+", default=["Finance_Agent"])
    args = parser.parse_args()
    asyncio.run(serve(args.port, args.agents))


if __name__ == "__main__":
    main()
