# Agent Mesh PoC 통합 테스트 — 디스커버리, 동적 라우팅, 핸드오프, JWT 거부, DLP
import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import grpc
import pytest

from agent_mesh_poc.common import registry
from agent_mesh_poc.common.dlp import mask
from agent_mesh_poc.common.jwt_utils import issue_token
from agent_mesh_poc.common.selection import select_agent
from agent_mesh_poc.generated import agent_mesh_pb2, agent_mesh_pb2_grpc
from agent_mesh_poc.orchestrator import hr_agent
from agent_mesh_poc.orchestrator.graph import build_mesh_graph
from agent_mesh_poc.orchestrator.handoff import resolve_handoff

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVERS = [(50051, "Finance_Agent"), (50052, "Legal_Agent")]


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
def mesh(tmp_path_factory):
    # 테스트 전용 레지스트리 디렉터리로 격리(서브프로세스에도 env로 전파).
    reg_dir = tmp_path_factory.mktemp("registry")
    os.environ["AGENT_MESH_REGISTRY_DIR"] = str(reg_dir)
    env = {**os.environ, "AGENT_MESH_REGISTRY_DIR": str(reg_dir)}

    # intra 에이전트 카드 등록.
    registry.register(hr_agent.CARD)

    procs = []
    for port, agent in SERVERS:
        procs.append(
            subprocess.Popen(
                [sys.executable, "-m", "agent_mesh_poc.remote_domain.server",
                 "--port", str(port), "--agents", agent],
                cwd=str(REPO_ROOT),
                env=env,
            )
        )
    for port, _ in SERVERS:
        if not _wait_port("localhost", port):
            for p in procs:
                p.terminate()
            pytest.fail(f"Remote 서버 기동 실패: {port}")
    yield
    for p in procs:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def _state(prompt: str) -> dict:
    return {
        "prompt": prompt,
        "jwt": issue_token("u1", ["employee"]),
        "context": {},
        "chunks": [],
        "hops": [],
    }


def test_dlp_mask():
    masked = mask("내 번호는 010-1234-5678 이고 메일은 a@b.com 입니다")
    assert "010-1234-5678" not in masked
    assert "a@b.com" not in masked
    assert "***" in masked


def test_discovery(mesh):
    names = {c["name"] for c in registry.discover()}
    assert {"HR_Agent", "Finance_Agent", "Legal_Agent"} <= names


def test_select_by_card(mesh):
    # 디스커버리된 카드 기준으로 휴가 질의는 HR이 선택돼야 한다.
    assert select_agent("휴가 규정 알려줘", registry.discover()) == "HR_Agent"


def test_intra_no_handoff(mesh):
    final = asyncio.run(build_mesh_graph().ainvoke(_state("휴가 규정 알려줘")))
    assert final["hops"] == ["HR_Agent"]
    assert "HR_Agent" in final["answer"]


def test_inter_no_handoff(mesh):
    final = asyncio.run(build_mesh_graph().ainvoke(_state("급여 예산 검토해줘")))
    assert final["hops"] == ["Finance_Agent"]
    assert "Finance_Agent" in final["answer"]
    assert len(final["chunks"]) > 1  # gRPC 스트리밍 청크


def test_handoff_finance_to_legal(mesh):
    final = asyncio.run(build_mesh_graph().ainvoke(_state("급여 인상의 법적 근거 검토해줘")))
    assert final["hops"] == ["Finance_Agent", "Legal_Agent"]
    assert "Legal_Agent" in final["answer"]


def test_bad_jwt_rejected(mesh):
    async def _call():
        async with grpc.aio.insecure_channel("localhost:50051") as channel:
            stub = agent_mesh_pb2_grpc.AgentServiceStub(channel)
            request = agent_mesh_pb2.AgentRequest(
                prompt="x", context={}, agent_name="Finance_Agent"
            )
            metadata = [("authorization", "Bearer invalid.token.value")]
            async for _ in stub.Invoke(request, metadata=metadata):
                pass

    with pytest.raises(grpc.aio.AioRpcError) as exc:
        asyncio.run(_call())
    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED


# --- 핸드오프 종료 판정(순수 함수, 서버 불필요) ---

def test_resolve_handoff_answered():
    d = resolve_handoff(["Finance_Agent"], "", 3)
    assert d["action"] == "stop"
    assert d["message"] == ""  # 정상 답변 → 실제 답변을 덮어쓰지 않음


def test_resolve_handoff_continue():
    d = resolve_handoff(["Finance_Agent"], "Legal_Agent", 3)
    assert d == {"action": "continue", "target": "Legal_Agent"}


def test_resolve_handoff_cycle():
    d = resolve_handoff(["Finance_Agent", "Legal_Agent"], "Finance_Agent", 3)
    assert d["action"] == "stop"
    assert "사이클" in d["message"]
    assert "찾지 못했습니다" in d["message"]


def test_resolve_handoff_exhausted():
    # 카드 3개를 모두 방문한 뒤 또 핸드오프 → 소진(미방문 대상이라도 한도).
    d = resolve_handoff(["A", "B", "C"], "D", 3)
    assert d["action"] == "stop"
    assert "한도 도달" in d["message"]
