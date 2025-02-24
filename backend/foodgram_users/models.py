from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import RegexValidator
from django.db import models

from .constants import MAX_LENGTH_EMAIL, MAX_LENGTH_NAME


class User(AbstractUser):
    """Модель переопределяющая поля пользоватяля"""
    email = models.EmailField(
        verbose_name='email address',
        max_length=MAX_LENGTH_EMAIL,
        unique=True,
        validators=[
            RegexValidator(regex=r'^[\w@+.-]+$')
        ]
    )
    username = models.CharField(
        verbose_name='Никнейм',
        max_length=MAX_LENGTH_NAME,
        unique=True,
        validators=[UnicodeUsernameValidator()]
    )
    first_name = models.CharField(
        verbose_name='Имя', max_length=MAX_LENGTH_NAME)
    last_name = models.CharField(
        verbose_name='Фамилия', max_length=MAX_LENGTH_NAME)
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='foodgram_users/images/',
        blank=True,
        null=True,
        default=None,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', ]

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username  # username


class Follow(models.Model):
    """Модель для отображения подписок."""
    user = models.ForeignKey(  # from_user/текущий пользователь
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(  # to_user/на кого подписан
        User,
        on_delete=models.CASCADE,
        related_name='followers',  # following
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='%(app_label)s_%(class)s_unique_follow'
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_prevent_self_follow",
                check=~models.Q(user=models.F('author'))
            )
        ]

    def __str__(self):
        return (f'{self.user} подписан на {self.author}')
