# Agent Mesh 전역 상태(MeshState) — 도메인 간 공유 상태 스키마
import operator
from typing import Annotated, TypedDict


class MeshState(TypedDict):
    prompt: str          # 사용자 질의
    jwt: str             # 진입점에서 발급한 신원 토큰(도메인 간 전파)
    context: dict        # 부가 컨텍스트(원격 전송 시 DLP 마스킹 대상)
    route: str           # router가 결정한 경로: "intra" | "inter"
    chunks: Annotated[list[str], operator.add]  # 스트리밍 청크 누적
    answer: str          # 최종 합성 응답
