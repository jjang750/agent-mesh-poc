# 인수인계 문서 (Agent Mesh PoC)

> 다음 세션이 이 프로젝트를 바로 이어받기 위한 컨텍스트. 최종 갱신: 2026-06-17.

## 1. 한 줄 요약

LangGraph 기반 A2A(Agent-to-Agent) Mesh PoC. 디스커버리(Agent Card + Registry)와
핸드오프(에이전트 간 작업 위임)를 갖춘 **3 에이전트 / 3 프로세스** 메시가 동작한다.

## 2. 위치 · 좌표

- 로컬: `C:\Users\PC-727\workspace\agent-mesh-poc`
- GitHub: https://github.com/jjang750/agent-mesh-poc (branch `main`)
- venv: `.venv` (이 레포 전용. 아래 4번 이유로 챗봇 venv와 분리)
- 모태 레포: `C:\Users\PC-727\workspace\xperp_qna_chatbot` — **무관**. 이 PoC는 거기서 분리해 나온 것.

## 3. 현재 상태 (무엇이 되어 있나)

- **1단계 (commit `4b9e8da`)**: 통신 패턴. Intra-domain(인메모리 그래프) + Inter-domain(gRPC server-streaming) + JWT 전파/검증 인터셉터 + DLP 마스킹.
- **2단계 (commit `d121f42`)**: 디스커버리 + 핸드오프.
  - Registry: 파일 기반 `.registry/<name>.json`. 에이전트가 기동 시 카드 `register()`, 오케스트레이터가 `discover()`.
  - 선택: 카드 `skills` 매칭 점수 기반 동적 선택(룰 기반).
  - 핸드오프: 에이전트가 `handoff_to` 반환 → 오케스트레이터가 레지스트리에서 대상 찾아 dispatch 루프 재진입.
  - 종료 보장(`orchestrator/handoff.py`의 `resolve_handoff`): 사이클(이미 방문) 또는 카드 수 소진 시 루프 종료 + 빈 답변 대신 실패 메시지. 호출 횟수는 `hops` 길이로 카운트됨.
- **테스트 7/7 통과.** 마지막으로 녹색 확인함.

에이전트 3개: `HR_Agent`(intra, 오케스트레이터 인메모리), `Finance_Agent`(inter :50051),
`Legal_Agent`(inter :50052). Finance는 법적 트리거 감지 시 Legal로 핸드오프.

## 4. 실행 · 테스트

모든 명령은 레포 루트에서. 한글 깨지면 `PYTHONUTF8=1` 접두.

```bash
# 의존성
./.venv/Scripts/python.exe -m pip install -r requirements.txt

# 테스트 (Remote 서버 2개를 자동 기동, 임시 레지스트리로 격리)
./.venv/Scripts/python.exe -m pytest agent_mesh_poc/tests -v

# 데모 (3 프로세스)
#  터미널1: ...server --port 50051 --agents Finance_Agent
#  터미널2: ...server --port 50052 --agents Legal_Agent
#  터미널3: ...main "급여 인상의 법적 근거 검토해줘"   → Finance → Legal 핸드오프
```

상세는 [`README.md`](../README.md), 설계는 [`docs/specs/`](specs/).

## 5. 함정 · 비자명한 결정 (이거 모르면 시간 날림)

1. **protobuf 충돌로 venv 분리** — `grpcio-tools`가 protobuf를 6.x로 올린다. 챗봇 레포는 `google-ai-generativelanguage`(protobuf <5) 때문에 깨진다. 그래서 이 PoC는 **전용 venv**를 쓴다. 챗봇 venv에 grpcio-tools를 절대 깔지 말 것.
2. **requirements.txt는 ASCII만** — 한글 주석을 넣으면 Windows pip가 cp949로 읽다 `UnicodeDecodeError`로 설치 전체가 실패한다. (config 파일이라 한글 헤더 규칙 예외.)
3. **좀비 gRPC 프로세스** — 데모/테스트로 띄운 서버가 50051/50052를 안 놓으면, 새 서버는 바인드 실패하고 오케스트레이터가 **옛 코드 서버**에 붙어 엉뚱한 결과가 나온다. 증상이 이상하면 먼저 포트 점유 확인:
   ```powershell
   Get-NetTCPConnection -LocalPort 50051,50052 -State Listen | %{ Stop-Process -Id $_.OwningProcess -Force }
   ```
4. **proto 재생성 후 import 수정 필요** — `protoc`가 만든 `agent_mesh_pb2_grpc.py`는 `import agent_mesh_pb2`로 나온다. 패키지 경로 `from agent_mesh_poc.generated import agent_mesh_pb2 as agent__mesh__pb2`로 매번 고쳐야 한다. (README에 명시.)
5. **.gitignore 제외 대상** — `.venv/`, `.registry/`, `.bkit/`, `__pycache__/`. 특히 `.bkit/`(bkit 툴 세션 상태)가 이 레포에 생기므로 커밋 금지.
6. **CRLF 경고** — git이 LF→CRLF 경고를 뱉지만 무해. 무시.
7. **stub 에이전트** — LLM 호출 없음. 응답은 결정론적 문자열. 스트리밍은 gRPC server-streaming 계층에서 일어남(공백 단위 청크).

## 6. 알려진 한계 (다음 작업 후보)

- **레지스트리 heartbeat/TTL 없음** — 카드가 파일로 영속돼 죽은 에이전트도 목록에 남는다. 죽은 endpoint 호출 시 `UNAVAILABLE`로 처리될 뿐. → TTL/헬스체크 추가 후보.
- **선택이 룰 기반** — 카드 description을 LLM이 보고 의미 기반 선택하도록 교체 후보.
- **mTLS 미적용** — 현재 `insecure_channel`. README에 활성화 방법만 문서화.
- **비동기 경로 없음** — Kafka/Redis 브로드캐스트형 핸드오프(요청 발행 → 에이전트 자기선택)는 범위 외.
- 실제 LLM 스트리밍(`astream_events`), Docker Compose 배포도 미구현.

→ 가장 자연스러운 다음 한 걸음: **LLM 기반 선택** / **레지스트리 TTL** / **비동기 pub-sub 핸드오프** 중 택1. (사용자 미정.)

## 7. 컨벤션

- 신규 소스 파일 첫 줄에 역할을 적은 한글 주석 1줄(config 파일 제외).
- 커밋 메시지에 한글/멀티라인을 넣을 때 PowerShell `@'...'@`를 **Bash 도구에서 쓰지 말 것**(`@`가 섞인다). 메시지 파일 + `git commit -F`로.
