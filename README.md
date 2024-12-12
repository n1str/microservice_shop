# Микросервисный Магазин

Простой магазин на микросервисной архитектуре с использованием gRPC и REST API.

## Сервисы
- API Gateway (:8000) - REST API + Swagger UI
- Сервис Пользователей (:50051) - Управление пользователями
- Сервис Заказов (:50052) - Обработка заказов
- Основной Сервис (:50050) - Логика

## Быстрый старт
```bash
docker-compose up --build
```

## Примеры API
Создание пользователя:
```bash
curl -X POST http://localhost:8000/users -H "Content-Type: application/json" \
-d '{"username": "test", "email": "test@test.com", "password": "test"}'
```

Создание заказа:
```bash
curl -X POST http://localhost:8000/orders -H "Content-Type: application/json" \
-d '{"user_id": "user_id", "items": [{"product_id": "1", "quantity": 1, "price": 10.99}]}'
```

## Технологии
- Python + FastAPI + gRPC
- MongoDB
- Docker
- JWT Авторизация