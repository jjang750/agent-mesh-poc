# Agent Mesh PoC 설계 문서

- 작성일: 2026-06-17
- 상태: 승인됨 (구현 진행)

## 목표

LangGraph 기반으로 2개 이상의 에이전트가 협업하는 A2A Mesh **통신 패턴 검증**.
프로덕션급 보안 스택 전체가 아니라, 도메인 간 통신 메커니즘 자체를 동작 시연하는 것이 목적이다.

## 확정된 범위 (브레인스토밍 결과)

| 항목 | 결정 |
|------|------|
| 1차 목표 | A2A Mesh 통신 패턴 검증 |
| 에이전트 두뇌 | 결정론적 stub 응답 (LLM 호출 없음) |
| 비동기 경로 | 제외 — gRPC sync 스트리밍만 |
| 보안 | JWT 전파/검증만 실제 구현. DLP는 최소 정규식 마스킹. mTLS는 문서화만 |
| 토폴로지 | 2개 프로세스, localhost gRPC loopback (A안) |

## 토폴로지 — 2 도메인 / 3 에이전트

```
[진입점 main.py] --JWT 발급--> Domain A (Orchestrator 프로세스)
                                 LangGraph StateGraph(MeshState)
                                 ├─ router 노드 (키워드 분류)
                                 ├─ [Intra] HR_Agent  ← 인메모리 subgraph (참조 전달)
                                 └─ [Inter] grpc_client 노드
                                         │ gRPC server-streaming
                                         │ + JWT(metadata) + DLP 마스킹
                                         ▼
                                 Domain B (Remote 프로세스, gRPC 서버)
                                    └─ Finance_Agent ← stub 스트리밍 + JWT 검증 인터셉터
```

- 에이전트 3개: Coordinator(router) + HR_Agent(intra) + Finance_Agent(remote) → 필수요건(2개 이상) 충족.
- 같은 요청 흐름에서 intra(인메모리)와 inter(gRPC) 위임을 모두 시연.

## 컴포넌트

- `proto/agent_mesh.proto` — `AgentService.Invoke(AgentRequest) returns (stream AgentChunk)`. 프롬프트·컨텍스트는 body, JWT는 metadata.
- `common/state.py` — `MeshState` TypedDict.
- `common/jwt_utils.py` — PyJWT 발급/검증(HS256 공유 시크릿).
- `common/dlp.py` — 정규식 PII 마스킹(주민번호·이메일·휴대폰).
- `remote_domain/finance_agent.py` — stub Finance LangGraph.
- `remote_domain/interceptor.py` — 서버측 JWT 검증 인터셉터.
- `remote_domain/server.py` — gRPC 서버(Finance_Agent server-streaming).
- `orchestrator/hr_agent.py` — intra-domain subgraph.
- `orchestrator/grpc_client.py` — inter-domain async 노드(DLP+JWT 전파).
- `orchestrator/graph.py` — router + 분기 메인 그래프.
- `main.py` — CLI 진입점.

## 데이터 흐름

JWT 발급 → MeshState 초기화 → router가 키워드로 intra/inter 판정 →
intra면 subgraph가 참조로 state 갱신 / inter면 grpc_client가 DLP 마스킹 후
metadata에 JWT 실어 스트리밍 호출 → 청크를 state.chunks에 누적 → 진입점 출력.

## 에러 처리

- JWT 누락/위변조 → 서버 인터셉터가 `UNAUTHENTICATED` abort → orchestrator가 에러 청크로 변환.
- 원격 서버 다운 → `UNAVAILABLE` 캐치 → "원격 도메인 호출 실패" 청크.

## 테스트 (pytest)

- intra 경로: route=="intra", 응답에 HR_Agent 포함.
- inter 경로: 서버 서브프로세스 부팅 → route=="inter", 응답에 Finance_Agent 포함, 청크 2개 이상.
- JWT 거부: 잘못된 토큰으로 직접 호출 → `UNAUTHENTICATED`.
- DLP: 민감 패턴이 `***`로 마스킹.

## 격리

xperp_qna_chatbot 레포와 무관한 작업이라 **독립 레포(`workspace/agent-mesh-poc`)로 분리**했다.
의존성 충돌(grpcio-tools가 protobuf를 6.x로 올려 챗봇의 google-ai-generativelanguage<5와 충돌)을
피하려고 전용 venv(`.venv`)를 사용한다.

## 범위 외 (후속)

mTLS 상호 인증, Kafka/Redis 비동기 경로, 실제 LLM 스트리밍, Docker Compose 배포.
