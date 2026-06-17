# Agent Mesh PoC

LangGraph 기반 A2A(Agent-to-Agent) Mesh **통신 패턴 검증** PoC.
2개 프로세스(2 도메인)에서 3개 에이전트가 협업하는 메커니즘을 시연한다.

설계 문서: [`docs/specs/2026-06-17-agent-mesh-poc-design.md`](docs/specs/2026-06-17-agent-mesh-poc-design.md)

## 토폴로지

```
[main.py]  --JWT 발급-->  Domain A (Orchestrator)
                            ├─ router (키워드 분류)
                            ├─ [Intra] HR_Agent     ← 인메모리 subgraph (참조 전달)
                            └─ [Inter] grpc_client   ← gRPC 스트리밍 + JWT + DLP 마스킹
                                    ▼
                          Domain B (Remote gRPC 서버, 별도 프로세스)
                            └─ Finance_Agent          ← stub 스트리밍 + JWT 검증 인터셉터
```

- 에이전트 3개: Coordinator(router) + HR_Agent(intra) + Finance_Agent(remote).
- 같은 요청 흐름에서 Intra-domain(인메모리)과 Inter-domain(gRPC) 위임을 모두 보여준다.

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

## 실행 (2개 프로세스)

한글 출력이 깨지면 `PYTHONUTF8=1`을 앞에 붙인다.

터미널 1 — Domain B 서버:

```bash
./.venv/Scripts/python.exe -m agent_mesh_poc.remote_domain.server
```

터미널 2 — Orchestrator:

```bash
# Inter-domain 경로 (gRPC로 Domain B 호출)
./.venv/Scripts/python.exe -m agent_mesh_poc.main "급여 인상 예산 검토해줘"

# Intra-domain 경로 (인메모리 subgraph, 서버 불필요)
./.venv/Scripts/python.exe -m agent_mesh_poc.main "휴가 규정 알려줘"
```

## 테스트

서버를 서브프로세스로 자동 기동해 두 경로 + JWT 거부 + DLP를 검증한다.

```bash
./.venv/Scripts/python.exe -m pytest agent_mesh_poc/tests -v
```

## 보안 (PoC 범위)

- **JWT 전파/검증**: 실제 구현. 진입점에서 발급 → gRPC metadata로 전파 → 서버 인터셉터가 검증, 실패 시 `UNAUTHENTICATED`.
- **DLP 마스킹**: 송신 직전 주민번호·이메일·휴대폰을 `***`로 마스킹(정규식, 최소 구현).

## 범위 외 (후속 과제)

- **mTLS 상호 인증**: 현재 `insecure_channel` 사용. 활성화하려면 서버는 `grpc.ssl_server_credentials`(클라이언트 인증서 요구), 클라이언트는 `grpc.ssl_channel_credentials`로 교체한다.
- Kafka/Redis 비동기 이벤트 경로, 실제 LLM 스트리밍(astream_events), Docker Compose 배포.
