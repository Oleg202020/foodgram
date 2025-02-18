from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """Класс определят права для владельца и администратора.
    В settings.py - permissions не задан(AllowAny по умолчанию) поэтому
    все остальные имеют доступ на все ресурсы, где не определён доступ.
    """

    def has_permission(self, request, view):
        """
        Проверяет общие права доступа.
        Запрос является безопасный (GET, HEAD, OPTIONS)
        или пользователь аутентифицирован.
        """
        return (request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        """
        Проверяет права доступа на уровне объекта.
        Запрос является безопасный (GET, HEAD, OPTIONS),
        пользователь автор объекта,
        пользователь суперпользователь.
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        return (obj.author == request.user
                or request.user.is_superuser)
