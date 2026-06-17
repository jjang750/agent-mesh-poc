# 파일 기반 Agent Registry — 카드 등록(write)/조회(read)로 프로세스 간 디스커버리
import json
import os
from pathlib import Path


def _registry_dir() -> Path:
    env = os.environ.get("AGENT_MESH_REGISTRY_DIR")
    base = Path(env) if env else Path(__file__).resolve().parents[1] / ".registry"
    base.mkdir(parents=True, exist_ok=True)
    return base


def register(card: dict) -> None:
    """에이전트가 자기 카드를 이름별 파일로 등록한다(원자적 교체로 write 충돌 방지)."""
    path = _registry_dir() / f"{card['name']}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def discover() -> list[dict]:
    """등록된 모든 에이전트 카드를 읽어 목록으로 반환한다."""
    cards = []
    for f in _registry_dir().glob("*.json"):
        try:
            cards.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return cards


def lookup(name: str) -> dict | None:
    path = _registry_dir() / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
