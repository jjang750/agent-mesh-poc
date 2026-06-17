# Inter-domain 위임 노드 — gRPC server-streaming 호출 + JWT 전파 + DLP 마스킹
import grpc

from agent_mesh_poc.common.dlp import mask
from agent_mesh_poc.common.state import MeshState
from agent_mesh_poc.generated import agent_mesh_pb2, agent_mesh_pb2_grpc

REMOTE = "localhost:50051"


async def call_remote(state: MeshState) -> dict:
    # 송신 직전 PII 마스킹(DLP). 컨텍스트 값도 함께 마스킹한다.
    masked_prompt = mask(state["prompt"])
    masked_context = {k: mask(str(v)) for k, v in state.get("context", {}).items()}
    # 최초 사용자 JWT를 metadata에 실어 타 도메인까지 신원을 전파한다.
    metadata = [("authorization", f"Bearer {state['jwt']}")]

    chunks: list[str] = []
    try:
        async with grpc.aio.insecure_channel(REMOTE) as channel:
            stub = agent_mesh_pb2_grpc.AgentServiceStub(channel)
            request = agent_mesh_pb2.AgentRequest(
                prompt=masked_prompt, context=masked_context
            )
            async for chunk in stub.Invoke(request, metadata=metadata):
                if chunk.text:
                    chunks.append(chunk.text)
    except grpc.aio.AioRpcError as exc:
        err = f"[Orchestrator] 원격 도메인 호출 실패({exc.code().name}): {exc.details()}"
        return {"chunks": [err], "answer": err}

    answer = "".join(chunks).strip()
    return {"chunks": chunks, "answer": answer}
