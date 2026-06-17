# Inter-domain Legal_Agent — 법무 도메인 에이전트(stub), 핸드오프 종착지
from agent_mesh_poc.common.agent_base import build_agent_graph

CARD = {
    "name": "Legal_Agent",
    "description": "법률·계약·컴플라이언스 등 법무 도메인 검토",
    "skills": ["법률", "계약서", "소송", "컴플라이언스", "legal"],
    "domain": "inter",
    "endpoint": "localhost:50052",
}


def respond(prompt: str, context: dict) -> dict:
    return {
        "answer": f"[Legal_Agent] 법무 검토 결과: '{prompt}' 에 대한 법적 근거 및 리스크 안내입니다."
    }


def build_graph():
    return build_agent_graph(respond)
