from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import User, Follow


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """
    Админ-модель для пользователей, даёт возможность
    редактировать пароли через админку, как у стандартной модели."""
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('username',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """
    Админ-модель для управления подписками (Follow).
    """
    list_display = ('id', 'user', 'author', 'is_subscribed')
    search_fields = ('user__username', 'author__username')
    list_filter = ('is_subscribed',)


admin.site.unregister(Group)
