from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Админ-модель для пользователей."""
    list_display = ('id', 'username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_active')
