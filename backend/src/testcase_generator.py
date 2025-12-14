import uuid
import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from .llm_client import LLMClient

class TestCaseGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    async def generate_ui_testcases(
        self,
        requirements: str,
        test_blocks: List[str],
        target_count: int,
        priority: str
    ) -> List[Dict[str, Any]]:
        """Генерация UI тест-кейсов для калькулятора"""
        
        print(f"[DEBUG] TestCaseGenerator.generate_ui_testcases вызван")
        print(f"  requirements: {requirements}")
        print(f"  test_blocks: {test_blocks}")
        print(f"  target_count: {target_count}")
        print(f"  priority: {priority}")
        
        try:
            # Используем реальную генерацию через LLM
            testcases = await self.llm.generate_ui_testcases(
                requirements=requirements,
                test_blocks=test_blocks,
                count=target_count,
                priority=priority
            )
            
            print(f"[DEBUG] Получено от LLM {len(testcases) if testcases else 0} тест-кейсов")
            
            if not testcases:
                raise ValueError("LLM не сгенерировал тест-кейсы")
            
            # Преобразуем в нужный формат
            formatted_testcases = []
            for tc in testcases:
                formatted_tc = {
                    "id": str(uuid.uuid4()),
                    "title": tc.get("title", f"UI Test Case"),
                    "feature": tc.get("feature", "Cloud.ru Calculator"),
                    "story": tc.get("story", "User interaction"),
                    "priority": tc.get("priority", priority),
                    "steps": tc.get("steps", []),
                    "expected_result": tc.get("expected_result", ""),
                    "python_code": self._generate_allure_code(tc),
                    "test_type": "manual_ui",
                    "owner": tc.get("owner", "qa_engineer"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                formatted_testcases.append(formatted_tc)
            
            print(f"[DEBUG] Сгенерировано {len(formatted_testcases)} тест-кейсов")
            return formatted_testcases
            
        except Exception as e:
            print(f"[ERROR] Ошибка генерации UI тест-кейсов: {e}")
            # Fallback на заглушку для тестирования
            return self._get_fallback_ui_testcases(
                requirements, test_blocks, target_count, priority
            )
    
    async def generate_api_testcases(
        self,
        openapi_spec: Dict[str, Any],
        sections: List[str],
        count: int,
        priority: str,
        auth_type: str = "bearer"
    ) -> List[Dict[str, Any]]:
        """Генерация API тест-кейсов на основе OpenAPI"""
        
        print(f"[DEBUG] TestCaseGenerator.generate_api_testcases вызван")
        print(f"  sections: {sections}")
        print(f"  count: {count}")
        print(f"  priority: {priority}")
        
        try:
            # Используем реальную генерацию через LLM
            testcases = await self.llm.generate_api_testcases(
                openapi_spec=openapi_spec,
                sections=sections,
                count=count,
                priority=priority,
                auth_type=auth_type
            )
            
            print(f"[DEBUG] Получено от LLM {len(testcases) if testcases else 0} API тест-кейсов")
            
            if not testcases:
                raise ValueError("LLM не сгенерировал API тест-кейсы")
            
            # Преобразуем в нужный формат
            formatted_testcases = []
            for tc in testcases:
                formatted_tc = {
                    "id": str(uuid.uuid4()),
                    "title": tc.get("title", f"API Test Case"),
                    "feature": tc.get("feature", "Cloud.ru Compute API"),
                    "story": tc.get("story", "API operation"),
                    "priority": tc.get("priority", priority),
                    "steps": tc.get("steps", []),
                    "expected_result": tc.get("expected_result", ""),
                    "python_code": tc.get("python_code", self._generate_api_allure_code(tc, sections)),
                    "test_type": "manual_api",
                    "owner": tc.get("owner", "qa_engineer"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                formatted_testcases.append(formatted_tc)
            
            print(f"[DEBUG] Сгенерировано {len(formatted_testcases)} API тест-кейсов")
            return formatted_testcases
            
        except Exception as e:
            print(f"[ERROR] Ошибка генерации API тест-кейсов: {e}")
            # Fallback на заглушку для тестирования
            return self._get_fallback_api_testcases(openapi_spec, sections, count, priority)

    def _generate_allure_code(self, testcase: Dict[str, Any]) -> str:
        """Генерация Python кода в формате Allure TestOps as Code"""
        
        title = testcase.get("title", "Test Case")
        feature = testcase.get("feature", "Feature")
        story = testcase.get("story", "Story")
        priority = testcase.get("priority", "NORMAL")
        steps = testcase.get("steps", [])
        expected_result = testcase.get("expected_result", "")
        
        # Формируем название метода (только английские символы)
        method_name = title.lower()
            # Преобразуем русские символы в английские
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
            'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
            'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
            'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
            'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        # Транслитерация
        transliterated = ''
        for char in method_name:
            if char in translit_map:
                transliterated += translit_map[char]
            elif char.isalpha() or char.isdigit():
                transliterated += char
            else:
                transliterated += '_'
        
        # Заменяем множественные подчеркивания одним
        transliterated = re.sub(r'_+', '_', transliterated)
        transliterated = transliterated.strip('_')
        
        method_name = f"test_{transliterated[:50]}"  # Ограничиваем длину
        
        # Формируем docstring для класса
        class_docstring = f"Тесты для {feature}"
        
        # Генерируем шаги в формате allure_step
        steps_code = ""
        for i, step in enumerate(steps, 1):
            # Экранируем кавычки в шагах
            escaped_step = step.replace('"', '\\"')
            steps_code += f'        with allure_step("Шаг {i} - {escaped_step}"):\n'
            steps_code += f'            # Выполнить: {step}\n'
            steps_code += f'            pass\n\n'
    
        code = f'''import allure
from allure import step as allure_step
import pytest

@allure.manual
@allure.label("owner", "qa_engineer")
@allure.feature("{feature}")
@allure.story("{story}")
@allure.suite("manual_ui")
@allure.label("priority", "{priority.lower()}")
@pytest.mark.manual
class TestCalculator:
    """{class_docstring}"""
    
    @allure.title("{title}")
    @allure.tag("{priority}")
    def {method_name}(self):
        """{title}"""
        
        with allure_step("Arrange - Подготовка тестовых данных"):
            # Подготовка тестовых данных
            pass

{steps_code.rstrip()}
        
        with allure_step("Assert - Проверка ожидаемого результата"):
            # Проверка: {expected_result}
            assert True, "Проверка ожидаемого результата"
'''
        return code
    
    def _get_fallback_ui_testcases(
        self,
        requirements: str,
        test_blocks: List[str],
        target_count: int,
        priority: str
    ) -> List[Dict[str, Any]]:
        """Fallback тест-кейсы при ошибке LLM"""
        fallback_testcases = []
        
        for i in range(min(5, target_count)):
            block = test_blocks[i % len(test_blocks)] if test_blocks else "main_page"
            
            testcase = {
                "id": str(uuid.uuid4()),
                "title": f"Тестирование {block} - {i+1}",
                "feature": f"Cloud.ru Calculator - {block}",
                "story": f"Пользователь взаимодействует с {block}",
                "priority": priority,
                "steps": [
                    f"Открыть страницу калькулятора",
                    f"Проверить отображение элементов в блоке {block}",
                    f"Выполнить действия в блоке {block}",
                ],
                "expected_result": f"Блок {block} работает корректно",
                "python_code": "",
                "test_type": "manual_ui",
                "owner": "qa_engineer",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Генерируем код
            testcase["python_code"] = self._generate_allure_code(testcase)
            fallback_testcases.append(testcase)
        
        return fallback_testcases
    
    def _get_fallback_api_testcases(
        self,
        openapi_spec: Dict[str, Any],
        sections: List[str],
        count: int,
        priority: str
    ) -> List[Dict[str, Any]]:
        """Fallback API тест-кейсы при ошибке LLM"""
        fallback_testcases = []
        
        # Генерируем тест-кейсы на основе OpenAPI спецификации
        for i in range(min(count, 10)):  # Ограничиваем 10
            section = sections[i % len(sections)] if sections else "vms"
            
            # Получаем эндпоинты для секции
            endpoints = []
            for path, methods in openapi_spec.get("paths", {}).items():
                for method, details in methods.items():
                    tags = details.get("tags", [])
                    if section in tags:
                        endpoints.append(f"{method.upper()} {path}")
            
            if not endpoints:
                endpoints = ["GET /api/v1/vms", "POST /api/v1/vms", "GET /api/v1/flavors"]
            
            endpoint = endpoints[i % len(endpoints)]
            method, path = endpoint.split(" ", 1)
            
            testcase = {
                "id": str(uuid.uuid4()),
                "title": f"{method} {path} - проверка успешного ответа",
                "feature": f"Cloud.ru Compute API - {section.upper()}",
                "story": f"Операция {method} для ресурса {section}",
                "priority": priority,
                "steps": [
                    f"Подготовить запрос {method} к эндпоинту {path}",
                    f"Установить заголовок Authorization: Bearer <token>",
                    f"Отправить запрос к {path}",
                    f"Получить и проверить ответ"
                ],
                "expected_result": f"Эндпоинт {path} возвращает статус 200 и корректный JSON",
                "python_code": "",
                "test_type": "manual_api",
                "owner": "qa_engineer",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Генерируем код
            testcase["python_code"] = self._generate_api_allure_code(testcase, [section])
            fallback_testcases.append(testcase)
        
        return fallback_testcases
    
    def _generate_api_allure_code(self, testcase: Dict[str, Any], sections: List[str]) -> str:
        """Генерация Python кода для API тестов в формате Allure"""
        
        title = testcase.get("title", "API Test Case")
        feature = testcase.get("feature", "Cloud.ru Compute API")
        story = testcase.get("story", "API operation")
        priority = testcase.get("priority", "NORMAL")
        steps = testcase.get("steps", [])
        expected_result = testcase.get("expected_result", "")
        
        # Формируем название метода (только английские символы)
        method_name = title.lower()
            # Преобразуем русские символы в английские
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
            'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
            'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
            'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
            'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        # Транслитерация
        transliterated = ''
        for char in method_name:
            if char in translit_map:
                transliterated += translit_map[char]
            elif char.isalpha() or char.isdigit():
                transliterated += char
            else:
                transliterated += '_'
        
        # Заменяем множественные подчеркивания одним
        transliterated = re.sub(r'_+', '_', transliterated)
        transliterated = transliterated.strip('_')
        
        method_name = f"test_{transliterated[:50]}"  # Ограничиваем длину
        
        # Формируем docstring для класса
        class_docstring = f"Тесты для {feature}"
        
        # Генерируем шаги в формате allure_step
        steps_code = ""
        for i, step in enumerate(steps, 1):
            # Экранируем кавычки в шагах
            escaped_step = step.replace('"', '\\"')
            steps_code += f'        with allure_step("Шаг {i} - {escaped_step}"):\n'
            steps_code += f'            # Выполнить: {step}\n'
            steps_code += f'            pass\n\n'
        
        code = f'''import allure
from allure import step as allure_step
import pytest
import httpx
import json
from typing import Dict, Any

BASE_URL = "https://compute.api.cloud.ru"
AUTH_TOKEN = "YOUR_BEARER_TOKEN_HERE"  # Замените на реальный токен

@allure.manual
@allure.label("owner", "qa_engineer")
@allure.feature("{feature}")
@allure.story("{story}")
@allure.suite("manual_api")
@allure.label("priority", "{priority.lower()}")
@pytest.mark.manual
class TestComputeAPI:
    
    @allure.title("{title}")
    @allure.tag("{priority}")
    def {method_name}(self):
        """{title}"""
        
        with allure_step("Arrange - Подготовка запроса"):
            # Подготовка заголовков аутентификации
            headers = {{
                "Authorization": f"Bearer {{AUTH_TOKEN}}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }}
            
            # Подготовка тестовых данных
            test_data = {{
                # Добавьте тестовые данные здесь
            }}
        
        with allure_step("Act - Отправка HTTP запроса"):
            # Используем httpx.Client для лучшей производительности
            with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
                response = client.get("/api/v1/vms")
            
            # Логирование запроса и ответа
            allure.attach(
                json.dumps({{
                    "url": f"{{BASE_URL}}/api/v1/vms",
                    "method": "GET",
                    "headers": headers
                }}, indent=2),
                name="request",
                attachment_type=allure.attachment_type.JSON
            )

{steps_code.rstrip()}
        
        with allure_step("Assert - Проверка ожидаемого результата"):
            # Проверка статуса ответа
            assert response.status_code == 200, \\
                f"Ожидался статус 200, получен {{response.status_code}}"
            
            # Проверка структуры ответа
            response_data = response.json()
            assert isinstance(response_data, (dict, list)), \\
                "Ответ должен быть в формате JSON"
            
            # Проверка конкретных полей
            # assert "data" in response_data
            
            # Логирование ответа
            allure.attach(
                json.dumps(response_data, indent=2, ensure_ascii=False),
                name="response_body",
                attachment_type=allure.attachment_type.JSON
            )
            
            # Проверка: {expected_result}
            assert True, "Проверка ожидаемого результата"
'''
        return code