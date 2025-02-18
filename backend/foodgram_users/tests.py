from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from rest_framework.test import APIClient

from .models import Follow

User = get_user_model()


class UsersAPITestCase(TestCase):
    """
    Тест-кейс для проверки работы пользовательского API.
    Содержит тесты на различные эндпоинты вьюсета UserViewSet и
    связанные с ним действия.
    """

    def setUp(self):
        """
        Инициализация тестовых данных и клиентов для каждого теста.

        Создаются:
        - Гость (неавторизованный клиент) — self.guest_client
        - Авторизованный клиент — self.auth_client
        - Пользователь (self.user)
        """
        self.guest_client = Client()
        self.auth_client = APIClient()

        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword'
        )
        self.auth_client.force_authenticate(user=self.user)

    def test_user_list_is_accessible(self):
        """
        Проверка доступности списка пользователей: /api/users/.
        Ожидается:
        - Код ответа 200 (OK).
        """
        response = self.guest_client.get('/api/users/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_user_registration(self):
        """
        Проверка регистрации нового пользователя:  /api/users/.
        Ожидается:
        - Код ответа 201 (Created) при корректных данных.
        - Пользователь с указанным username должен существовать в БД.
        """
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newstrongpassword'
        }
        response = self.guest_client.post('/api/users/', data=data)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_user_detail_is_accessible(self):
        """
        Проверка доступности детального просмотра пользователя:
        /api/users/{id}/ GET.
        Ожидается:
        - Код ответа 200 (OK) для существующего пользователя.
        """
        response = self.guest_client.get(f'/api/users/{self.user.id}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_me_endpoint_for_authorized_user(self):
        """
        Проверка эндпоинта /api/users/me/ для авторизованного пользователя.
        Ожидается:
        - Код ответа 200 (OK).
        - В ответе содержится корректная информация о пользователе.
        """
        response = self.auth_client.get('/api/users/me/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data['username'], self.user.username)

    def test_me_endpoint_for_unauthorized_user(self):
        """
        Проверка эндпоинта /api/users/me/ для неавторизованного пользователя.
        Ожидается:
        - Код ответа 401 (Unauthorized),
        если применяются стандартные настройки.
        """
        response = self.guest_client.get('/api/users/me/')
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_subscribe_to_another_user(self):
        """
        Проверка подписки на другого пользователя:
        /api/users/{id}/subscribe/ POST.
        Ожидается:
        - Код ответа 201 (Created) при успешной подписке.
        - В модели Follow должен появиться соответствующий объект.
        """
        other_user = User.objects.create_user(
            username='otheruser',
            email='otheruser@example.com',
            password='otherpassword'
        )
        response = self.auth_client.post(
            f'/api/users/{other_user.id}/subscribe/')
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(Follow.objects.filter(
            user=self.user, author=other_user).exists())

    def test_subscribe_to_self_forbidden(self):
        """
        Проверка попытки подписаться на самого себя:
        /api/users/{id}/subscribe/, где id текущего пользователя (POST).
        Ожидается:
        - Код ответа 400 (Bad Request).
        - Объект Follow не создается.
        """
        response = self.auth_client.post(
            f'/api/users/{self.user.id}/subscribe/')
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertFalse(Follow.objects.filter(
            user=self.user, author=self.user).exists())

    def test_unsubscribe_from_user(self):
        """
        Проверка отписки от пользователя:
        /api/users/{id}/subscribe/ DELETE.
        Ожидается:
        - Код ответа 204 (No Content) при успешной отписке.
        - Объект Follow должен быть удалён.
        """
        other_user = User.objects.create_user(
            username='subscribeduser',
            email='subscribeduser@example.com',
            password='somepassword'
        )
        Follow.objects.create(user=self.user, author=other_user)
        response = self.auth_client.delete(
            f'/api/users/{other_user.id}/subscribe/')
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(Follow.objects.filter(
            user=self.user, author=other_user).exists())

    def test_subscriptions_list(self):
        """
        Проверка списка подписок текущего пользователя:
        /api/users/subscriptions/ GET.
        Ожидается:
        - Код ответа 200 (OK).
        - Сериализованные данные о подписках пользователя.
        """
        other_user = User.objects.create_user(
            username='subscribeduser',
            email='subscribeduser@example.com',
            password='somepassword'
        )
        Follow.objects.create(user=self.user, author=other_user)
        response = self.auth_client.get('/api/users/subscriptions/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn('results', response.data)
