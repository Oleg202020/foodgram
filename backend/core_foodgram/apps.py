from django.apps import AppConfig


class CoreFoodgramConfig(AppConfig):
    """
    Конфигурационный класс для приложения `core_foodgram`.
    Содержит базовые настройки и имя приложения.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core_foodgram'
