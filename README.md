# TestOps Copilot

AI-ассистент для автоматизации рутинной работы QA-инженера. Генерирует тест-кейсы и автотесты на основе Cloud.ru Evolution Foundation Model.

## Что это делает

Проект решает задачу автоматизации тестирования через AI. Вместо того, чтобы вручную писать десятки тест-кейсов и тестов, система:

- **Генерирует ручные тест-кейсы** в формате Allure TestOps as Code — просто скармливаете ей требования или OpenAPI спецификацию
- **Создаёт автотесты** на Playwright (для UI) и pytest (для API) — не просто болванки, а полноценный код с AAA-паттерном
- **Проверяет на стандарты** — следит, чтобы тесты были структурированы правильно, со всеми декораторами Allure
- **Оптимизирует** — находит дубликаты, пробелы в покрытии, устаревшие тесты

Протестирован на двух реальных кейсах:
1. UI-тестирование калькулятора цен Cloud.ru (https://cloud.ru/calculator)
2. API-тестирование Evolution Compute (виртуальные машины, диски, флейворы)

## Архитектура

```
┌─────────────────┐
│  React Frontend │  ← Vite, TypeScript, Monaco Editor
│  (port 5173)    │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  FastAPI Backend│  ← Python 3.11, async/await
│  (port 8000)    │
└────────┬────────┘
         │
    ┌────┴──────────────┐
    │                   │
    ▼                   ▼
┌────────┐      ┌──────────────┐
│  Redis │      │  Cloud.ru    │
│ Storage│      │  Evolution   │
└────────┘      │  Model (LLM) │
                └──────────────┘
```

**Backend модули:**
- `testcase_generator.py` — ручные тест-кейсы (UI + API)
- `autotest_generator.py` — автотесты на Playwright/pytest
- `standards_checker.py` — валидация по стандартам Allure
- `optimizer.py` — анализ покрытия и оптимизация
- `llm_client.py` — обёртка над Cloud.ru API
- `openapi_parser.py` — парсинг OpenAPI 3.0 спецификаций
- `gitlab_integration.py` — коммит тестов в GitLab

**Frontend страницы:**
- Dashboard — статистика и быстрый старт
- Тест-кейсы — генерация ручных кейсов
- Автотесты — генерация автоматизированных тестов
- Стандарты — проверка на соответствие
- Оптимизация — анализ и улучшение
- Задачи (Jobs) — отслеживание генераций
- Настройки — конфиг LLM и интеграций

## Быстрый старт

### Требования

- Python 3.11+
- Node.js 18+
- Redis 5.0+
- Docker + docker-compose (опционально)

### Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# Cloud.ru Evolution Model
LLM_API_KEY=your_cloud_ru_api_key
LLM_API_BASE=https://api.evolution.cloud.ru/v1
LLM_MODEL=evolution-1.5-large

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# GitLab (опционально)
GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=your_gitlab_token

# Compute API (для демо)
COMPUTE_API_TOKEN=your_compute_token
COMPUTE_API_URL=https://compute.api.cloud.ru
```

### Вариант 1: Локальный запуск (для разработки)

**Шаг 1. Запустите Redis**
```bash
redis-server
```

**Шаг 2. Backend**
```bash
cd backend

# Установка зависимостей
pip install -r requirements.txt

# Запуск
python run.py
# или
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Backend поднимется на `http://localhost:8000`  
Swagger UI доступен по адресу `http://localhost:8000/docs`

**Шаг 3. Frontend**
```bash
cd frontend

# Установка зависимостей
npm install

# Запуск dev-сервера
npm run dev
```

Frontend откроется на `http://localhost:5173`

### Вариант 2: Docker (для продакшена или демо)

```bash
docker-compose up --build
```

Всё поднимется автоматически:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Redis: localhost:6379

## Как использовать

### 1. Генерация ручных тест-кейсов для UI

**Через UI:**
1. Откройте страницу "Тест-кейсы"
2. Выберите тип "UI тестирование"
3. Заполните:
   - Название проекта: "Cloud.ru Calculator"
   - Требования: вставьте описание функционала или пользовательские сценарии
   - Блоки тестирования: выберите из списка (Главная страница, Каталог, Конфигурация...)
   - Количество тестов: 15-35
   - Приоритет: CRITICAL/NORMAL/LOW
4. Жмите "Сгенерировать"
5. Через 20-40 секунд получите готовые тест-кейсы
6. Скачайте Python файл с тестами или закоммитьте в GitLab

**Через API:**
```bash
curl -X POST http://localhost:8000/api/testcases/manual/ui \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Cloud.ru Calculator",
    "requirements": "Калькулятор цен для облачных сервисов...",
    "test_blocks": ["Главная страница", "Каталог продуктов", "Конфигурация"],
    "target_count": 20,
    "priority": "CRITICAL",
    "owner": "qa-team",
    "include_screenshots": true
  }'
```

Ответ:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "estimated_time": 30
}
```

Проверить статус:
```bash
curl http://localhost:8000/api/testcases/123e4567-e89b-12d3-a456-426614174000
```

### 2. Генерация ручных тест-кейсов для API

**Через UI:**
1. Страница "Тест-кейсы" → тип "API тестирование"
2. Укажите OpenAPI спецификацию:
   - URL: `https://cloud.ru/docs/virtual-machines/openapi.yaml`
   - Или загрузите файл
