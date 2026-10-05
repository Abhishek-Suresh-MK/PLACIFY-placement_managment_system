from rest_framework import permissions

from accounts.models import Role


def _is_admin(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.role == Role.ADMIN)
    )


class IsAdminOrReadOnly(permissions.BasePermission):
    """Authenticated users may read; only admins may modify."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.method in permissions.SAFE_METHODS
                or _is_admin(request.user)
            )
        )


class IsRecruiterOrAdmin(permissions.BasePermission):
    """Only recruiters/admins can access recruiter-only endpoints."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == Role.RECRUITER or _is_admin(request.user))
        )


class IsStudentOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == Role.STUDENT or _is_admin(request.user))
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Read/write access for the owner; admins have unrestricted access."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if _is_admin(request.user):
            return True
        if hasattr(obj, "user"):
            return obj.user_id == request.user.id
        if hasattr(obj, "student"):
            return obj.student.user_id == request.user.id
        return False


class IsStudentOwnerOrRecruiterOrAdmin(permissions.BasePermission):
    """
    Students can access their own objects, recruiters can read objects,
    and admins have full access.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if _is_admin(request.user):
            return True
        if request.user.role == Role.RECRUITER:
            return request.method in permissions.SAFE_METHODS
        if request.user.role == Role.STUDENT:
            return request.method in permissions.SAFE_METHODS or request.method in ("PUT", "PATCH")
        return False

    def has_object_permission(self, request, view, obj):
        if _is_admin(request.user):
            return True
        if request.user.role == Role.RECRUITER:
            return request.method in permissions.SAFE_METHODS
        if hasattr(obj, "user"):
            return obj.user_id == request.user.id
        if hasattr(obj, "student"):
            return obj.student.user_id == request.user.id
        return False


class IsAnnouncementManager(permissions.BasePermission):
    """All authenticated users can read; only admins can write."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return _is_admin(request.user)
