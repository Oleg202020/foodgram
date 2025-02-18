from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class User(AbstractUser):
    """Модель переопределяющая поля пользоватяля"""
    email = models.EmailField(
        verbose_name='email address',
        max_length=254,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w@+.-]+$'
            )]
    )
    username = models.CharField(
        verbose_name='Никнейм', max_length=150, unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='Ограничение для ввода символов в Никнейм\
                    допустим ввод: букв, цифр, символов: _ . @ + - '
            )
        ]
    )
    first_name = models.CharField(
        verbose_name='Имя', max_length=150)
    last_name = models.CharField(
        verbose_name='Фамилия', max_length=150)
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

    def __str__(self):
        return self.username  # username


class Follow(models.Model):
    """Модель для отображения подписок."""
    user = models.ForeignKey(  # from_user/текущий пользователь
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(  # to_user/на кого подписан
        User,
        on_delete=models.CASCADE,
        related_name='author',  # following
        verbose_name='Автор'
    )
    is_subscribed = models.BooleanField(
        default=False,
        blank=True,
        verbose_name='Наличие подписки')

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
