# Agent Mesh PoC 통합 테스트 — intra/inter 경로, JWT 거부, DLP 마스킹 검증
import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path

import grpc
import pytest

from agent_mesh_poc.common.dlp import mask
from agent_mesh_poc.common.jwt_utils import issue_token
from agent_mesh_poc.generated import agent_mesh_pb2, agent_mesh_pb2_grpc
from agent_mesh_poc.orchestrator.graph import build_mesh_graph

REPO_ROOT = Path(__file__).resolve().parents[2]
PORT = 50051


def _wait_port(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                return True
            except OSError:
                time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def remote_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "agent_mesh_poc.remote_domain.server"],
        cwd=str(REPO_ROOT),
    )
    if not _wait_port("localhost", PORT):
        proc.terminate()
        pytest.fail("Domain B gRPC 서버가 시간 내에 기동하지 않았습니다.")
    yield
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_dlp_mask():
    masked = mask("내 번호는 010-1234-5678 이고 메일은 a@b.com 입니다")
    assert "010-1234-5678" not in masked
    assert "a@b.com" not in masked
    assert "***" in masked


def test_intra_route():
    graph = build_mesh_graph()
    state = {
        "prompt": "휴가 규정 알려줘",
        "jwt": issue_token("u1", ["employee"]),
        "context": {},
        "chunks": [],
    }
    final = asyncio.run(graph.ainvoke(state))
    assert final["route"] == "intra"
    assert "HR_Agent" in final["answer"]


def test_inter_route(remote_server):
    graph = build_mesh_graph()
    state = {
        "prompt": "급여 인상 예산 검토해줘",
        "jwt": issue_token("u1", ["employee"]),
        "context": {},
        "chunks": [],
    }
    final = asyncio.run(graph.ainvoke(state))
    assert final["route"] == "inter"
    assert "Finance_Agent" in final["answer"]
    assert len(final["chunks"]) > 1  # 스트리밍으로 여러 청크 수신


def test_bad_jwt_rejected(remote_server):
    async def _call():
        async with grpc.aio.insecure_channel(f"localhost:{PORT}") as channel:
            stub = agent_mesh_pb2_grpc.AgentServiceStub(channel)
            request = agent_mesh_pb2.AgentRequest(prompt="x", context={})
            metadata = [("authorization", "Bearer invalid.token.value")]
            async for _ in stub.Invoke(request, metadata=metadata):
                pass

    with pytest.raises(grpc.aio.AioRpcError) as exc:
        asyncio.run(_call())
    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED
