from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid
import json
import asyncio
from datetime import datetime, timezone
import os
import logging
import sys
import httpx
import psutil
import redis



from dotenv import load_dotenv
from .gitlab_integration import init_gitlab, get_gitlab_repos, commit_tests_to_gitlab
from .testplan_generator import TestPlanGenerator
from .llm_client import LLMClient
from .openapi_parser import OpenAPIParser
from .testcase_generator import TestCaseGenerator
from .autotest_generator import AutotestGenerator
from .optimizer import TestOptimizer
from .standards_checker import StandardsChecker
from .storage import StorageManager
from .models import *

load_dotenv()

# Настройка логирования с выводом в stdout
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(file_handler)

logger = logging.getLogger(__name__)

# Установим уровень для uvicorn логов тоже
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

app = FastAPI(
    title="TestOps Copilot API",
    description="AI-ассистент для автоматизации работы QA-инженера",
    version="1.0.0"
)

# allow_origins=["http://localhost:3000", "http://localhost:5173"],
# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация компонентов
llm_client = LLMClient()
storage = StorageManager()
testcase_generator = TestCaseGenerator(llm_client)
autotest_generator = AutotestGenerator(llm_client)
optimizer = TestOptimizer(llm_client)
standards_checker = StandardsChecker()
testplan_generator = TestPlanGenerator(llm_client)

@app.get("/")
async def root():
    return {"message": "TestOps Copilot API", "version": "1.0.0"}

