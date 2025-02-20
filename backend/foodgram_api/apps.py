from django.apps import AppConfig


class FoodgramApiConfig(AppConfig):
    """
    Конфигурационный класс для приложения `foodgram_api`.
    Определяет имя приложения и базовые настройки.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'foodgram_api'
