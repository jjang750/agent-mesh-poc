# Inter-domain 호출 — 카드 endpoint로 gRPC 스트리밍 + JWT 전파 + DLP 마스킹 + 핸드오프 수신
import grpc

from agent_mesh_poc.common.dlp import mask
from agent_mesh_poc.generated import agent_mesh_pb2, agent_mesh_pb2_grpc


async def call_remote(card: dict, prompt: str, context: dict, jwt: str) -> dict:
    # 송신 직전 PII 마스킹(DLP).
    masked_prompt = mask(prompt)
    masked_context = {k: mask(str(v)) for k, v in (context or {}).items()}
    # 최초 사용자 JWT를 metadata에 실어 타 도메인까지 신원을 전파한다.
    metadata = [("authorization", f"Bearer {jwt}")]

    chunks: list[str] = []
    handoff_to, handoff_reason = "", ""
    try:
        async with grpc.aio.insecure_channel(card["endpoint"]) as channel:
            stub = agent_mesh_pb2_grpc.AgentServiceStub(channel)
            request = agent_mesh_pb2.AgentRequest(
                prompt=masked_prompt,
                context=masked_context,
                agent_name=card["name"],
            )
            async for chunk in stub.Invoke(request, metadata=metadata):
                if chunk.text:
                    chunks.append(chunk.text)
                if chunk.handoff_to:
                    handoff_to = chunk.handoff_to
                    handoff_reason = chunk.handoff_reason
    except grpc.aio.AioRpcError as exc:
        err = f"[Orchestrator] {card['name']} 호출 실패({exc.code().name}): {exc.details()}"
        return {"chunks": [err], "answer": err, "handoff_to": "", "handoff_reason": ""}

    return {
        "chunks": chunks,
        "answer": "".join(chunks).strip(),
        "handoff_to": handoff_to,
        "handoff_reason": handoff_reason,
    }
