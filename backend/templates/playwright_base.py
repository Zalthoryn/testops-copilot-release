"""
Базовый шаблон для Playwright UI тестов
Автоматически сгенерирован TestOps Copilot
"""

import pytest
import allure
from playwright.sync_api import Page, expect, Browser
from typing import Generator
import os


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Конфигурация браузера для всех тестов"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "locale": "ru-RU",
        "timezone_id": "Europe/Moscow",
    }


@pytest.fixture(scope="function")
def page(page: Page) -> Generator[Page, None, None]:
    """
    Базовая фикстура страницы с дополнительной настройкой
    Автоматически делает скриншоты при падении теста
    """
    # Увеличиваем таймауты для стабильности
    page.set_default_timeout(30000)  # 30 секунд
    page.set_default_navigation_timeout(30000)
    
    yield page
    
    # Cleanup: делаем скриншот если тест упал
    if hasattr(pytest, 'last_test_failed') and pytest.last_test_failed:
        screenshot_path = f"screenshots/failed_{pytest.last_test_name}.png"
        os.makedirs("screenshots", exist_ok=True)
        page.screenshot(path=screenshot_path)
        allure.attach.file(
            screenshot_path,
            name=f"Failed: {pytest.last_test_name}",
            attachment_type=allure.attachment_type.PNG
        )


# ============================================================================
# PAGE OBJECTS / HELPERS
# ============================================================================

class BasePage:
    """Базовый класс для Page Objects"""
    
    def __init__(self, page: Page):
        self.page = page
    
    def navigate(self, url: str):
        """Навигация на страницу с логированием"""
        with allure.step(f"Открываем URL: {url}"):
            self.page.goto(url)
            self.page.wait_for_load_state("networkidle")
    
    def click_element(self, selector: str, description: str = None):
        """Клик по элементу с явным ожиданием"""
        desc = description or f"Клик по элементу: {selector}"
        with allure.step(desc):
            element = self.page.locator(selector)
            element.wait_for(state="visible", timeout=10000)
            element.click()
    
    def fill_input(self, selector: str, value: str, description: str = None):
        """Заполнение поля ввода"""
        desc = description or f"Вводим '{value}' в поле {selector}"
        with allure.step(desc):
            element = self.page.locator(selector)
            element.wait_for(state="visible", timeout=10000)
            element.fill(value)
    
    def verify_text(self, selector: str, expected_text: str):
        """Проверка текста элемента"""
        with allure.step(f"Проверяем, что текст '{expected_text}' присутствует"):
            element = self.page.locator(selector)
            expect(element).to_contain_text(expected_text)
    
    def verify_element_visible(self, selector: str, description: str = None):
        """Проверка видимости элемента"""
        desc = description or f"Проверяем видимость элемента: {selector}"
        with allure.step(desc):
            element = self.page.locator(selector)
            expect(element).to_be_visible()
    
    def take_screenshot(self, name: str):
        """Снимок экрана с прикреплением к Allure"""
        with allure.step(f"Делаем скриншот: {name}"):
            screenshot_bytes = self.page.screenshot()
            allure.attach(
                screenshot_bytes,
                name=name,
                attachment_type=allure.attachment_type.PNG
            )


# ============================================================================
# EXAMPLE TEST CLASS (ЗАМЕНИТЬ НА РЕАЛЬНЫЕ ТЕСТЫ)
# ============================================================================

@allure.feature("Calculator")
@allure.story("Main Page")
class TestCalculatorMainPage:
    """Тесты главной страницы калькулятора"""
    
    BASE_URL = "https://cloud.ru/calculator"
    
    @allure.title("Открытие главной страницы калькулятора")
    @allure.tag("CRITICAL", "smoke")
    @allure.label("priority", "CRITICAL")
    @pytest.mark.smoke
    def test_open_main_page(self, page: Page):
        """
        Проверка открытия главной страницы калькулятора
        
        Arrange: Подготовка браузера
        Act: Открытие страницы
        Assert: Проверка загрузки страницы и основных элементов
        """
        base_page = BasePage(page)
        
        with allure.step("Открываем главную страницу калькулятора"):
            base_page.navigate(self.BASE_URL)
        
        with allure.step("Проверяем отображение заголовка"):
            base_page.verify_element_visible("h1", "Проверка заголовка страницы")
        
        with allure.step("Проверяем наличие кнопки 'Добавить сервис'"):
            add_service_button = page.locator("button:has-text('Добавить сервис')")
            expect(add_service_button).to_be_visible()
        
        with allure.step("Делаем скриншот главной страницы"):
            base_page.take_screenshot("calculator_main_page")
    
    @allure.title("Проверка отображения стоимости")
    @allure.tag("NORMAL", "regression")
    @allure.label("priority", "NORMAL")
    def test_price_display(self, page: Page):
        """Проверка отображения блока с общей стоимостью"""
        base_page = BasePage(page)
        
        with allure.step("Открываем калькулятор"):
            base_page.navigate(self.BASE_URL)
        
        with allure.step("Проверяем наличие блока с ценой"):
            price_block = page.locator("[class*='price'], [class*='total']")
            expect(price_block.first).to_be_visible()
        
        with allure.step("Проверяем текст 'в месяц'"):
            month_text = page.locator("text=/в месяц/i")
            expect(month_text.first).to_be_visible()


# ============================================================================
# CONFTEST HOOKS (для pytest)
# ============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Хук для отслеживания упавших тестов"""
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        pytest.last_test_failed = True
        pytest.last_test_name = item.name
    else:
        pytest.last_test_failed = False


# ============================================================================
# INSTRUCTIONS FOR USAGE
# ============================================================================

"""
ИСПОЛЬЗОВАНИЕ ЭТОГО ШАБЛОНА:

1. Установите зависимости:
   pip install playwright pytest pytest-playwright allure-pytest

2. Установите браузеры:
   playwright install

3. Запуск тестов:
   pytest test_calculator.py --headed                    # С GUI
   pytest test_calculator.py --browser chromium         # Конкретный браузер
   pytest test_calculator.py -m smoke                   # Только smoke тесты
   pytest test_calculator.py --alluredir=allure-results # С Allure отчетами

4. Генерация Allure отчета:
   allure serve allure-results

5. Параллельный запуск:
   pytest test_calculator.py -n 4  # 4 воркера (нужен pytest-xdist)

СТРУКТУРА ТЕСТА (AAA Pattern):

class TestFeature:
    @allure.title("Название теста")
    def test_something(self, page: Page):
        # ARRANGE - Подготовка
        with allure.step("Подготовка данных"):
            pass
        
        # ACT - Действие
        with allure.step("Выполнение действия"):
            pass
        
        # ASSERT - Проверка
        with allure.step("Проверка результата"):
            pass
"""