3. Выберите разделы: VMs, Disks, Flavors
4. Количество: 15-35
5. Генерируйте

**Через API:**
```bash
curl -X POST http://localhost:8000/api/testcases/manual/api \
  -H "Content-Type: application/json" \
  -d '{
    "openapi_url": "https://compute.api.cloud.ru/openapi.yaml",
    "sections": ["VMs", "Disks", "Flavors"],
    "auth_type": "Bearer",
    "target_count": 25,
    "priority": "CRITICAL"
  }'
```

### 3. Генерация автоматизированных тестов

**UI автотесты (Playwright):**
```bash
curl -X POST http://localhost:8000/api/autotests/ui \
  -H "Content-Type: application/json" \
  -d '{
    "manual_testcases_ids": ["abc-123", "def-456"],
    "framework": "playwright",
    "browsers": ["chromium", "firefox"],
    "base_url": "https://cloud.ru/calculator",
    "headless": true,
    "priority_filter": ["CRITICAL", "NORMAL"]
  }'
```

**API автотесты (pytest):**
```bash
curl -X POST http://localhost:8000/api/autotests/api \
  -H "Content-Type: application/json" \
  -d '{
    "openapi_url": "https://compute.api.cloud.ru/openapi.yaml",
    "sections": ["VMs", "Disks"],
    "base_url": "https://compute.api.cloud.ru",
    "auth_type": "Bearer"
  }'
```

### 4. Проверка на стандарты

Загрузите существующие тест-кейсы для проверки:

```bash
curl -X POST http://localhost:8000/api/standards/check \
  -F "files=@test_calculator.py" \
  -F "files=@test_compute_api.py" \
  -F "checks=allure_decorators" \
  -F "checks=aaa_pattern" \
  -F "checks=naming_conventions"
```

Получите отчёт с нарушениями и рекомендациями.

### 5. Оптимизация тестов

```bash
curl -X POST http://localhost:8000/api/optimization/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://gitlab.com/company/tests.git",
    "checks": ["duplicates", "coverage", "obsolete"],
    "optimization_level": "moderate"
  }'
```

Система найдёт:
- Дублирующиеся тесты (одинаковые проверки)
- Пробелы в покрытии (что не покрыто)
- Устаревшие тесты (конфликтующие требования)

## Как проверять

### Ручная проверка генерации

1. **Откройте UI**: http://localhost:5173
2. **Сгенерируйте тест-кейсы** для калькулятора (UI) — должно получиться 15-35 кейсов за ~30 секунд
3. **Проверьте структуру кода**:
   ```python
   @allure.manual
   @allure.label("owner", "qa-team")
   @allure.feature("Calculator")
   @allure.story("Add Service")
   @allure.tag("CRITICAL")
   class TestCalculatorAddService:
       @allure.title("Проверка добавления Compute в конфигурацию")
       def test_add_compute_service(self):
           with allure.step("Открываем калькулятор"):
               pass
           with allure.step("Нажимаем 'Добавить сервис'"):
               pass
           ...
   ```

4. **Сгенерируйте API тесты** для Evolution Compute
5. **Проверьте автотест**:
   ```python
   @pytest.mark.asyncio
   async def test_get_vms_list(authenticated_client):
       # ARRANGE
       with allure.step("Подготовка клиента"):
           pass
       
       # ACT
       with allure.step("GET /v3/vms"):
           response = await authenticated_client.get("/v3/vms")
       
       # ASSERT
       with allure.step("Проверка статус кода"):
           assert response.status_code == 200
   ```

### Автоматические тесты

**Backend unit-тесты:**
```bash
cd backend
pytest src/test_functional.py -v
```

**Frontend тесты:**
```bash
cd frontend
npm run test
```

### Проверка интеграций

**1. LLM доступность:**
```bash
curl http://localhost:8000/api/config

# Должен вернуть:
{
  "llm_available": true,
  "llm_model": "evolution-1.5-large",
  "compute_endpoint": "https://compute.api.cloud.ru",
  ...
}
```

**2. Compute API (если настроен):**
```bash
curl http://localhost:8000/api/integrations/compute/validate

# Должен вернуть:
{
  "valid": true,
  "available_resources": ["vms", "disks", "flavors"]
}
```

**3. GitLab (если настроен):**
```bash
curl http://localhost:8000/api/integrations/gitlab/validate

# Должен вернуть статус подключения
```

### Stress-тест

Создайте несколько генераций параллельно:

```bash
# 5 параллельных запросов
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/testcases/manual/ui \
    -H "Content-Type: application/json" \
    -d '{...}' &
done
```

Проверьте Redis:
```bash
redis-cli
> KEYS "job:*"
> GET "job:123e4567-e89b-12d3-a456-426614174000"
```

### Метрики производительности

Измерьте время генерации:
- 1 тест-кейс: < 5 секунд
- 10 тест-кейсов: < 30 секунд
- 30 тест-кейсов: < 60 секунд

