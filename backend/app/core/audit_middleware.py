"""FastAPI middleware to auto-log key actions to audit.events."""
from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

AUDIT_PATHS = {
    ("POST", "/api/v1/auth/login"): "auth.login",
    ("POST", "/api/v1/auth/logout"): "auth.logout",
    ("POST", "/api/v1/auth/register"): "auth.register",
    ("POST", "/api/v1/control/sessions"): "control.session_created",
    ("POST", "/api/v1/pto/queries"): "pto.query_created",
    ("POST", "/api/v1/ntd/documents"): "ntd.document_uploaded",
    ("POST", "/api/v1/pto/registry/import"): "pto.registry_imported",
}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response = await call_next(request)

        path_key = (request.method, request.url.path)
        action = AUDIT_PATHS.get(path_key)

        if action and response.status_code < 400:
            try:
                from app.db.session import AsyncSessionFactory
                from app.modules.audit.service import AuditService
                import jwt as pyjwt

                user_id = None
                user_email = None
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    try:
                        from app.core.config import get_settings
                        settings = get_settings()
                        payload = pyjwt.decode(
                            auth_header[7:], settings.jwt_secret_key,
                            algorithms=[settings.jwt_algorithm]
                        )
                        from uuid import UUID
                        user_id = UUID(payload.get("sub", ""))
                    except Exception:
                        pass

                ip = request.client.host if request.client else None
                ua = request.headers.get("User-Agent")

                async with AsyncSessionFactory() as db:
                    svc = AuditService(db)
                    await svc.log(
                        action=action,
                        user_id=user_id,
                        ip_address=ip,
                        user_agent=ua,
                        payload={"path": str(request.url.path), "status": response.status_code},
                    )
                    await db.commit()
            except Exception:
                pass  # Audit must never break main request

        return response
