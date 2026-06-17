# 송신 페이로드의 민감정보(PII)를 마스킹하는 최소 DLP 유틸
import re

# PoC 수준 패턴: 주민등록번호, 이메일, 휴대폰 번호.
_PATTERNS = [
    re.compile(r"\d{6}-\d{7}"),                  # 주민등록번호
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),     # 이메일
    re.compile(r"01[016789]-?\d{3,4}-?\d{4}"),   # 휴대폰
]


def mask(text: str) -> str:
    masked = text
    for pattern in _PATTERNS:
        masked = pattern.sub("***", masked)
    return masked
