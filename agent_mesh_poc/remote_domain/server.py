# Remote 도메인(Domain B) gRPC 서버 — Finance_Agent를 server-streaming으로 노출
import asyncio

import grpc

from agent_mesh_poc.generated import agent_mesh_pb2, agent_mesh_pb2_grpc
from agent_mesh_poc.remote_domain.finance_agent import build_finance_graph
from agent_mesh_poc.remote_domain.interceptor import JWTAuthInterceptor

LISTEN = "[::]:50051"


class AgentServicer(agent_mesh_pb2_grpc.AgentServiceServicer):
    def __init__(self):
        self._graph = build_finance_graph()

    async def Invoke(self, request, context):
        # 인터셉터에서 JWT 검증을 이미 통과한 요청만 여기 도달한다.
        result = await self._graph.ainvoke(
            {"prompt": request.prompt, "context": dict(request.context)}
        )
        answer = result["answer"]
        # 추론 결과를 공백 단위 청크로 스트리밍.
        for token in answer.split(" "):
            yield agent_mesh_pb2.AgentChunk(text=token + " ", done=False)
            await asyncio.sleep(0.02)
        yield agent_mesh_pb2.AgentChunk(text="", done=True)


async def serve():
    server = grpc.aio.server(interceptors=[JWTAuthInterceptor()])
    agent_mesh_pb2_grpc.add_AgentServiceServicer_to_server(AgentServicer(), server)
    server.add_insecure_port(LISTEN)
    await server.start()
    print(f"[Domain B] Finance_Agent gRPC 서버 시작: {LISTEN}")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