@app.get("/api/config/")
async def get_config():
    """Получить текущую конфигурацию системы"""
    compute_status = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://compute.api.cloud.ru/api/v1/flavors",
                timeout=5.0
            )
            
            # Если получаем 401 (Unauthorized) или 403 (Forbidden) - API доступен, но нужна аутентификация
            # Если 200 - аутентификация работает
            if response.status_code in [200, 401, 403]:
                compute_status = True
    except Exception as e:
        logger.error(f"Compute check failed: {e}")

    return {
        "llm_model": os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
        "llm_available": llm_client.check_availability(),
        "compute_endpoint": "https://compute.api.cloud.ru",
        "compute_available": compute_status,
        "gitlab_configured": bool(os.getenv("GITLAB_TOKEN")),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.post("/api/config/llm/validate")
async def validate_llm(
    api_key: str = Form(...),
    model: str = Form(...),
    base_url: str = Form(...)
):
    """Валидация подключения к LLM"""
    try:
        # Используем корректное количество параметров
        result = llm_client.test_connection(
            api_key=api_key,
            base_url=base_url,
            model=model
        )
        if result.get("success"):
            return {"valid": True, "model": model, "base_url": base_url}
        else:
            return {"valid": False, "error": result.get("error", "Unknown error")}
    except Exception as e:
        return {"valid": False, "error": str(e)}

@app.post("/api/config/compute/validate")
async def validate_compute(data: ComputeValidationRequest):
    """Валидация подключения к Compute API"""
    
    token = data.token or os.getenv("COMPUTE_TOKEN") or os.getenv("COMPUTE_API_KEY")
    
    if not token:
        return {
            "valid": False,
            "endpoint": "https://compute.api.cloud.ru",
            "error": "Токен не предоставлен. Укажите token в запросе или установите переменную окружения COMPUTE_TOKEN"
        }
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Пробуем получить список флейворов
            response = await client.get(
                "https://compute.api.cloud.ru/api/v1/flavors",
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Проверяем структуру ответа
                    if "items" in data or isinstance(data, list):
                        available_resources = ["vms", "disks", "flavors"]  # Базовые ресурсы
                        # Пробуем определить доступные ресурсы из ответа
                        if "items" in data and len(data["items"]) > 0:
                            item = data["items"][0]
                            if "type" in item:
                                resource_type = item["type"]
                                if resource_type == "vm":
                                    available_resources = ["vms", "disks"]
                                elif resource_type == "disk":
                                    available_resources = ["disks", "flavors"]
                        
                        return {
                            "valid": True,
                            "endpoint": "https://compute.api.cloud.ru",
                            "available_resources": available_resources,
                            "authenticated": True
                        }
                except:
                    # Если не удалось распарсить JSON, но статус 200
                    return {
                        "valid": True,
                        "endpoint": "https://compute.api.cloud.ru",
                        "available_resources": ["vms", "disks", "flavors"],
                        "authenticated": True
                    }
            elif response.status_code == 401:
                return {
                    "valid": False,
                    "endpoint": "https://compute.api.cloud.ru",
                    "error": "Ошибка аутентификации: неверный токен"
                }
            elif response.status_code == 403:
                return {
                    "valid": False,
                    "endpoint": "https://compute.api.cloud.ru",
                    "error": "Доступ запрещен: недостаточно прав"
                }
            else:
                return {
                    "valid": False,
                    "endpoint": "https://compute.api.cloud.ru",
                    "error": f"API вернул статус {response.status_code}: {response.text[:100]}"
                }
                
    except httpx.TimeoutException:
        return {
            "valid": False,
            "endpoint": "https://compute.api.cloud.ru",
            "error": "Таймаут подключения к Compute API"
        }
    except Exception as e:
        return {
            "valid": False,
            "endpoint": "https://compute.api.cloud.ru",
            "error": f"Ошибка подключения: {str(e)}"
        }


# ==================== GITLAB INTEGRATION ====================

@app.post("/api/integrations/gitlab/init")
async def init_gitlab_integration(data: GitLabInitRequest):
    """Инициализация GitLab интеграции"""
    result = await init_gitlab(data.token, data.gitlab_url)
    return result

@app.post("/api/integrations/gitlab/repos")
async def get_gitlab_repositories(data: GitLabReposRequest):
    """Получение списка доступных репозиториев"""
    try:
        repos = await get_gitlab_repos(data.token, data.search)
        return {"success": True, "repositories": repos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/integrations/gitlab/commit-tests")
async def commit_testcases_to_gitlab(data: GitLabCommitRequest):
    """Коммит тест-кейсов в GitLab репозиторий"""
    result = await commit_tests_to_gitlab(
        token=data.token,
        project_id=data.project_id,
        testcases=data.testcases,
        directory=data.directory,
        branch=data.branch,
        commit_message=data.commit_message
    )
    return result

@app.get("/api/config/health/detailed")
async def get_detailed_health():
    """Детальная проверка здоровья системы"""
    
    # Проверка LLM
    llm_status = "healthy" if llm_client.check_availability() else "unhealthy"
    
    # Проверка Redis
    redis_status = "healthy"
    redis_connection = True
    try:
        # Пробуем выполнить ping к Redis
        redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        redis_client.ping()
        redis_client.close()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
        redis_connection = False
    
    # Проверка Storage
    storage_status = "healthy"
    available_space = "unknown"
    try:
        # Проверяем доступность директории storage
        storage_path = os.getenv("STORAGE_PATH", "./storage")
        os.makedirs(storage_path, exist_ok=True)
        
        # Проверяем доступное место на диске
        disk_usage = psutil.disk_usage(storage_path)
        available_gb = disk_usage.free // (1024**3)
        available_space = f"{available_gb}GB"
        
        # Проверяем возможность записи
        test_file = os.path.join(storage_path, ".health_check")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        storage_status = "unhealthy"
    
    # Проверка Compute API
    compute_status = "unknown"
    compute_response_time = None
    
    try:
        async with httpx.AsyncClient() as client:
            # Пробуем получить список флейворов без аутентификации (должен вернуть 401/403)
            start_time = datetime.now()
            response = await client.get(
                "https://compute.api.cloud.ru/api/v1/flavors",
                timeout=5.0
            )
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Если получаем 401 (Unauthorized) или 403 (Forbidden) - API доступен, но нужна аутентификация
            # Если 200 - аутентификация работает
            if response.status_code in [200, 401, 403]:
                compute_status = "healthy"
                compute_response_time = round(response_time, 2)
            else:
                compute_status = "unhealthy"
                
    except httpx.TimeoutException:
        compute_status = "timeout"
    except Exception as e:
        logger.error(f"Compute API health check failed: {e}")
        compute_status = "unhealthy"
    
    return {
        "llm": {
            "status": llm_status,
            "model": os.getenv("LLM_MODEL"),
            "response_time": 150  # ms
        },
        "redis": {
            "status": redis_status,
            "connection": redis_connection
        },
        "storage": {
            "status": storage_status,
            "available_space": available_space,
            "path": os.getenv("STORAGE_PATH", "./storage")
        },
        "compute": {
            "status": compute_status,
            "response_time_ms": compute_response_time,
            "endpoint": "https://compute.api.cloud.ru"
        }
    }

@app.post("/api/testcases/manual/ui")
async def generate_manual_ui_testcases(data: UIGenerationRequest, background_tasks: BackgroundTasks):
    """Генерация ручных UI тест-кейсов"""
    job_id = str(uuid.uuid4())
    
    async def generate_task():
        try:
            logger.info(f"Начало генерации UI тест-кейсов для job_id: {job_id}")
            logger.debug(f"Данные: {data.dict()}")
            
            # Обновление прогресса
            await storage.update_job_status(job_id, "processing", None, None, 25)
        
            testcases = await testcase_generator.generate_ui_testcases(
                requirements=data.requirements,
                test_blocks=data.test_blocks,
                target_count=data.target_count,
                priority=data.priority
            )
            
            logger.info(f"Сгенерировано {len(testcases) if testcases else 0} тест-кейсов")
            
            await storage.update_job_status(job_id, "processing", None, None, 75)

            await storage.save_testcases(job_id, testcases, "manual_ui")
            await storage.update_job_status(job_id, "completed", testcases, None, 100)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации UI тест-кейсов: {e}", exc_info=True)
            await storage.update_job_status(job_id, "failed", None, str(e))
    
    background_tasks.add_task(generate_task)
    await storage.create_job(job_id, "manual_ui", data.dict())
    
    logger.info(f"Тестовы лог {job_id}")
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Задача создана, начата генерация тест-кейсов",
        "estimated_time": 30,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/testcases/manual/api")
async def generate_manual_api_testcases(data: APIGenerationRequest, background_tasks: BackgroundTasks):
    """Генерация ручных API тест-кейсов"""
    job_id = str(uuid.uuid4())
    
    async def generate_task():
        try:
            logger.info(f"Начало генерации API тест-кейсов для job_id: {job_id}")
            logger.debug(f"Данные: {data.dict()}")
            
            # Обновляем прогресс
            await storage.update_job_status(job_id, "processing", None, None, 10)
            
            # Парсинг OpenAPI спецификации
            parser = OpenAPIParser()
            spec = {}
            
            if data.openapi_url:
                logger.info(f"Парсинг OpenAPI из URL: {data.openapi_url}")
                spec = await parser.parse_from_url(data.openapi_url)
            elif data.openapi_content:
                logger.info("Парсинг OpenAPI из контента")
                spec = parser.parse_from_content(data.openapi_content)
            else:
                # Используем стандартную спецификацию из cloud.ru
                logger.info("Использование стандартного OpenAPI URL из cloud.ru")
                try:
                    # Пробуем скачать спецификацию с официального URL
                    spec = await parser.parse_from_url("https://cloud.ru/docs/api/cdn/virtual-machines/ug/_specs/openapi-v3.yaml")
                except Exception as e:
                    logger.warning(f"Не удалось загрузить спецификацию: {e}")
                    # Fallback на локальный файл если есть
                    try:
                        with open("cloud_docs.yaml", "r", encoding="utf-8") as f:
                            spec = parser.parse_from_content(f.read())
                    except Exception as e2:
                        logger.error(f"Не удалось загрузить локальную спецификацию: {e2}")
                        raise ValueError("Не удалось загрузить OpenAPI спецификацию")
            
            # Валидация спецификации
            if not spec or not parser.validate_spec(spec):
                raise ValueError("Недействительная OpenAPI спецификация")
            
            await storage.update_job_status(job_id, "processing", None, None, 30)
            
            logger.info(f"Данные: {data}")
            # Генерация тест-кейсов
            logger.info(f"Генерация {data.target_count} API тест-кейсов для секций: {data.sections}")
            testcases = await testcase_generator.generate_api_testcases(
                openapi_spec=spec,
                sections=data.sections,
                count=data.target_count,  # Используем target_count
                priority=data.priority,
                auth_type=data.auth_type
            )
            
            logger.info(f"Сгенерировано {len(testcases) if testcases else 0} API тест-кейсов")
            
            await storage.update_job_status(job_id, "processing", None, None, 80)
            
            await storage.save_testcases(job_id, testcases, "manual_api")
            await storage.update_job_status(job_id, "completed", testcases, None, 100)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации API тест-кейсов: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await storage.update_job_status(job_id, "failed", None, str(e))
    
    background_tasks.add_task(generate_task)
    await storage.create_job(job_id, "manual_api", data.dict())
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Задача создана, начата генерация API тест-кейсов",
        "estimated_time": 60,
        "progress": 10,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/testcases/{job_id}")
async def get_testcase_job(job_id: str):
    """Получить статус задачи генерации тест-кейсов"""
    job = await storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job

@app.get("/api/testcases/{job_id}/download")
async def download_testcases(job_id: str):
    """Скачать сгенерированные тест-кейсы"""
    zip_path = await storage.get_testcases_zip(job_id)
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"testcases_{job_id}.zip"
    )

@app.post("/api/autotests/ui")
async def generate_ui_autotests(data: UIAutotestsRequest, background_tasks: BackgroundTasks):
    """Генерация UI автотестов (Playwright)"""
    job_id = str(uuid.uuid4())
    
    async def generate_task():
        try:
            logger.info(f"[AUTOTEST-UI] Начало генерации для job_id: {job_id}")
            
            # Обновляем прогресс
            await storage.update_job_status(job_id, "processing", None, None, 20)

            autotests = await autotest_generator.generate_ui_tests(
                manual_testcases_ids=data.manual_testcases_ids,
                framework=data.framework,
                browsers=data.browsers,
                base_url=data.base_url,
                headless=data.headless,
                priority_filter=data.priority_filter
            )
            
            logger.info(f"[AUTOTEST-UI] Сгенерировано {len(autotests) if autotests else 0} автотестов")
            
            # Обновляем прогресс
            await storage.update_job_status(job_id, "processing", None, None, 80)
            
            # Сохраняем автотесты
            zip_path = await storage.save_autotests(job_id, autotests, "ui")
            logger.info(f"[AUTOTEST-UI] Автотесты сохранены: {zip_path}")
            
            # Завершаем задачу
            await storage.update_job_status(job_id, "completed", autotests, None, 100)
            logger.info(f"[AUTOTEST-UI] Задача {job_id} завершена")
            
        except Exception as e:
            logger.error(f"[AUTOTEST-UI] Ошибка при генерации UI автотестов: {e}", exc_info=True)
            await storage.update_job_status(job_id, "failed", None, str(e))
    
    background_tasks.add_task(generate_task)
    await storage.create_job(job_id, "autotest_ui", data.dict())
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Задача создана, начата генерация UI автотестов",
        "estimated_time": 60,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/autotests/api")
async def generate_api_autotests(data: APIAutotestsRequest, background_tasks: BackgroundTasks):
    """Генерация API автотестов (pytest)"""
    job_id = str(uuid.uuid4())
    
    async def generate_task():
        try:
            logger.info(f"[AUTOTEST-API] Начало генерации для job_id: {job_id}")
            
            # Обновляем прогресс
            await storage.update_job_status(job_id, "processing", None, None, 20)

            autotests = await autotest_generator.generate_api_tests(
                manual_testcases_ids=data.manual_testcases_ids,
                openapi_url=data.openapi_url,
                sections=data.sections,
                base_url=data.base_url,
                auth_token=data.auth_token,
                test_framework=data.test_framework,
                http_client=data.http_client
            )

            logger.info(f"[AUTOTEST-API] Сгенерировано {len(autotests) if autotests else 0} автотестов")
            
            # Обновляем прогресс
            await storage.update_job_status(job_id, "processing", None, None, 80)
            
            # Сохраняем автотесты
            zip_path = await storage.save_autotests(job_id, autotests, "api")
            logger.info(f"[AUTOTEST-API] Автотесты сохранены: {zip_path}")
            
            # Завершаем задачу
            await storage.update_job_status(job_id, "completed", autotests, None, 100)
            logger.info(f"[AUTOTEST-API] Задача {job_id} завершена")
            
        except Exception as e:
            logger.error(f"[AUTOTEST-API] Ошибка при генерации API автотестов: {e}", exc_info=True)
            await storage.update_job_status(job_id, "failed", None, str(e))

    background_tasks.add_task(generate_task)
    await storage.create_job(job_id, "autotest_api", data.dict())
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Задача создана, начата генерация API автотестов",
        "estimated_time": 50,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/autotests/{job_id}")
async def get_autotest_job(job_id: str):
    """Получить статус задачи генерации автотестов"""
    job = await storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job

@app.get("/api/autotests/{job_id}/download")
async def download_autotests(job_id: str):
    """Скачать сгенерированные автотесты"""
    zip_path = await storage.get_autotests_zip(job_id)
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"autotests_{job_id}.zip"
    )

@app.post("/api/optimization/analyze")
async def analyze_optimization(data: OptimizationRequest, background_tasks: BackgroundTasks):
    """Анализ и оптимизация тест-кейсов"""
    job_id = str(uuid.uuid4())
    
    async def analyze_task():
        try:
            result = await optimizer.analyze_and_optimize(
                repository_url=data.repository_url,
                requirements=data.requirements,
                checks=data.checks,
                optimization_level=data.optimization_level
            )
            
            await storage.save_optimization_result(job_id, result)
            await storage.update_job_status(job_id, "completed", result)
            
        except Exception as e:
            logger.error(f"Ошибка при оптимизации: {e}", exc_info=True)
            await storage.update_job_status(job_id, "failed", None, str(e))
    
    background_tasks.add_task(analyze_task)
    await storage.create_job(job_id, "optimization", data.dict())
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Задача создана, начат анализ оптимизации",
        "estimated_time": 90,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/optimization/{job_id}")
async def get_optimization_job(job_id: str):
    """Получить статус задачи оптимизации"""
    job = await storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job

@app.get("/api/optimization/{job_id}/download")
async def download_optimized(job_id: str):
    """Скачать результаты оптимизации"""
    zip_path = await storage.get_optimization_zip(job_id)
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"optimized_{job_id}.zip"
    )

