import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.schemas import TokenPair, UserCreate

settings = get_settings()


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, data: UserCreate) -> User:
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self._get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ForbiddenError("Invalid credentials")
        if not user.is_active:
            raise ForbiddenError("Account is deactivated")
        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token)
        except Exception as exc:
            raise ForbiddenError("Invalid refresh token") from exc

        if payload.get("type") != "refresh":
            raise ForbiddenError("Invalid token type")

        token_hash = self._hash_token(refresh_token)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
        result = await self.db.execute(stmt)
        db_token = result.scalar_one_or_none()
        if not db_token or db_token.expires_at < datetime.now(UTC):
            raise ForbiddenError("Refresh token expired or revoked")

        # Rotate: revoke old, issue new
        db_token.revoked_at = datetime.now(UTC)
        user = await self.db.get(User, db_token.user_id)
        if not user:
            raise NotFoundError("User not found")
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        token_hash = self._hash_token(refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(stmt)
        db_token = result.scalar_one_or_none()
        if db_token:
            db_token.revoked_at = datetime.now(UTC)

    async def forgot_password(self, email: str) -> str | None:
        """Generate a password-reset token stored in Redis (TTL 1h).

        Returns the token only in debug mode (for dev/test convenience).
        In production, integrate with an email provider here.
        """
        from app.core.ratelimit import get_redis
        user = await self._get_by_email(email)
        if not user:
            return None  # silent fail — don't leak account existence
        token = secrets.token_urlsafe(32)
        r = get_redis()
        await r.setex(f"pwd_reset:{token}", 3600, str(user.id))
        if settings.app_debug:
            return token
        # TODO: send email with reset link in production
        return None

    async def reset_password(self, token: str, new_password: str) -> None:
        from app.core.ratelimit import get_redis
        r = get_redis()
        user_id_bytes = await r.get(f"pwd_reset:{token}")
        if not user_id_bytes:
            raise ForbiddenError("Invalid or expired reset token")
        from uuid import UUID as _UUID
        user = await self.db.get(User, _UUID(user_id_bytes.decode()))
        if not user:
            raise NotFoundError("User not found")
        user.hashed_password = hash_password(new_password)
        await r.delete(f"pwd_reset:{token}")
        await self.db.flush()

    async def get_user_by_id(self, user_id: UUID) -> User:
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def _get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _issue_tokens(self, user: User) -> TokenPair:
        access = create_access_token(str(user.id), {"role": user.role.value})
        refresh = create_refresh_token(str(user.id))

        token_hash = self._hash_token(refresh)
        expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
        db_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(db_token)
        await self.db.flush()
        return TokenPair(access_token=access, refresh_token=refresh)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