Использование памяти:
```bash
docker stats testops-copilot-backend
# Должно быть < 500MB в покое
```

## Структура генерируемых файлов

### Ручные тест-кейсы (manual test)

```python
# test_calculator_manual.py
import allure
from pytest import mark

@allure.manual
@allure.label("owner", "qa-team")
@allure.feature("Price Calculator")
@allure.story("Service Configuration")
@allure.suite("UI Testing")
@mark.manual
class TestCalculatorConfiguration:
    @allure.title("Проверка конфигурации Compute сервиса")
    @allure.tag("CRITICAL")
    @allure.label("priority", "CRITICAL")
    def test_configure_compute_service(self) -> None:
        with allure.step("Открыть калькулятор"):
            pass
        with allure.step("Добавить Compute сервис"):
            pass
        with allure.step("Выбрать конфигурацию: 4 CPU, 8GB RAM"):
            pass
        with allure.step("Проверить расчёт цены"):
            allure.attach.file(
                "screenshots/compute_price.png",
                name="Compute Price",
                attachment_type=allure.attachment_type.PNG
            )
```

### Автотесты UI (Playwright)

```python
# test_calculator_auto.py
import pytest
from playwright.async_api import Page, expect

@pytest.mark.asyncio
async def test_add_compute_service(page: Page):
    # ARRANGE
    await page.goto("https://cloud.ru/calculator")
    
    # ACT
    await page.click('button:has-text("Добавить сервис")')
    await page.click('text=Compute')
    
    # ASSERT
    await expect(page.locator('.service-card')).to_be_visible()
    await expect(page.locator('.price-display')).to_contain_text('₽')
```

### Автотесты API (pytest)

```python
# test_compute_api_auto.py
import pytest
import httpx
import allure

@pytest.mark.asyncio
async def test_create_vm(authenticated_client: httpx.AsyncClient):
    # ARRANGE
    vm_data = {
        "name": "test-vm",
        "flavor_id": "standard-2-4",
        "image_id": "ubuntu-22.04"
    }
    
    # ACT
    response = await authenticated_client.post("/v3/vms", json=vm_data)
    
    # ASSERT
    assert response.status_code == 201
    created_vm = response.json()
    assert created_vm["name"] == "test-vm"
    assert "id" in created_vm
```

## Troubleshooting

### Backend не стартует

**Проблема:** `ModuleNotFoundError: No module named 'fastapi'`  
**Решение:**
```bash
pip install -r requirements.txt
```

**Проблема:** `Connection refused to Redis`  
**Решение:**
```bash
# Проверьте, запущен ли Redis
redis-cli ping
# Должен вернуть: PONG

# Если нет, запустите:
redis-server
```

### LLM не отвечает

**Проблема:** `LLM API unavailable`  
**Решение:**
1. Проверьте `.env` — правильный ли API ключ?
2. Проверьте доступность:
   ```bash
   curl -H "Authorization: Bearer YOUR_KEY" \
     https://api.evolution.cloud.ru/v1/models
   ```
3. Проверьте квоты на Cloud.ru

### Frontend не коннектится к Backend

**Проблема:** `Network Error` или CORS  
**Решение:**
1. Проверьте, что backend запущен на 8000:
   ```bash
   curl http://localhost:8000/
   ```
2. Проверьте proxy в `vite.config.ts`:
   ```typescript
   proxy: {
     '/api': {
       target: 'http://localhost:8000',
       changeOrigin: true
     }
   }
   ```

### Генерация долго выполняется

**Проблема:** Генерация 10 тестов идёт > 2 минуты  
**Причины:**
- Медленная работа LLM API (проверьте регион, нагрузку)
- Слишком большой `max_tokens` в промптах
- Нет асинхронности в бэкенде

**Решение:**
- Уменьшите `temperature` в LLM запросах (0.5 вместо 0.7)
- Добавьте timeout в `llm_client.py`
- Используйте batch-генерацию вместо последовательной

## Production deployment

### С Docker

```bash
# Сборка
docker build -t testops-copilot-backend ./backend
docker build -t testops-copilot-frontend ./frontend

# Запуск с docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Без Docker

**Backend:**
```bash
cd backend
pip install -r requirements.txt
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

**Frontend:**
```bash
cd frontend
npm run build
# Статика будет в dist/
# Раздавайте через nginx или другой веб-сервер
```

**Nginx конфиг:**
```nginx
server {
    listen 80;
    server_name testops.example.com;

    # Frontend
    location / {
        root /var/www/testops-copilot/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Известные ограничения

- **LLM rate limits:** Cloud.ru может ограничивать количество запросов. Если превышаете лимит, получите 429 ошибку
- **Размер контекста:** OpenAPI спецификации > 100KB могут вызвать проблемы с токенами LLM
- **Redis память:** При большом количестве jobs (>1000) может потребоваться настройка `maxmemory` в Redis
- **GitLab API:** Ограничение на размер коммита — нельзя залить файл > 10MB
- **Генерация не идеальна:** ~80% кода требует минимальных правок, 20% нужно подправить вручную