# 핸드오프 진행/중단 판정 — 사이클 차단 및 카드 수 소진 처리(순수 함수)
def resolve_handoff(visited: list[str], handoff_to: str, catalog_size: int) -> dict:
    """현재까지 방문한 에이전트(visited)와 다음 핸드오프 대상으로 진행 여부를 판정한다.

    반환: {"action": "continue", "target": <name>}
          또는 {"action": "stop", "message": <폴백 메시지 또는 "">}
    message가 빈 문자열이면 정상 종료(답변 완료), 비어있지 않으면 핸드오프 실패다.
    """
    if not handoff_to:
        # 핸드오프 없음 → 답변 완료, 정상 종료.
        return {"action": "stop", "message": ""}

    path = " → ".join(visited)
    if handoff_to in visited:
        # 이미 방문한 에이전트로의 재핸드오프 = 사이클.
        return {
            "action": "stop",
            "message": (
                f"[Orchestrator] 핸드오프 중단: '{handoff_to}' 는 이미 방문함(사이클). "
                f"경로: {path}. 처리 가능한 에이전트를 찾지 못했습니다."
            ),
        }
    if len(visited) >= catalog_size:
        # 등록된 모든 에이전트를 시도했는데도 답변이 없음.
        return {
            "action": "stop",
            "message": (
                f"[Orchestrator] 핸드오프 한도 도달: 에이전트 {catalog_size}개를 모두 시도했으나 "
                f"답변 없음. 경로: {path}. 처리 가능한 에이전트를 찾지 못했습니다."
            ),
        }
    return {"action": "continue", "target": handoff_to}
