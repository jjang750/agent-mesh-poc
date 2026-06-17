# Agent Mesh PoC 2단계 설계 — 디스커버리 + 핸드오프

- 작성일: 2026-06-17
- 상태: 구현 완료
- 1단계 문서: [`2026-06-17-agent-mesh-poc-design.md`](2026-06-17-agent-mesh-poc-design.md)

## 배경

1단계는 라우팅이 하드코딩이었다. 오케스트레이터가 키워드 리스트(`_INTER_KEYWORDS`)와
고정 주소(`localhost:50051`)로 "어떤 에이전트가 어디 있는지"를 사람이 알려줘야 했다.
에이전트가 늘면 무너진다. 2단계는 이를 **디스커버리**로 풀고, 에이전트 간 **핸드오프**를 더한다.

## 목표

- 하드코딩 키워드 라우팅 → 레지스트리 카드 기반 동적 선택.
- 에이전트가 자기 일이 아니면 다른 에이전트로 작업을 넘기는 핸드오프.
- 에이전트 3개 / 프로세스 3개로 "여러 곳에서 자동 선택 + 위임"을 시연.

## 구성요소

### Agent Card
각 에이전트가 발행하는 매니페스트.
```json
{ "name": "Finance_Agent", "description": "...", "skills": ["급여","예산",...],
  "domain": "inter", "endpoint": "localhost:50051" }
```
`domain`은 `intra`(오케스트레이터 인메모리 그래프) 또는 `inter`(gRPC endpoint).
(cf. Google A2A 프로토콜의 Agent Card / `/.well-known/agent.json`.)

### Registry (`common/registry.py`)
파일 기반. `.registry/<name>.json`. `register(card)`는 자기 이름 파일로 원자적 write,
`discover()`는 디렉터리의 모든 카드를 read, `lookup(name)`은 단건 조회.
에이전트별로 자기 파일만 쓰므로 프로세스 간 write 충돌이 없다.
`AGENT_MESH_REGISTRY_DIR` 환경변수로 위치 격리(테스트용).

### 선택 (`common/selection.py`)
프롬프트에 카드 `skills`가 몇 개 등장하는지 점수화해 최고점 에이전트 선택. 룰 기반.
프로덕션 교체 지점: 카드 description을 LLM이 보고 의미 기반 선택.

### 핸드오프
- proto 확장: `AgentRequest.agent_name`(한 서버의 다중 에이전트 중 대상),
  `AgentChunk.handoff_to` / `handoff_reason`(답변 대신 핸드오프 지시).
- 에이전트 `respond()`는 `{"answer"}` 또는 `{"handoff_to","handoff_reason"}` 반환.
- 오케스트레이터 그래프: `discover → select → dispatch` 이고, dispatch는 핸드오프를
  받으면 대상을 `target`으로 바꿔 dispatch로 다시 분기한다.
- 종료 보장(`orchestrator/handoff.py`의 순수 함수 `resolve_handoff`): 이미 방문한
  에이전트로의 재핸드오프(사이클) 또는 카드 수만큼 시도 후에도 답이 없으면 루프를 끊고,
  빈 답변 대신 명시적 실패 메시지(방문 경로 포함)로 덮어쓴다. 방문 추적은 `hops`로 한다.

## 토폴로지

```
Registry(.registry/*.json) ◀─register─ HR/Finance/Legal
        ▲ discover
Orchestrator: discover → select → dispatch ──(handoff?)──┐
        │                          │ intra: 인메모리 그래프  │
        └──────────────────────────┘ inter: gRPC(JWT+DLP)   │
                                       ▲                      │
                           Finance(:50051)  Legal(:50052) ◀───┘
```

- HR_Agent: intra, 인메모리.
- Finance_Agent: inter :50051. 법적 트리거 감지 시 Legal_Agent로 핸드오프.
- Legal_Agent: inter :50052. 핸드오프 종착지.

## 시연 시나리오 (테스트로 검증)

| 질의 | 선택 | hops |
|------|------|------|
| "휴가 규정 알려줘" | HR_Agent | HR_Agent |
| "급여 예산 검토해줘" | Finance_Agent | Finance_Agent |
| "급여 인상의 법적 근거 검토해줘" | Finance_Agent | Finance_Agent → Legal_Agent |

## 테스트

디스커버리(3카드), 카드 기반 선택, intra/inter 무핸드오프, Finance→Legal 핸드오프,
JWT 거부, DLP, 그리고 종료 판정(`resolve_handoff`) 단위 테스트(정상/계속/사이클/소진) —
총 11종. Remote 서버 2개를 서브프로세스로 기동, 임시 레지스트리로 격리.

## 범위 외 (후속)

- 레지스트리 heartbeat/TTL(죽은 카드 정리), LLM 기반 선택, mTLS,
  Kafka/Redis 브로드캐스트형 핸드오프, 실제 LLM 스트리밍.
