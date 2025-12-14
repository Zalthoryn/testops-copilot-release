"""
Базовый шаблон для pytest API тестов
Автоматически сгенерирован TestOps Copilot
"""

import pytest
import allure
import httpx
import json
from typing import Dict, Any, Optional, Generator
import os
from datetime import datetime


# ============================================================================
# CONFIGURATION
# ============================================================================

class APIConfig:
    """Конфигурация для API тестов"""
    
    BASE_URL = os.getenv("API_BASE_URL", "https://compute.api.cloud.ru")
    API_TOKEN = os.getenv("API_TOKEN", "")
    TIMEOUT = 30.0
    
    # Headers
    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    @classmethod
    def get_auth_headers(cls) -> Dict[str, str]:
        """Получение headers с авторизацией"""
        headers = cls.DEFAULT_HEADERS.copy()
        if cls.API_TOKEN:
            headers["Authorization"] = f"Bearer {cls.API_TOKEN}"
        return headers


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def api_client() -> Generator[httpx.AsyncClient, None, None]:
    """
    Сессионный API клиент
    Переиспользуется между тестами для производительности
    """
    client = httpx.AsyncClient(
        base_url=APIConfig.BASE_URL,
        headers=APIConfig.get_auth_headers(),
        timeout=APIConfig.TIMEOUT,
        verify=True  # SSL verification
    )
    
    yield client
    
    # Cleanup
    client.aclose()


@pytest.fixture(scope="function")
async def authenticated_client() -> Generator[httpx.AsyncClient, None, None]:
    """
    API клиент с аутентификацией для каждого теста
    """
    async with httpx.AsyncClient(
        base_url=APIConfig.BASE_URL,
        headers=APIConfig.get_auth_headers(),
        timeout=APIConfig.TIMEOUT
    ) as client:
        yield client


# ============================================================================
# BASE API CLIENT CLASS
# ============================================================================

class BaseAPIClient:
    """Базовый класс для работы с API"""
    
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.headers = APIConfig.DEFAULT_HEADERS.copy()
        
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        expected_status: int = 200
    ) -> httpx.Response:
        """
        Базовый метод для выполнения HTTP запросов
        
        Args:
            method: HTTP метод (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (например, /v3/vms)
            data: Тело запроса (для POST, PUT)
            params: Query параметры
            expected_status: Ожидаемый статус код
            
        Returns:
            httpx.Response объект
        """
        url = f"{self.base_url}{endpoint}"
        
        with allure.step(f"{method} {endpoint}"):
            async with httpx.AsyncClient() as client:
                # Логируем запрос
                allure.attach(
                    json.dumps({
                        "method": method,
                        "url": url,
                        "headers": self.headers,
                        "params": params,
                        "data": data
                    }, indent=2),
                    name="Request",
                    attachment_type=allure.attachment_type.JSON
                )
                
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params,
                    timeout=APIConfig.TIMEOUT
                )
                
                # Логируем ответ
                allure.attach(
                    json.dumps({
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": response.json() if response.text else None
                    }, indent=2),
                    name="Response",
                    attachment_type=allure.attachment_type.JSON
                )
                
                # Проверяем статус код
                with allure.step(f"Проверяем статус код: {expected_status}"):
                    assert response.status_code == expected_status, \
                        f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"
                
                return response
    
    async def get(self, endpoint: str, params: Optional[Dict] = None, expected_status: int = 200):
        """GET запрос"""
        return await self.request("GET", endpoint, params=params, expected_status=expected_status)
    
    async def post(self, endpoint: str, data: Dict, expected_status: int = 201):
        """POST запрос"""
        return await self.request("POST", endpoint, data=data, expected_status=expected_status)
    
    async def put(self, endpoint: str, data: Dict, expected_status: int = 200):
        """PUT запрос"""
        return await self.request("PUT", endpoint, data=data, expected_status=expected_status)
    
    async def delete(self, endpoint: str, expected_status: int = 204):
        """DELETE запрос"""
        return await self.request("DELETE", endpoint, expected_status=expected_status)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_json_schema(response_json: Dict, required_fields: list):
    """Валидация JSON схемы ответа"""
    with allure.step(f"Проверяем наличие обязательных полей: {required_fields}"):
        for field in required_fields:
            assert field in response_json, f"Поле '{field}' отсутствует в ответе"


