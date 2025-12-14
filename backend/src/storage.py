import json
import asyncio
import redis
import os
import zipfile
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import uuid

class StorageManager:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.storage_path = os.getenv("STORAGE_PATH", "./storage")
        
        # Создаем директории если их нет
        os.makedirs(self.storage_path, exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "testcases"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "autotests"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "optimization"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "standards"), exist_ok=True)
    
    async def create_job(self, job_id: str, job_type: str, data: Dict[str, Any]) -> None:
        """Создание новой задачи"""
        job_data = {
            "job_id": job_id,
            "type": job_type,
            "status": "pending",
            "data": data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.redis.setex(
            f"job:{job_id}",
            86400,  # TTL 24 часа
            json.dumps(job_data)
        )
        
        # Добавляем в список задач
        self.redis.lpush(f"jobs:{job_type}", job_id)
        self.redis.lpush("jobs:all", job_id)
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        progress: Optional[int] = None
    ) -> None:
        """Обновление статуса задачи с прогрессом"""
        job_data = self.redis.get(f"job:{job_id}")
        if not job_data:
            return
        
        job = json.loads(job_data)
        job["status"] = status
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        if progress is not None:
            job["progress"] = progress
        
        if result:
            job["result"] = result
        
        if error:
            job["error"] = error
        
        self.redis.setex(
            f"job:{job_id}",
            86400,
            json.dumps(job)
        )
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job_data = self.redis.get(f"job:{job_id}")
        if not job_data:
            return None
        
        job = json.loads(job_data)
        
        # Проверяем тип задачи
        job_type = job.get("type", "")
        
        response = {
            "job_id": job_id,
            "type": job_type,  # Добавляем тип
            "status": job.get("status", "unknown"),
            "message": job.get("error") or f"Job {job.get('status')}",
            "estimated_time": 30,
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
            "progress": job.get("progress", 0),
            # Для автотестов возвращаем result, а не testcases
            "result": job.get("result") if job.get("status") == "completed" else None
        }
        
        # Только для тест-кейсов добавляем поле testcases
        if job_type in ["manual_ui", "manual_api"]:
            response["testcases"] = job.get("result", []) if job.get("status") == "completed" else []
        
        return response
    
    async def list_jobs(
        self,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Список задач с фильтрацией"""
        jobs = []
        
        # Определяем ключ для списка
        if job_type and job_type != "all":
            key = f"jobs:{job_type}"
        else:
            key = "jobs:all"
        
        # Получаем ID задач
        job_ids = self.redis.lrange(key, offset, offset + limit - 1)
        
        for job_id in job_ids:
            job = await self.get_job(job_id)
            if job and (not status or job["status"] == status):
                jobs.append(job)
        
        return jobs
    
    async def save_testcases(
        self,
        job_id: str,
        testcases: List[Dict[str, Any]],
        test_type: str
    ) -> str:
        """Сохранение тест-кейсов в ZIP файл"""
        zip_path = os.path.join(self.storage_path, "testcases", f"{job_id}.zip")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем структуру файлов
            for i, testcase in enumerate(testcases):
                filename = f"testcase_{i+1:03d}.py"
                filepath = os.path.join(temp_dir, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(testcase.get("python_code", "# No code generated"))
            
            # Создаем метаданные
            metadata = {
                "job_id": job_id,
                "test_type": test_type,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "testcases_count": len(testcases),
                "testcases": [
                    {
                        "title": tc.get("title"),
                        "feature": tc.get("feature"),
                        "priority": tc.get("priority"),
                        "id": tc.get("id")
                    }
                    for tc in testcases
                ]
            }
            
            metadata_path = os.path.join(temp_dir, "metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Создаем ZIP архив
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        return zip_path
    
    async def get_testcases_zip(self, job_id: str) -> Optional[str]:
        """Получение пути к ZIP архиву с тест-кейсами"""
        zip_path = os.path.join(self.storage_path, "testcases", f"{job_id}.zip")
        return zip_path if os.path.exists(zip_path) else None
    
    async def save_autotests(
        self,
        job_id: str,
        autotests: List[Dict[str, Any]],
        test_type: str
    ) -> str:
        """Сохранение автотестов в ZIP файл"""
        zip_path = os.path.join(self.storage_path, "autotests", f"{job_id}.zip")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем структуру каталогов
            if test_type == "ui":
                tests_dir = os.path.join(temp_dir, "ui_tests")
                conftest_content = """
import pytest
import allure
from playwright.sync_api import Page

@pytest.fixture(scope="function")
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()

@pytest.fixture(scope="session")
def browser(browser_type, launch_browser):
    browser = launch_browser.launch(headless=True)
    yield browser
    browser.close()
"""
            else:  # api
                tests_dir = os.path.join(temp_dir, "api_tests")
                conftest_content = """
import pytest
import allure
import httpx

@pytest.fixture(scope="session")
def api_client():
    base_url = "https://compute.api.cloud.ru"
    headers = {
        "Authorization": "Bearer YOUR_TOKEN_HERE",
        "Content-Type": "application/json"
    }
    
    client = httpx.Client(base_url=base_url, headers=headers, timeout=30.0)
    yield client
    client.close()
"""
            
            os.makedirs(tests_dir, exist_ok=True)
            
            # Сохраняем conftest.py
            conftest_path = os.path.join(temp_dir, "conftest.py")
            with open(conftest_path, "w", encoding="utf-8") as f:
                f.write(conftest_content)
            
            # Сохраняем тесты
            for i, test in enumerate(autotests):
                filename = f"test_{i+1:03d}.py"
                filepath = os.path.join(tests_dir, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(test.get("code", "# No code generated"))
            
            # Создаем README
            readme_content = f"""# Auto-generated {test_type.upper()} Tests
Generated by TestOps Copilot
Job ID: {job_id}
Date: {datetime.now(timezone.utc).isoformat()}

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. For UI tests: `playwright install`
3. Run tests: `pytest --alluredir=./allure-results`

## Configuration
Update base URLs and authentication tokens in conftest.py
"""
            
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)
            
            # Создаем requirements.txt
            requirements = ["pytest", "allure-pytest", "httpx"]
            if test_type == "ui":
                requirements.append("playwright")
            
            req_path = os.path.join(temp_dir, "requirements.txt")
            with open(req_path, "w", encoding="utf-8") as f:
                f.write("\n".join(requirements))
            
            # Создаем ZIP
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        return zip_path
    
    async def get_autotests_zip(self, job_id: str) -> Optional[str]:
        """Получение пути к ZIP архиву с автотестами"""
        zip_path = os.path.join(self.storage_path, "autotests", f"{job_id}.zip")
        return zip_path if os.path.exists(zip_path) else None

    async def list_all_jobs(
        self,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Список всех задач с фильтрацией"""
        all_jobs = []
        
        # Получаем все ключи задач
        job_keys = self.redis.keys("job:*")
        
        for key in job_keys:
            try:
                job_data = self.redis.get(key)
                if job_data:
                    job = json.loads(job_data)
                    
                    # Фильтрация по типу
                    if job_type and job_type != "all":
                        if job.get("type") != job_type:
                            continue
                    
                    # Фильтрация по статусу
                    if status and status != "all":
                        if job.get("status") != status:
                            continue
                    
                    # Формируем ответ
                    job_response = {
                        "job_id": job.get("job_id"),
                        "type": job.get("type"),
                        "status": job.get("status", "unknown"),
                        "message": job.get("error") or f"Job {job.get('status')}",
                        "estimated_time": 30,
                        "created_at": job.get("created_at"),
                        "updated_at": job.get("updated_at"),
                        "progress": job.get("progress", 0),
                        "result": job.get("result")
                    }
                    all_jobs.append(job_response)
            except Exception as e:
                print(f"Error processing job {key}: {e}")
                continue
        
        # Сортировка по дате создания (новые первыми)
        all_jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Пагинация
        start = offset
        end = offset + limit
        return all_jobs[start:end]


    async def save_optimization_result(
        self,
        job_id: str,
        result: Dict[str, Any]
    ) -> str:
        """Сохранение результатов оптимизации в ZIP файл"""
        zip_path = os.path.join(self.storage_path, "optimization", f"{job_id}.zip")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Сохраняем результат в JSON
            result_file = os.path.join(temp_dir, "optimization_result.json")
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            # Если есть оптимизированные тест-кейсы, сохраняем их как файлы
            optimized_testcases = result.get("optimized_testcases", [])
            if optimized_testcases:
                testcases_dir = os.path.join(temp_dir, "optimized_testcases")
                os.makedirs(testcases_dir, exist_ok=True)
                
                for i, tc in enumerate(optimized_testcases):
                    filename = f"testcase_{i+1:03d}.py"
                    filepath = os.path.join(testcases_dir, filename)
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(tc.get("python_code", "# No code generated"))
            
            # Создаем ZIP архив
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        return zip_path

    async def save_standards_report(
        self,
        job_id: str,
        report: Dict[str, Any],
        violations: List[Any]
    ) -> str:
        """Сохранение отчета по проверке стандартов в HTML файл"""
        report_path = os.path.join(self.storage_path, "standards", f"{job_id}.html")
        
        # Генерируем простой HTML отчет
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f'    <title>Standards Report for Job {job_id}</title>',
            """    <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .error { background-color: #ffebee; }
            .warning { background-color: #fff3e0; }
            .info { background-color: #e3f2fd; }
            .summary { background-color: #f5f5f5; padding: 20px; margin-bottom: 20px; }
            </style>""",
            "</head>",
            "<body>",
            "    <h1>Standards Report</h1>",
            '    <div class="summary">',
            f"        <p><strong>Job ID:</strong> {job_id}</p>",
            f"        <p><strong>Generated at:</strong> {report.get('generated_at', 'N/A')}</p>",
            f"        <p><strong>Total files:</strong> {report.get('summary', {}).get('total_files', 0)}</p>",
            f"        <p><strong>Total violations:</strong> {report.get('summary', {}).get('total_violations', 0)}</p>",
            "    </div>",
            "    <h2>Violations</h2>",
            "    <table>",
            "        <thead>",
            "            <tr>",
            "                <th>File</th>",
            "                <th>Line</th>",
            "                <th>Severity</th>",
            "                <th>Rule</th>",
            "                <th>Message</th>",
            "                <th>Suggested Fix</th>",
            "            </tr>",
            "        </thead>",
            "        <tbody>"
        ]
        
        for v in violations:    
            # Обрабатываем как объект Violation или словарь
            if hasattr(v, 'file'):
                # Это объект Violation
                file_name = v.file
                line = v.line
                severity = v.severity.value if hasattr(v.severity, 'value') else str(v.severity)
                rule = v.rule.value if hasattr(v.rule, 'value') else str(v.rule)
                message = v.message
                suggested_fix = v.suggested_fix
            else:
                # Это словарь
                file_name = v.get("file", "N/A")
                line = v.get("line", "N/A")
                severity = v.get("severity", "info")
                rule = v.get("rule", "N/A")
                message = v.get("message", "N/A")
                suggested_fix = v.get("suggested_fix", "N/A")
            
            html_lines.append(f'            <tr class="{severity}">')
            html_lines.append(f'                <td>{file_name}</td>')
            html_lines.append(f'                <td>{line}</td>')
            html_lines.append(f'                <td>{severity}</td>')
            html_lines.append(f'                <td>{rule}</td>')
            html_lines.append(f'                <td>{message}</td>')
            html_lines.append(f'                <td>{suggested_fix}</td>')
            html_lines.append('            </tr>')
        
        # Закрываем таблицу и документ
        html_lines.extend([
            "        </tbody>",
            "    </table>",
            "</body>",
            "</html>"
        ])
        
        # Объединяем все строки
        html_content = "\n".join(html_lines)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return report_path

    async def get_optimization_zip(self, job_id: str) -> Optional[str]:
        """Получение пути к ZIP архиву с результатами оптимизации"""
        zip_path = os.path.join(self.storage_path, "optimization", f"{job_id}.zip")
        return zip_path if os.path.exists(zip_path) else None

    async def get_standards_report(self, job_id: str) -> Optional[str]:
        """Получение пути к HTML отчету по проверке стандартов"""
        report_path = os.path.join(self.storage_path, "standards", f"{job_id}.html")
        return report_path if os.path.exists(report_path) else None