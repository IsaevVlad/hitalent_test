# API организационной структуры

REST API на Django + Django REST Framework для управления организационной структурой компании: подразделения (дерево) и сотрудники.

## Стек

- Python 3.12
- Django 5
- Django REST Framework
- PostgreSQL 16
- Docker / Docker Compose

## Быстрый старт

```bash
docker compose up --build
```

API будет доступен по адресу: http://localhost:8000/

Интерактивная документация (Browsable API DRF): http://localhost:8000/departments/

## Эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/departments/` | Создать подразделение |
| GET | `/departments/{id}/` | Получить подразделение с сотрудниками и поддеревом |
| PATCH | `/departments/{id}/` | Обновить подразделение (имя / родитель) |
| DELETE | `/departments/{id}/` | Удалить подразделение |
| POST | `/departments/{id}/employees/` | Создать сотрудника в подразделении |

### Примеры

**Создать подразделение:**
```bash
curl -X POST http://localhost:8000/departments/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Engineering", "parent_id": null}'
```

**Создать сотрудника:**
```bash
curl -X POST http://localhost:8000/departments/1/employees/ \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Ivan Ivanov", "position": "Backend Developer"}'
```

**Получить подразделение с деревом (глубина 2):**
```bash
curl "http://localhost:8000/departments/1/?depth=2&include_employees=true"
```

**Удалить с каскадом:**
```bash
curl -X DELETE "http://localhost:8000/departments/1/?mode=cascade"
```

**Удалить с переносом сотрудников:**
```bash
curl -X DELETE "http://localhost:8000/departments/1/?mode=reassign&reassign_to_department_id=2"
```

## Структура проекта

```
├── config/              # настройки Django
├── departments/         # приложение: модели, API, бизнес-логика
│   ├── models.py        # Department, Employee
│   ├── serializers.py   # валидация входных данных
│   ├── services.py      # проверка циклов в дереве
│   ├── views.py         # API views
│   └── tests/           # тесты
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Запуск тестов

Локально (нужен PostgreSQL или SQLite через override):

```bash
pip install -r requirements.txt
python manage.py test
```

Через Docker:

```bash
docker compose run --rm web python manage.py test
```

## Бизнес-правила

- Название подразделения уникально в рамках одного родителя (1–200 символов, пробелы обрезаются).
- Нельзя создать цикл в дереве подразделений (ответ `409 Conflict`).
- При удалении `mode=cascade` — каскадное удаление через ORM (`on_delete=CASCADE`).
- При удалении `mode=reassign` — сотрудники переносятся в указанное подразделение, дочерние подразделения поднимаются на уровень выше.
