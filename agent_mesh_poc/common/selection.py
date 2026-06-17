# 작업-에이전트 매칭 — 카드 skills 기반 점수 라우팅(룰 기반; 프로덕션은 LLM 매칭으로 교체)
def select_agent(prompt: str, cards: list[dict]) -> str | None:
    """프롬프트에 카드 skills가 몇 개 등장하는지로 최적 에이전트를 고른다."""
    best, best_score = None, 0
    for card in cards:
        score = sum(1 for skill in card.get("skills", []) if skill in prompt)
        if score > best_score:
            best, best_score = card["name"], score

    if best is not None:
        return best
    # 매칭 0이면 intra 에이전트로 폴백(없으면 첫 카드).
    intra = [c for c in cards if c.get("domain") == "intra"]
    if intra:
        return intra[0]["name"]
    return cards[0]["name"] if cards else None
