import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from .llm_client import LLMClient
from .openapi_parser import OpenAPIParser

class AutotestGenerator:
    """Генератор автоматизированных тестов (UI - Playwright, API - pytest)"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.base_playwright_template = self._load_playwright_template()
        self.base_pytest_template = self._load_pytest_template()

    async def generate_ui_tests(
        self,
        manual_testcases_ids: List[str],
        framework: str = "playwright",
        browsers: List[str] = None,
        base_url: str = "https://cloud.ru/calculator",
        headless: bool = True,
        priority_filter: List[str] = None
    ) -> List[Dict[str, Any]]:

        print(f"[DEBUG] generate_ui_tests вызван для {len(manual_testcases_ids)} тест-кейсов") # Отладка

        """
        Генерация UI e2e тестов на основе ручных тест-кейсов
        """
        if browsers is None:
            browsers = ["chromium"]
        if priority_filter is None:
            priority_filter = ["CRITICAL", "NORMAL"]

        # В реальном проекте здесь был бы запрос к БД/стораджу для получения кейсов по IDs
        # Для примера сгенерируем тесты через LLM
        prompt = f"""Сгенерируй автоматизированные UI тесты на Playwright для калькулятора Cloud.ru.

Требования:
- Базовый URL: {base_url}
- Браузеры: {', '.join(browsers)}
- Headless режим: {headless}
- Приоритеты для тестирования: {', '.join(priority_filter)}

Сгенерируй 3-5 критических тестов для следующих сценариев:
1. Открытие главной страницы и проверка основных элементов
2. Добавление сервиса Compute в конфигурацию
3. Изменение параметров конфигурации (CPU, RAM)
4. Расчет стоимости и проверка отображения цены
5. Тест мобильной версии (viewport)

Формат каждого теста в JSON:
{{
    "id": "uuid",
    "title": "Название теста",
    "description": "Описание",
    "priority": "CRITICAL|NORMAL|LOW",
    "code": "Python код на Playwright",
    "tags": ["tag1", "tag2"],
    "metadata": {{"browser": "chromium", "viewport": "desktop"}}
}}

Код должен следовать паттерну AAA и использовать фикстуры pytest."""

        try:
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "Ты генерируешь автоматизированные UI тесты на Playwright."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            tests = self._parse_llm_response(content)
            
            # Добавляем метаданные и форматируем код
            for test in tests:
                test["id"] = str(uuid.uuid4())
                test["type"] = "auto_ui"
                test["framework"] = framework
                test["generated_at"] = datetime.now(timezone.utc).isoformat()
                test["code"] = self._wrap_playwright_code(
                    test.get("code", ""),
                    base_url=base_url,
                    browsers=browsers,
                    headless=headless
                )
            
            return tests
            
        except Exception as e:
            raise Exception(f"Ошибка генерации UI тестов: {str(e)}")

    async def generate_api_tests(
        self,
        manual_testcases_ids: List[str],
        openapi_url: Optional[str] = None,
        sections: List[str] = None,
        base_url: str = "https://compute.api.cloud.ru",
        auth_token: Optional[str] = None,
        test_framework: str = "pytest",
        http_client: str = "httpx"
    ) -> List[Dict[str, Any]]:
        """
        Генерация API тестов на основе OpenAPI спецификации
        """
        if sections is None:
            sections = ["vms", "disks", "flavors"]

        try:
            # Парсинг OpenAPI спецификации
            parser = OpenAPIParser()
            spec = {}
            if openapi_url:
                spec = await parser.parse_from_url(openapi_url)
            
            # Генерация тестов через LLM
            prompt = self._build_api_test_prompt(spec, sections, base_url, auth_token)
            
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "Ты генерируешь автоматизированные API тесты на pytest."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=5000,
                temperature=0.6
            )
            
            content = response.choices[0].message.content
            tests = self._parse_llm_response(content)
            
            # Обработка и форматирование
            for test in tests:
                test["id"] = str(uuid.uuid4())
                test["type"] = "auto_api"
                test["framework"] = test_framework
                test["generated_at"] = datetime.now(timezone.utc).isoformat()
                test["code"] = self._wrap_pytest_code(
                    test.get("code", ""),
                    base_url=base_url,
                    auth_token=auth_token,
                    http_client=http_client
                )
            
            return tests
            
        except Exception as e:
            raise Exception(f"Ошибка генерации API тестов: {str(e)}")

    def _load_playwright_template(self) -> str:
        """Загрузка шаблона для Playwright тестов"""
        return """import pytest
