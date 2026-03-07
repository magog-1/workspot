from fastapi import Depends, HTTPException, status

import auth.service as auth_service
from auth.models import User, UserRole


async def require_admin(
    current_user: User = Depends(auth_service.get_current_user),
) -> User:
    """FastAPI dependency — allows access only to users with role=admin."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён. Требуется роль администратора.",
        )
    return current_user