@app.post("/api/standards/check")
async def check_standards(
    files: List[UploadFile] = File(...),
    checks: List[str] = Form(...)
):
    """Проверка тест-кейсов на соответствие стандартам"""
    job_id = str(uuid.uuid4())
    
    # ВАЖНО: читаем содержимое файлов ДО запуска фоновой задачи
    file_contents = []
    for file in files:
        content = await file.read()
        file_contents.append({
            "filename": file.filename,
            "content": content.decode("utf-8")
        })

    async def check_task():
        try:
            logger.info(f"[STANDARDS] Начало проверки для job_id: {job_id}")
            await storage.update_job_status(job_id, "processing", None, None, 30)
            
            # Проверка файлов
            all_issues = []
            for file_data in file_contents:
                result = await standards_checker.check_testcase(file_data["content"])
                for issue in result.get("issues", []):
                    all_issues.append({
                        "file": file_data["filename"],
                        "line": 0,
                        "severity": issue.get("severity", "medium"),
                        "rule": issue.get("type", "unknown"),
                        "message": issue.get("message", ""),
                        "suggested_fix": ""
                    })
            
            logger.info(f"[STANDARDS] Найдено проблем: {len(all_issues)}")
            
            # Генерируем отчет
            if file_contents:
                report = await standards_checker.generate_standards_report(
                    testcase_code=file_contents[0]["content"],
                    include_suggestions=True
                )
            else:
                report = {}
            
            report_path = await storage.save_standards_report(job_id, report, all_issues)
            logger.info(f"[STANDARDS] HTML отчет сохранен: {report_path}")
            
            # Сохраняем в Redis
            await storage.update_job_status(job_id, "completed", {
                "report": report,
                "issues": all_issues,
                "issues_count": len(all_issues)
            }, None, 100)
            
        except Exception as e:  # 👈 Обязательный except после try
            logger.error(f"[STANDARDS] Ошибка: {e}", exc_info=True)
            await storage.update_job_status(job_id, "failed", None, str(e))
    
    # Запускаем в фоне
    asyncio.create_task(check_task())
    await storage.create_job(job_id, "standards_check", {"checks": checks})
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Задача создана, начата проверка стандартов",
        "estimated_time": 30,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/standards/{job_id}")
