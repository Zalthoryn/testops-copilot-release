import os
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx
from datetime import datetime, timezone

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "YTc5NDZhMTAtZjkwNi00OTlkLTgxM2QtOGNkZDUyYjAzOWY1.03eccda7c192ba2cbe8f5c94da06be64")
        self.base_url = os.getenv("LLM_BASE_URL", "https://foundation-models.api.cloud.ru/v1")
        self.model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

        # Проверка наличия API ключа
        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY не установлен. Убедитесь, что файл .env существует "
                "и содержит переменную LLM_API_KEY"
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def check_availability(self) -> bool:
        """Проверка доступности LLM"""
        
        print("Вызвана проверка доступности модели") # Отладка

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=100,
                presence_penalty=0,
                top_p=0.95,
                messages=[
                    {
                            "role": "user",
                            "content":"ping"
                    }
                ]
                )
            return response.choices[0].message.content is not None
        except Exception:
            return False
                
    def test_connection(self, api_key: Optional[str] = None, 
                    base_url: Optional[str] = None,
                    model: Optional[str] = None):
        """Тестирование подключения с возможностью переопределения ключа"""
        client = OpenAI(
            api_key=api_key or self.api_key,
            base_url=base_url or self.base_url
        )
        response = client.chat.completions.create(
            model=model or self.model,
            messages=[{"role": "user", "content": "Test connection"}],
            max_tokens=100
        )
        return {"success": True, "response": response.choices[0].message.content}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_ui_testcases(
        self,
        requirements: str,
        test_blocks: List[str],
        count: int = 5,
        priority: str = "NORMAL"
    ) -> List[Dict[str, Any]]:
        """Генерация UI тест-кейсов через LLM"""

        priority_str = priority.value if hasattr(priority, 'value') else priority

#        prompt = f"""Ты - опытный QA инженер. Сгенерируй тест-кейсы для UI калькулятора Cloud.ru.
        prompt = f"""Ты - опытный QA инженер. Сгенерируй тест-кейсы на основе следующих требований.

Требования: {requirements}
Блоки тестирования: {', '.join(test_blocks)}
Количество тест-кейсов: {count}
Приоритет: {priority_str}

Формат каждого тест-кейса в JSON:
{{
    "id": "uuid",
    "title": "Название тест-кейса",
    "feature": "Основная функциональность",
    "story": "User Story",
    "priority": "CRITICAL|NORMAL|LOW",
    "steps": ["шаг1", "шаг2"],
    "expected_result": "Ожидаемый результат",
    "python_code": "код в формате Allure TestOps as Code"
}}

Верни только JSON массив с тест-кейсами, без пояснений."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Ты генерируешь тест-кейсы в формате JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        # Извлекаем JSON из ответа
        try:
            # Пытаемся найти JSON между ```
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            testcases = json.loads(content)
            # Добавляем недостающие поля
            for i, tc in enumerate(testcases):
                tc.setdefault("id", f"tc_{datetime.now().timestamp()}_{i}")
                tc.setdefault("owner", "qa_engineer")
                tc.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                tc.setdefault("test_type", "manual_ui")
                
            return testcases
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга JSON от LLM: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_api_testcases(
        self,
        openapi_spec: Dict[str, Any],
        sections: List[str],
        count: int = 5,
        priority: str = "NORMAL",
        auth_type: str = "bearer"
    ) -> List[Dict[str, Any]]:
        """Генерация API тест-кейсов на основе OpenAPI спецификации"""
        
        # Фильтруем спецификацию по разделам
        filtered_paths = {}
        for path, methods in openapi_spec.get("paths", {}).items():
            for method, spec in methods.items():
                tags = spec.get("tags", [])
                if any(section in str(tags) for section in sections):
                    filtered_paths[f"{method.upper()} {path}"] = spec
        
        prompt = f"""Ты - опытный QA инженер API тестирования. Сгенерируй тест-кейсы для API Cloud.ru Compute.

Разделы для тестирования: {', '.join(sections)}
Количество тест-кейсов: {count}
Приоритет: {priority}
Тип аутентификации: {auth_type}

Доступные эндпоинты:
{json.dumps(list(filtered_paths.keys())[:20], indent=2)}

Формат каждого тест-кейса в JSON:
{{
    "id": "uuid",
    "title": "Название тест-кейса",
    "feature": "Основная функциональность",
    "story": "User Story",
    "priority": "CRITICAL|NORMAL|LOW",
    "steps": ["шаг1", "шаг2"],
    "expected_result": "Ожидаемый результат",
    "python_code": "код в формате Allure TestOps as Code с использованием AAA паттерна"
}}

Пример Python кода:
```python
@allure.manual
@allure.label("owner", "qa_engineer")
@allure.feature("VMs")
@allure.story("CRUD операций виртуальных машин")
@allure.suite("manual_api")
class TestVMCrud:
    @allure.title("Создание виртуальной машины")
    @allure.tag("CRITICAL")
    def test_create_vm(self):
        # Arrange
        vm_data = {{"name": "test-vm", "flavor_id": "..."}}
        # Act
        response = requests.post(f"{{BASE_URL}}/api/v1/vms", json=vm_data, headers=headers)
        # Assert
        assert response.status_code == 201
        assert response.json()["name"] == "test-vm"
```

Верни только JSON массив с тест-кейсами, без пояснений."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Ты генерируешь API тест-кейсы в формате JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=5000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            testcases = json.loads(content)
            for i, tc in enumerate(testcases):
                tc.setdefault("id", f"api_tc_{datetime.now().timestamp()}_{i}")
                tc.setdefault("owner", "qa_engineer")
                tc.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                tc.setdefault("test_type", "manual_api")
                
            return testcases
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга JSON от LLM: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def check_standards(
        self,
        code: str,
        checks: List[str]
    ) -> List[Dict[str, Any]]:
        """Проверка кода на соответствие стандартам"""
        
        checks_str = ", ".join(checks)
        prompt = f"""Проверь следующий тестовый код на соответствие стандартам QA.

Стандарты для проверки: {checks_str}

Код для проверки:
```python
{code}
```

Формат ответа в JSON:
{{
    "violations": [
        {{
            "file": "имя файла",
            "line": номер строки,
            "severity": "error|warning|info",
            "rule": "название правила",
            "message": "описание проблемы",
            "suggested_fix": "предлагаемое исправление"
        }}
    ]
}}

Если нарушений нет, верни пустой массив violations."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Ты проверяешь тестовый код на соответствие стандартам."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content)
            return result.get("violations", [])
        except json.JSONDecodeError:
            return []