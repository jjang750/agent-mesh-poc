# Intra-domain HR_Agent — 오케스트레이터 프로세스 내 인메모리 그래프(네트워크 I/O 없음) + 카드
from agent_mesh_poc.common.agent_base import build_agent_graph

CARD = {
    "name": "HR_Agent",
    "description": "휴가·근태·채용 등 인사 도메인 안내",
    "skills": ["휴가", "규정", "인사", "근태", "채용", "hr"],
    "domain": "intra",
    "endpoint": "",
}


def respond(prompt: str, context: dict) -> dict:
    return {
        "answer": f"[HR_Agent] 인사 도메인 처리 결과: '{prompt}' 에 대한 사내 규정 안내입니다."
    }


def build_graph():
    return build_agent_graph(respond)