import allure
from playwright.sync_api import Page, expect
import re

@pytest.fixture(scope="function")
def page(context):
    page = context.new_page()
    yield page
    page.close()

@pytest.fixture(scope="session")
def browser(browser_type, launch_browser):
    browser = launch_browser.launch(headless={headless})
    yield browser
    browser.close()

@pytest.fixture(scope="session")
def context(browser):
    context = browser.new_context(viewport={{'width': 1920, 'height': 1080}})
    yield context
    context.close()

@allure.parent_suite("UI Autotests")
@allure.suite("Cloud.ru Calculator")
"""

    def _load_pytest_template(self) -> str:
        """Загрузка шаблона для pytest API тестов"""
        return """import pytest
import allure
import {http_client}
import json
from typing import Dict, Any

BASE_URL = "{base_url}"
AUTH_TOKEN = "{auth_token}"

@pytest.fixture(scope="session")
def api_client():
    headers = {{
        "Content-Type": "application/json"
    }}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {{AUTH_TOKEN}}"
    
    client = {http_client}.Client(
        base_url=BASE_URL,
        headers=headers,
        timeout=30.0
    )
    yield client
    client.close()

@allure.parent_suite("API Autotests")
@allure.suite("Cloud.ru Compute API")
"""

    def _wrap_playwright_code(self, code: str, **kwargs) -> str:
        """Обертывание кода в Playwright шаблон"""
        template = self.base_playwright_template.format(**kwargs)
        return template + "\n\n" + code

    def _wrap_pytest_code(self, code: str, **kwargs) -> str:
        """Обертывание кода в pytest шаблон"""
        template = self.base_pytest_template.format(**kwargs)
        return template + "\n\n" + code

    def _parse_llm_response(self, content: str) -> List[Dict[str, Any]]:
        """Парсинг JSON ответа от LLM"""
        try:
            # Извлечение JSON из markdown
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Fallback: возвращаем примерные тесты
            return self._get_fallback_tests()

    def _build_api_test_prompt(self, spec: Dict, sections: List[str], 
                               base_url: str, auth_token: Optional[str]) -> str:
        """Построение промпта для API тестов"""
        endpoints = []
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                tags = details.get("tags", [])
                if any(section in tags for section in sections):
                    endpoints.append(f"{method.upper()} {path}")
        
        return f"""Сгенерируй автоматизированные API тесты для Cloud.ru Compute.

Базовый URL: {base_url}
Секции для тестирования: {', '.join(sections)}
Аутентификация: {'Bearer token' if auth_token else 'None'}

Доступные эндпоинты (первые 10):
{chr(10).join(endpoints[:10])}

Сгенерируй 5-7 тестов, покрывающих:
1. Успешные CRUD операции для VMs
2. Обработку ошибок (404, 422, 403)
3. Пагинацию и фильтрацию
4. Валидацию входных данных
5. Работу с дисками и флейворами

Формат каждого теста:
{{
    "id": "uuid",
    "title": "Название теста",
    "description": "Описание",
    "priority": "CRITICAL|NORMAL|LOW",
    "code": "Python код на pytest с httpx",
    "tags": ["api", "vms", "crud"],
    "metadata": {{"method": "GET", "endpoint": "/api/v1/vms"}}
}}

Код должен использовать паттерн AAA и корректно обрабатывать ошибки."""

    def _get_fallback_tests(self) -> List[Dict[str, Any]]:
        """Fallback тесты при ошибке парсинга LLM"""
        return [
            {
                "title": "Get flavors list - успешный запрос",
                "description": "Получение списка доступных флейворов",
                "priority": "CRITICAL",
                "code": """
@pytest.mark.vms
@allure.title("Получение списка флейворов")
def test_get_flavors(api_client):
    # Arrange
    endpoint = "/api/v1/flavors"
    
    # Act
    response = api_client.get(endpoint)
    
    # Assert
    assert response.status_code == 200
    assert "items" in response.json()
    assert isinstance(response.json()["items"], list)""",
                "tags": ["api", "flavors", "get"],
                "metadata": {"method": "GET", "endpoint": "/api/v1/flavors"}
            }
        ]