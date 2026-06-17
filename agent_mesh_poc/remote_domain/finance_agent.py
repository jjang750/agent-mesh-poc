# Inter-domain Finance_Agent — 재무 도메인. 법적 사안은 Legal_Agent로 핸드오프
from agent_mesh_poc.common.agent_base import build_agent_graph

CARD = {
    "name": "Finance_Agent",
    "description": "예산·비용·급여·회계 등 재무 도메인 분석",
    "skills": ["급여", "예산", "비용", "회계", "재무", "인상", "finance"],
    "domain": "inter",
    "endpoint": "localhost:50051",
}

# 자기 영역이 아니라고 판단하는 트리거(법적 사안).
_LEGAL_TRIGGERS = ("법", "법적", "법률", "위법", "소송", "계약")


def respond(prompt: str, context: dict) -> dict:
    if any(t in prompt for t in _LEGAL_TRIGGERS):
        return {
            "handoff_to": "Legal_Agent",
            "handoff_reason": "법적 판단이 필요하여 Legal_Agent로 핸드오프합니다.",
        }
    return {
        "answer": f"[Finance_Agent] 재무 분석 결과: '{prompt}' 에 대한 예산/비용 검토 응답입니다."
    }


def build_graph():
    return build_agent_graph(respond)
