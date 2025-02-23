from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html

from .models import Follow, User


@admin.register(User)
class FoodgramUserAdmin(BaseUserAdmin):
    """
    Админ-модель для пользователей, даёт возможность
    редактировать пароли через админку, как у стандартной модели."""
    list_display = ('id', 'username', 'email', 'first_name',
                    'last_name', 'is_staff'
                    )
    search_fields = ('username', 'email')
    ordering = ('username',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """
    Админ-модель для управления подписками (Follow).
    """
    list_display = ('id', 'user', 'author', 'get_is_subscribed')
    list_filter = ('user', 'author',)

    def get_is_subscribed(self, obj):
        """
        Метод для вычисления, подписан ли текущий пользователь на автора.
        """
        is_subscribed = obj.user.follower.filter(author=obj.author).exists()
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if is_subscribed else 'red',
            'Да' if is_subscribed else 'Нет'
        )

    @admin.display(description='Подписан ли пользователь на автора?')
    def is_subscribed_display(self, obj):
        """
        Отображение "Да"/"Нет" для подписки в админке.
        """
        is_subscribed = obj.user.follower.filter(author=obj.author).exists()
        return 'Да' if is_subscribed else 'Нет'


admin.site.unregister(Group)
