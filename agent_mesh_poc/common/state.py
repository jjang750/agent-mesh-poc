# Agent Mesh 전역 상태(MeshState) — 디스커버리·핸드오프 루프용 공유 상태 스키마
import operator
from typing import Annotated, TypedDict


class MeshState(TypedDict):
    prompt: str          # 사용자 질의
    jwt: str             # 진입점에서 발급한 신원 토큰(도메인 간 전파)
    context: dict        # 부가 컨텍스트(원격 전송 시 DLP 마스킹 대상)
    catalog: list[dict]  # 레지스트리에서 디스커버리한 에이전트 카드 목록
    target: str          # 현재 dispatch 대상 에이전트 이름
    hops: Annotated[list[str], operator.add]    # 거쳐간 에이전트(핸드오프 경로)
    handoff_to: str      # 마지막 dispatch가 반환한 핸드오프 대상(있으면 재라우팅)
    handoff_reason: str
    chunks: Annotated[list[str], operator.add]  # 스트리밍 청크 누적
    answer: str          # 최종 응답
