# 사용자 신원(JWT) 발급·검증 유틸 — 도메인 간 인가 컨텍스트 전파용
import datetime

import jwt

# PoC 전용 공유 시크릿. 운영에서는 KMS/비대칭키로 교체해야 한다.
SECRET = "poc-shared-secret-do-not-use-in-prod"
ALGORITHM = "HS256"


def issue_token(subject: str, roles: list[str], ttl_seconds: int = 3600) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": subject,
        "roles": roles,
        "iat": now,
        "exp": now + datetime.timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """검증 실패 시 jwt.InvalidTokenError 계열 예외를 던진다."""
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
