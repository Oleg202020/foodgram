Foodgram

Описание проекта

    Foodgram — это сервис для публикации рецептов. Здесь пользователи могут:
    Создавать собственные рецепты, загружать изображения.
    Подписываться на рецепты других авторов.
    Добавлять рецепты в избранное.
    Формировать список покупок и скачивать его в виде текстового файла.
    Проект развернут по адресу:
    https://foodgramlar.viewdns.net

    Автор проекта: Ларионов Олег Сергеевич.

Технологический стек

    Python 3.7+
    Django 3.2+
    Django REST Framework (DRF)
    PostgreSQL (база данных)
    Docker, docker-compose
    Nginx (для отдачи статических файлов и проксирования)
    Gunicorn (WSGI-сервер для Django-приложения)
    (Опционально) Vue/React или другой SPA-фреймворк на фронтенде

Развертывание проекта с помощью Docker

    1 Клонировать репозиторий:
    git clone https://github.com/Oleg202020/foodgram.git
    cd foodgram

    2 Создать и заполнить файл окружения .env в корне проекта:

    SECRET_KEY=<секретный ключ Django>
    DB_ENGINE=django.db.backends.postgresql
    DB_NAME=<имя базы данных>
    POSTGRES_USER=<пользователь postgres>
    POSTGRES_PASSWORD=<пароль к БД>
    DB_HOST=db
    DB_PORT=5432

    Пример (не используйте эти данные на продакшене!):

    SECRET_KEY=some-very-secret-key
    DB_ENGINE=django.db.backends.postgresql
    DB_NAME=foodgram
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    DB_HOST=db
    DB_PORT=5432

    3 Запустить docker-compose:

    docker-compose up -d
    Команда поднимет несколько контейнеров (db, backend, frontend, gateway и т.п. — в зависимости от вашей конфигурации).

    4 Выполнить миграции, собрать статику и (опционально) создать суперпользователя:

    # применяем миграции
    docker-compose exec backend python manage.py migrate

    # собираем статику
    docker-compose exec backend python manage.py collectstatic --noinput

    # создаем суперпользователя
    docker-compose exec backend python manage.py createsuperuser

    5. Проверить, что проект запущен

    Откройте в браузере адрес http://localhost (или используйте IP или домен, если на сервере).
    Если в конфигурации nginx порт прокинут на 80 или 8080, то уточните соответствующий порт (например, http://localhost:8080).
    После этих шагов сайт должен быть доступен по вашему домену или локальному адресу.

Запуск бэкенда локально (без Docker)

    Если вы хотите запустить Django-приложение напрямую:

    1. Установите зависимости:
    pip install -r requirements.txt

    2 Создайте базу данных PostgreSQL или используйте SQLite (изменив настройки в settings.py).

    3 Выполните миграции:
    python manage.py migrate

    4. Cоберите статические файлы:
    python manage.py collectstatic --noinput

    5. Запустите локальный сервер разработки:
    python manage.py runserver

    По умолчанию приложение будет доступно по адресу http://127.0.0.1:8000/.


Развёрнутый проект:
https://foodgramlar.viewdns.net

Автор: Ларионов Олег Сергеевич.

Если остались вопросы, можно связаться по email или другим каналам связи, указанным в репозитории/проекте.