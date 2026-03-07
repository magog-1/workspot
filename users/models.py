# Users module does not define its own model.
# The User model lives in auth/models.py to avoid duplication.
# Import it from there wherever needed:
#   from auth.models import User

from auth.models import User  # noqa: F401 — re-export for convenience

__all__ = ["User"]