def validate_uuid_format(uuid_string: str):
    """Проверка формата UUID"""
    import uuid
    with allure.step(f"Проверяем формат UUID: {uuid_string}"):
        try:
            uuid.UUID(uuid_string)
        except ValueError:
            pytest.fail(f"Некорректный формат UUID: {uuid_string}")


def validate_datetime_format(datetime_string: str):
    """Проверка формата даты-времени ISO 8601"""
    with allure.step(f"Проверяем формат даты-времени: {datetime_string}"):
        try:
            datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Некорректный формат даты: {datetime_string}")


# ============================================================================
# EXAMPLE TEST CLASS (ЗАМЕНИТЬ НА РЕАЛЬНЫЕ ТЕСТЫ)
# ============================================================================

@allure.feature("Virtual Machines API")
@allure.story("VMs CRUD Operations")
class TestVirtualMachines:
    """Тесты для работы с виртуальными машинами через API"""
    
    @allure.title("Получение списка виртуальных машин")
    @allure.tag("CRITICAL", "smoke")
    @allure.label("priority", "CRITICAL")
    @pytest.mark.asyncio
    async def test_get_vms_list(self, authenticated_client: httpx.AsyncClient):
        """
        Проверка получения списка виртуальных машин
        
        Arrange: Подготовка API клиента с аутентификацией
        Act: Выполнение GET запроса /v3/vms
        Assert: Проверка статус кода 200 и структуры ответа
        """
        with allure.step("Отправляем GET запрос на /v3/vms"):
            response = await authenticated_client.get("/v3/vms")
        
        with allure.step("Проверяем статус код 200"):
            assert response.status_code == 200
        
        with allure.step("Проверяем структуру JSON ответа"):
            data = response.json()
            assert isinstance(data, list), "Ответ должен быть массивом"
            
            if data:  # Если есть ВМ
                first_vm = data[0]
                required_fields = ["id", "name", "status", "flavor_id"]
                validate_json_schema(first_vm, required_fields)
                validate_uuid_format(first_vm["id"])
        
        with allure.step("Логируем количество ВМ"):
            allure.attach(
                f"Найдено виртуальных машин: {len(data)}",
                name="VMs Count",
                attachment_type=allure.attachment_type.TEXT
            )
    
    @allure.title("Создание виртуальной машины")
    @allure.tag("HIGH", "regression")
    @allure.label("priority", "HIGH")
    @pytest.mark.asyncio
    async def test_create_vm(self, authenticated_client: httpx.AsyncClient):
        """
        Проверка создания новой виртуальной машины
        
        Arrange: Подготовка данных для создания ВМ
        Act: Выполнение POST запроса /v3/vms
        Assert: Проверка статус кода 201 и созданной ВМ
        """
        vm_data = {
            "name": f"test-vm-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "flavor_id": "standard-2-4",  # 2 CPU, 4GB RAM
            "image_id": "ubuntu-22.04",
            "keypair_name": "my-keypair",
            "network_id": "default-network"
        }
        
        with allure.step("Подготавливаем данные для создания ВМ"):
            allure.attach(
                json.dumps(vm_data, indent=2),
                name="VM Creation Data",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Отправляем POST запрос на /v3/vms"):
            response = await authenticated_client.post("/v3/vms", json=vm_data)
        
        with allure.step("Проверяем статус код 201 Created"):
            assert response.status_code == 201
        
        with allure.step("Проверяем созданную ВМ"):
            created_vm = response.json()
            
            # Валидация обязательных полей
            required_fields = ["id", "name", "status", "created_at"]
            validate_json_schema(created_vm, required_fields)
            
            # Проверяем, что имя совпадает
            assert created_vm["name"] == vm_data["name"]
            
            # Проверяем формат UUID
            validate_uuid_format(created_vm["id"])
            
            # Проверяем формат даты создания
            validate_datetime_format(created_vm["created_at"])
        
        # Cleanup: удаляем созданную ВМ (опционально)
        vm_id = created_vm["id"]
        with allure.step(f"Удаляем тестовую ВМ {vm_id}"):
            delete_response = await authenticated_client.delete(f"/v3/vms/{vm_id}")
            assert delete_response.status_code in [204, 202]


@allure.feature("Disks API")
@allure.story("Disks Management")
class TestDisks:
    """Тесты для работы с дисками через API"""
    
    @allure.title("Получение списка дисков")
    @allure.tag("NORMAL", "smoke")
    @allure.label("priority", "NORMAL")
    @pytest.mark.asyncio
    async def test_get_disks_list(self):
        """Проверка получения списка дисков"""
        client = BaseAPIClient(APIConfig.BASE_URL, APIConfig.API_TOKEN)
        
        with allure.step("Получаем список дисков"):
            response = await client.get("/v3/disks", expected_status=200)
        
        with allure.step("Проверяем ответ"):
            data = response.json()
            assert isinstance(data, list)


@allure.feature("Flavors API")
@allure.story("Flavors Information")
class TestFlavors:
    """Тесты для получения информации о флейворах"""
    
    @allure.title("Получение списка доступных флейворов")
    @allure.tag("CRITICAL", "smoke")
    @allure.label("priority", "CRITICAL")
    @pytest.mark.asyncio
    async def test_get_flavors(self):
        """Проверка получения списка доступных конфигураций (флейворов)"""
        client = BaseAPIClient(APIConfig.BASE_URL, APIConfig.API_TOKEN)
        
        with allure.step("Получаем список флейворов"):
            response = await client.get("/v3/flavors", expected_status=200)
        
        with allure.step("Проверяем структуру ответа"):
            data = response.json()
            assert isinstance(data, list)
            
            if data:
                flavor = data[0]
                required_fields = ["id", "name", "vcpus", "ram", "disk"]
                validate_json_schema(flavor, required_fields)


# ============================================================================
# PYTEST MARKERS
# ============================================================================

"""
Используйте маркеры для категоризации тестов:

@pytest.mark.smoke      - Дымовые тесты (критичные, быстрые)
@pytest.mark.regression - Регрессионные тесты
@pytest.mark.integration - Интеграционные тесты
@pytest.mark.slow       - Медленные тесты
@pytest.mark.asyncio    - Асинхронные тесты (обязательно для async функций)
"""


# ============================================================================
# INSTRUCTIONS FOR USAGE
# ============================================================================

"""
ИСПОЛЬЗОВАНИЕ ЭТОГО ШАБЛОНА:

1. Установите зависимости:
   pip install pytest httpx allure-pytest pytest-asyncio

2. Настройте переменные окружения:
   export API_BASE_URL="https://compute.api.cloud.ru"
   export API_TOKEN="your_token_here"

3. Запуск тестов:
   pytest test_api.py                              # Все тесты
   pytest test_api.py -m smoke                     # Только smoke тесты
   pytest test_api.py -v                           # С подробным выводом
   pytest test_api.py --alluredir=allure-results  # С Allure отчетами

4. Генерация Allure отчета:
   allure serve allure-results

5. Параллельный запуск:
   pytest test_api.py -n 4  # 4 воркера (нужен pytest-xdist)

СТРУКТУРА ТЕСТА (AAA Pattern):

@pytest.mark.asyncio
async def test_example(self, authenticated_client):
    # ARRANGE - Подготовка
    with allure.step("Подготовка данных"):
        test_data = {"key": "value"}
    
    # ACT - Действие  
    with allure.step("Выполнение запроса"):
        response = await authenticated_client.post("/endpoint", json=test_data)
    
    # ASSERT - Проверка
    with allure.step("Проверка результата"):
        assert response.status_code == 201
        assert response.json()["key"] == "value"

BEST PRACTICES:

1. Всегда используйте with allure.step() для структурирования тестов
2. Логируйте request/response через allure.attach()
3. Используйте фикстуры для переиспользования кода
4. Очищайте тестовые данные после тестов (cleanup)
5. Используйте async/await для параллельного выполнения
6. Валидируйте JSON схемы и форматы данных
7. Используйте pytest.mark для категоризации тестов
"""
