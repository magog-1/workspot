from fastapi import Depends, HTTPException, status

import auth.service as auth_service
from auth.models import User, UserRole


async def require_admin(
    current_user: User | None = Depends(auth_service.get_current_user_optional),
) -> User:
    """FastAPI dependency — redirects to /auth/login if not authenticated,
    raises 403 if authenticated but not admin."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/auth/login"},
        )
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён. Требуется роль администратора.",
        )
    return current_user
