# gRPC 서버 인터셉터 — 요청 metadata의 JWT를 추출·검증(Zero-Trust 인가 전파)
import grpc

from agent_mesh_poc.common.jwt_utils import verify_token


class JWTAuthInterceptor(grpc.aio.ServerInterceptor):
    """모든 RPC 진입 전에 metadata의 Bearer 토큰을 검증한다."""

    async def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata or [])
        auth = metadata.get("authorization", "")
        token = auth[len("Bearer "):] if auth.startswith("Bearer ") else ""
        try:
            verify_token(token)
        except Exception as exc:  # noqa: BLE001 - 모든 검증 실패를 인증 거부로 변환
            return self._deny(f"JWT 검증 실패: {exc}")
        return await continuation(handler_call_details)

    @staticmethod
    def _deny(message: str):
        async def abort(request, context):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, message)

        # Invoke는 unary-request → stream-response 핸들러다.
        return grpc.unary_stream_rpc_method_handler(abort)
