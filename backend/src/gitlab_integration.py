import httpx
import base64
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio

class GitLabClient:
    """
    Клиент для работы с GitLab API v4
    
    Функциональность:
    - Аутентификация и валидация токена
    - Получение информации о проектах и репозиториях
    - Работа с файлами (create, read, update)
    - Commit и push тест-кейсов
    - Управление merge requests
    """
    
    def __init__(self, token: str, gitlab_url: str = "https://gitlab.com"):
        """
        Инициализация клиента
        
        Args:
            token: Personal Access Token для GitLab
            gitlab_url: URL GitLab instance (по умолчанию gitlab.com)
        """
        self.token = token
        self.gitlab_url = gitlab_url.rstrip('/')
        self.api_url = f"{self.gitlab_url}/api/v4"
        
        self.headers = {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json"
        }
        
        self.timeout = httpx.Timeout(30.0, connect=10.0)
    
    async def authenticate(self) -> Dict[str, Any]:
        """
        ✅ Проверка валидности токена и получение информации о текущем пользователе
        
        Returns:
            Dict с информацией о пользователе
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.api_url}/user",
                    headers=self.headers
                )
                response.raise_for_status()
                
                user_info = response.json()
                return {
                    "valid": True,
                    "user_id": user_info.get("id"),
                    "username": user_info.get("username"),
                    "name": user_info.get("name"),
                    "email": user_info.get("email"),
                    "avatar_url": user_info.get("avatar_url")
                }
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    return {
                        "valid": False,
                        "error": "Неверный токен",
                        "details": "Токен не прошел аутентификацию"
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"HTTP {e.response.status_code}",
                        "details": str(e)
                    }
            except Exception as e:
                return {
                    "valid": False,
                    "error": "Ошибка подключения",
                    "details": str(e)
                }
    
    async def get_projects(self, search: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        ✅ Получение списка доступных проектов
        
        Args:
            search: Поисковый запрос (опционально)
            limit: Максимальное количество проектов
            
        Returns:
            List проектов
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                params = {
                    "per_page": min(limit, 100),
                    "membership": True,  # Только проекты, где пользователь является участником
                    "simple": True  # Упрощенный формат для производительности
                }
                
                if search:
                    params["search"] = search
                
                response = await client.get(
                    f"{self.api_url}/projects",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                
                projects = response.json()
                
                # Форматируем результат
                formatted_projects = []
                for project in projects:
                    formatted_projects.append({
                        "id": project.get("id"),
                        "name": project.get("name"),
                        "path": project.get("path"),
                        "path_with_namespace": project.get("path_with_namespace"),
                        "description": project.get("description", ""),
                        "web_url": project.get("web_url"),
                        "default_branch": project.get("default_branch", "main"),
                        "visibility": project.get("visibility"),
                        "last_activity_at": project.get("last_activity_at")
                    })
                
                return formatted_projects
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"Ошибка получения проектов: HTTP {e.response.status_code}")
            except Exception as e:
                raise Exception(f"Ошибка получения проектов: {str(e)}")
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        ✅ Получение информации о конкретном проекте
        
        Args:
            project_id: ID проекта или path_with_namespace (например, "username/repo")
            
        Returns:
            Dict с информацией о проекте
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # URL-encode project_id если это path
                if "/" in project_id:
                    from urllib.parse import quote_plus
                    project_id = quote_plus(project_id)
                
                response = await client.get(
                    f"{self.api_url}/projects/{project_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                
                project = response.json()
                
                return {
                    "id": project.get("id"),
                    "name": project.get("name"),
                    "path": project.get("path"),
                    "path_with_namespace": project.get("path_with_namespace"),
                    "description": project.get("description", ""),
                    "web_url": project.get("web_url"),
                    "default_branch": project.get("default_branch", "main"),
                    "visibility": project.get("visibility"),
                    "ssh_url_to_repo": project.get("ssh_url_to_repo"),
                    "http_url_to_repo": project.get("http_url_to_repo"),
                    "created_at": project.get("created_at"),
                    "last_activity_at": project.get("last_activity_at")
                }
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise Exception(f"Проект '{project_id}' не найден")
                else:
                    raise Exception(f"Ошибка получения проекта: HTTP {e.response.status_code}")
            except Exception as e:
                raise Exception(f"Ошибка получения проекта: {str(e)}")
    
    async def get_file(
        self,
        project_id: str,
        file_path: str,
        branch: str = "main"
    ) -> Optional[Dict[str, Any]]:
        """
        ✅ Получение содержимого файла из репозитория
        
        Args:
            project_id: ID проекта
            file_path: Путь к файлу в репозитории
            branch: Ветка (по умолчанию main)
            
        Returns:
            Dict с содержимым файла или None если не найден
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if "/" in project_id:
                    from urllib.parse import quote_plus
                    project_id = quote_plus(project_id)
                
                file_path_encoded = quote_plus(file_path)
                
                response = await client.get(
                    f"{self.api_url}/projects/{project_id}/repository/files/{file_path_encoded}",
                    headers=self.headers,
                    params={"ref": branch}
                )
                
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                
                file_data = response.json()
                
                # Декодируем содержимое из base64
                content = base64.b64decode(file_data.get("content", "")).decode("utf-8")
                
                return {
                    "file_name": file_data.get("file_name"),
                    "file_path": file_data.get("file_path"),
                    "size": file_data.get("size"),
                    "encoding": file_data.get("encoding"),
                    "content": content,
                    "ref": file_data.get("ref"),
                    "blob_id": file_data.get("blob_id"),
                    "commit_id": file_data.get("commit_id"),
                    "last_commit_id": file_data.get("last_commit_id")
                }
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 404:
                    raise Exception(f"Ошибка получения файла: HTTP {e.response.status_code}")
                return None
            except Exception as e:
                raise Exception(f"Ошибка получения файла: {str(e)}")
    
    async def create_or_update_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str = "main",
        author_email: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ✅ Создание или обновление файла в репозитории
        
        Args:
            project_id: ID проекта
            file_path: Путь к файлу
            content: Содержимое файла
            commit_message: Сообщение коммита
            branch: Ветка
            author_email: Email автора (опционально)
            author_name: Имя автора (опционально)
            
        Returns:
            Dict с информацией о файле и коммите
        """
        # Сначала проверяем, существует ли файл
        existing_file = await self.get_file(project_id, file_path, branch)
        
        if existing_file:
            # Обновляем существующий файл
            return await self._update_file(
                project_id, file_path, content, commit_message,
                branch, author_email, author_name
            )
        else:
            # Создаем новый файл
            return await self._create_file(
                project_id, file_path, content, commit_message,
                branch, author_email, author_name
            )
    
    async def _create_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str,
        author_email: Optional[str],
        author_name: Optional[str]
    ) -> Dict[str, Any]:
        """Создание нового файла"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if "/" in project_id:
                    from urllib.parse import quote_plus
                    project_id = quote_plus(project_id)
                
                file_path_encoded = quote_plus(file_path)
                
                payload = {
                    "branch": branch,
                    "content": content,
                    "commit_message": commit_message
                }
                
                if author_email:
                    payload["author_email"] = author_email
                if author_name:
                    payload["author_name"] = author_name
                
                response = await client.post(
                    f"{self.api_url}/projects/{project_id}/repository/files/{file_path_encoded}",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                return {
                    "action": "created",
                    "file_path": result.get("file_path"),
                    "branch": result.get("branch")
                }
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"Ошибка создания файла: HTTP {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"Ошибка создания файла: {str(e)}")
    
    async def _update_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str,
        author_email: Optional[str],
        author_name: Optional[str]
    ) -> Dict[str, Any]:
        """Обновление существующего файла"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if "/" in project_id:
                    from urllib.parse import quote_plus
                    project_id = quote_plus(project_id)
                
                file_path_encoded = quote_plus(file_path)
                
                payload = {
                    "branch": branch,
                    "content": content,
                    "commit_message": commit_message
                }
                
                if author_email:
                    payload["author_email"] = author_email
                if author_name:
                    payload["author_name"] = author_name
                
                response = await client.put(
                    f"{self.api_url}/projects/{project_id}/repository/files/{file_path_encoded}",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                return {
                    "action": "updated",
                    "file_path": result.get("file_path"),
                    "branch": result.get("branch")
                }
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"Ошибка обновления файла: HTTP {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"Ошибка обновления файла: {str(e)}")
    
    async def commit_testcases(
        self,
        project_id: str,
        testcases: List[str],
        directory: str = "tests/manual",
        branch: str = "main",
        commit_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ✅ Коммит тест-кейсов в репозиторий
        
        Создает/обновляет файлы с тест-кейсами и делает commit
        
        Args:
            project_id: ID проекта
            testcases: Список тест-кейсов (Python код)
            directory: Директория для размещения тестов
            branch: Ветка
            commit_message: Сообщение коммита (опционально)
            
        Returns:
            Dict с результатами коммита
        """
        if not commit_message:
            commit_message = f"Add {len(testcases)} test case(s) via TestOps Copilot"
        
        committed_files = []
        errors = []
        
        # Коммитим каждый тест-кейс как отдельный файл
        for i, testcase_code in enumerate(testcases, 1):
            try:
                # Генерируем имя файла из кода
                file_name = self._extract_test_filename(testcase_code, i)
                file_path = f"{directory.rstrip('/')}/{file_name}"
                
                # Создаем/обновляем файл
                result = await self.create_or_update_file(
                    project_id=project_id,
                    file_path=file_path,
                    content=testcase_code,
                    commit_message=f"{commit_message} - {file_name}",
                    branch=branch
                )
                
                committed_files.append({
                    "file_path": file_path,
                    "action": result.get("action"),
                    "success": True
                })
                
            except Exception as e:
                errors.append({
                    "testcase_index": i,
                    "error": str(e)
                })
        
        return {
            "success": len(errors) == 0,
            "committed_files": committed_files,
            "total_files": len(testcases),
            "successful": len(committed_files),
            "failed": len(errors),
            "errors": errors,
            "branch": branch,
            "commit_message": commit_message
        }
    
    async def create_merge_request(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ✅ Создание merge request
        
        Args:
            project_id: ID проекта
            source_branch: Исходная ветка
            target_branch: Целевая ветка
            title: Заголовок MR
            description: Описание MR (опционально)
            
        Returns:
            Dict с информацией о созданном MR
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if "/" in project_id:
                    from urllib.parse import quote_plus
                    project_id = quote_plus(project_id)
                
                payload = {
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "title": title
                }
                
                if description:
                    payload["description"] = description
                
                response = await client.post(
                    f"{self.api_url}/projects/{project_id}/merge_requests",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                
                mr = response.json()
                
                return {
                    "id": mr.get("id"),
                    "iid": mr.get("iid"),
                    "title": mr.get("title"),
                    "state": mr.get("state"),
                    "web_url": mr.get("web_url"),
                    "source_branch": mr.get("source_branch"),
                    "target_branch": mr.get("target_branch")
                }
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"Ошибка создания MR: HTTP {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise Exception(f"Ошибка создания MR: {str(e)}")
    
    def _extract_test_filename(self, testcase_code: str, index: int) -> str:
        """Извлечение имени файла из кода тест-кейса"""
        # Пытаемся найти имя класса
        import re
        
        class_match = re.search(r'class\s+(\w+)', testcase_code)
        if class_match:
            class_name = class_match.group(1)
            # Конвертируем CamelCase в snake_case
            snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
            return f"test_{snake_case}.py"
        
        # Пытаемся найти имя функции
        func_match = re.search(r'def\s+(test_\w+)', testcase_code)
        if func_match:
            func_name = func_match.group(1)
            return f"{func_name}.py"
        
        # Fallback - используем индекс
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"test_case_{index}_{timestamp}.py"


# Вспомогательные функции для использования в main.py

async def init_gitlab(token: str, gitlab_url: str = "https://gitlab.com") -> Dict[str, Any]:
    """
    Инициализация GitLab клиента и валидация токена
    
    Returns:
        Dict с результатом валидации и информацией о пользователе
    """
    try:
        client = GitLabClient(token, gitlab_url)
        auth_result = await client.authenticate()
        
        if auth_result.get("valid"):
            return {
                "success": True,
                "message": "GitLab подключен успешно",
                **auth_result
            }
        else:
            return {
                "success": False,
                "error": auth_result.get("error"),
                "details": auth_result.get("details")
            }
    except Exception as e:
        return {
            "success": False,
            "error": "Ошибка инициализации",
            "details": str(e)
        }


async def get_gitlab_repos(token: str, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Получение списка доступных репозиториев
    
    Returns:
        List репозиториев
    """
    try:
        client = GitLabClient(token)
        projects = await client.get_projects(search=search)
        return projects
    except Exception as e:
        raise Exception(f"Ошибка получения репозиториев: {str(e)}")


async def commit_tests_to_gitlab(
    token: str,
    project_id: str,
    testcases: List[str],
    directory: str = "tests/manual",
    branch: str = "main",
    commit_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Коммит тест-кейсов в GitLab репозиторий
    
    Returns:
        Dict с результатами коммита
    """
    try:
        client = GitLabClient(token)
        result = await client.commit_testcases(
            project_id=project_id,
            testcases=testcases,
            directory=directory,
            branch=branch,
            commit_message=commit_message
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "committed_files": [],
            "total_files": len(testcases),
            "successful": 0,
            "failed": len(testcases)
        }
