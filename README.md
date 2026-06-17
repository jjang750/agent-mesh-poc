# Agent Mesh PoC

LangGraph 기반 A2A(Agent-to-Agent) Mesh PoC.
**디스커버리(Agent Card + Registry)** 와 **핸드오프(에이전트 간 작업 위임)** 를 갖춘
3 에이전트 / 3 프로세스 메시를 시연한다.

설계 문서:
- [`docs/specs/2026-06-17-agent-mesh-poc-design.md`](docs/specs/2026-06-17-agent-mesh-poc-design.md) — 1단계: 통신 패턴(intra/inter, gRPC, JWT, DLP)
- [`docs/specs/2026-06-17-agent-mesh-discovery-handoff-design.md`](docs/specs/2026-06-17-agent-mesh-discovery-handoff-design.md) — 2단계: 디스커버리 + 핸드오프

## 토폴로지

```
                         ┌─ Registry (.registry/*.json) ─┐
                         │  에이전트가 기동 시 카드 등록   │
                         └───────────────▲───────────────┘
                          discover()      │ register(card)
[main.py] --JWT 발급--> Orchestrator      │
                         ├─ discover : 레지스트리에서 카드 목록 조회
                         ├─ select   : 카드 skills 매칭으로 처리 에이전트 선택
                         └─ dispatch : 대상 호출 → 핸드오프면 재라우팅(loop)
                              │                    │
                   [Intra] 인메모리 그래프      [Inter] gRPC 스트리밍(JWT+DLP)
                              │                    │
                          HR_Agent       Finance_Agent(:50051)   Legal_Agent(:50052)
                                                  └── 법적 사안 → Legal_Agent로 핸드오프 ──┘
```

- 에이전트 3개: HR_Agent(intra), Finance_Agent(inter), Legal_Agent(inter).
- 라우팅은 하드코딩 키워드가 아니라 **레지스트리 카드 기반 동적 선택**.
- 한 에이전트가 자기 일이 아니라고 판단하면 **핸드오프** 지시를 반환하고, 오케스트레이터가 레지스트리에서 대상을 찾아 재라우팅한다(최대 hop 가드).

## 셋업

모든 명령은 **이 레포 루트**에서 실행한다.

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux
```

gRPC 스텁 재생성이 필요하면(프로토 변경 시):

```bash
./.venv/Scripts/python.exe -m grpc_tools.protoc \
  -I agent_mesh_poc/proto \
  --python_out=agent_mesh_poc/generated \
  --grpc_python_out=agent_mesh_poc/generated \
  agent_mesh_poc/proto/agent_mesh.proto
# 생성 후 agent_mesh_pb2_grpc.py의 import를 패키지 경로로 수정:
#   from agent_mesh_poc.generated import agent_mesh_pb2 as agent__mesh__pb2
```

## 실행 (3개 프로세스)

한글 출력이 깨지면 `PYTHONUTF8=1`을 앞에 붙인다.

터미널 1 — Finance 도메인 서버:

```bash
./.venv/Scripts/python.exe -m agent_mesh_poc.remote_domain.server --port 50051 --agents Finance_Agent
```

터미널 2 — Legal 도메인 서버:

```bash
./.venv/Scripts/python.exe -m agent_mesh_poc.remote_domain.server --port 50052 --agents Legal_Agent
```

터미널 3 — Orchestrator (HR는 오케스트레이터 프로세스 내 intra 에이전트로 자기등록):

```bash
./.venv/Scripts/python.exe -m agent_mesh_poc.main "휴가 규정 알려줘"            # → HR_Agent (intra)
./.venv/Scripts/python.exe -m agent_mesh_poc.main "급여 예산 검토해줘"          # → Finance_Agent (inter)
./.venv/Scripts/python.exe -m agent_mesh_poc.main "급여 인상의 법적 근거 검토해줘"  # → Finance → Legal 핸드오프
```

출력의 `핸드오프 경로(hops)` 가 거쳐간 에이전트를 보여준다.

## 테스트

두 Remote 서버(Finance/Legal)를 서브프로세스로 자동 기동하고, 격리된 임시 레지스트리에서
디스커버리·동적 라우팅·핸드오프·JWT 거부·DLP를 검증한다.

```bash
./.venv/Scripts/python.exe -m pytest agent_mesh_poc/tests -v
```

## 디스커버리 & 핸드오프

- **Agent Card**: 각 에이전트가 `{name, description, skills, domain, endpoint}` 카드를 발행. (cf. Google A2A의 Agent Card / `/.well-known/agent.json`)
- **Registry**: 파일 기반(`.registry/<name>.json`). 에이전트가 기동 시 자기 카드를 등록(write), 오케스트레이터가 조회(read). 프로세스 간 공유.
- **선택**: 카드 `skills`와 프롬프트의 매칭 점수로 동적 선택(룰 기반). 프로덕션에서는 LLM 매칭으로 교체.
- **핸드오프**: 에이전트가 답변 대신 `handoff_to`를 반환 → 오케스트레이터가 그 대상을 레지스트리에서 찾아 dispatch 루프를 다시 돈다.
- **종료 보장**([handoff.py](agent_mesh_poc/orchestrator/handoff.py)): 이미 방문한 에이전트로의 재핸드오프(사이클)나 등록된 카드 수만큼 시도해도 답이 없으면 루프를 끊고, **빈 답변 대신 명시적 실패 메시지**(방문 경로 포함)를 반환한다. `hops`가 거쳐간 에이전트 수(=호출 횟수)를 그대로 기록한다.

## 보안 (PoC 범위)

- **JWT 전파/검증**: 진입점에서 발급 → gRPC metadata로 전파 → 서버 인터셉터가 검증, 실패 시 `UNAUTHENTICATED`.
- **DLP 마스킹**: 송신 직전 주민번호·이메일·휴대폰을 `***`로 마스킹(정규식, 최소 구현).

## 범위 외 (후속 과제)

- **레지스트리 헬스/TTL**: 현재 카드는 파일로 영속되어 죽은 에이전트도 남는다. 실제로는 heartbeat/TTL로 stale 카드를 제거해야 한다(죽은 엔드포인트 호출 시 `UNAVAILABLE`로 처리됨).
- **LLM 기반 선택**: 현재 룰 기반 점수 매칭. 카드 description을 LLM이 보고 의미 기반 선택.
- **mTLS 상호 인증**: 현재 `insecure_channel` 사용. 서버는 `grpc.ssl_server_credentials`, 클라이언트는 `grpc.ssl_channel_credentials`로 교체.
- Kafka/Redis 비동기(브로드캐스트형) 핸드오프, 실제 LLM 스트리밍(astream_events), Docker Compose 배포.