async def get_standards_job(job_id: str):
    """Получить статус задачи проверки стандартов"""
    job = await storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job

@app.get("/api/standards/{job_id}/report")
async def download_standards_report(job_id: str):
    """Скачать отчет по проверке стандартов"""
    report_path = await storage.get_standards_report(job_id)
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Отчет не найден")
    
    return FileResponse(
        report_path,
        media_type="text/html",
        filename=f"standards_report_{job_id}.html"
    )

app.post("/api/testplan/generate")
async def generate_testplan(data: TestPlanRequest, background_tasks: BackgroundTasks):
    """Генерация тест-плана на основе тест-кейсов"""
    job_id = str(uuid.uuid4())
    
    async def generate_task():
        try:
            logger.info(f"Генерация тест-плана: {job_id}")
            await storage.update_job_status(job_id, "processing", None, None, 30)
            
            testplan = await create_testplan_from_testcases(
                llm_client=llm_client,
                testcases=data.testcases,
                requirements=data.requirements,
                sprint_duration=data.sprint_duration,
                team_size=data.team_size
            )
            
            await storage.update_job_status(job_id, "completed", testplan, None, 100)
            
        except Exception as e:
            logger.error(f"Ошибка генерации тест-плана: {e}", exc_info=True)
            await storage.update_job_status(job_id, "failed", None, str(e))
    
    background_tasks.add_task(generate_task)
    await storage.create_job(job_id, "testplan", data.dict())
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Генерация тест-плана начата",
        "estimated_time": 45,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/testplan/{job_id}")
async def get_testplan_job(job_id: str):
    """Получить тест-план"""
    job = await storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job

@app.get("/api/testcases/")
async def list_testcase_jobs(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Список задач генерации тест-кейсов"""
    jobs = await storage.list_jobs(job_type="testcase", status=status, limit=limit, offset=offset)
    return jobs

@app.get("/api/jobs/")
async def list_all_jobs(
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Получить список всех задач"""
    jobs = await storage.list_all_jobs(
        job_type=job_type,
        status=status,
        limit=limit,
        offset=offset
    )
    return jobs

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)