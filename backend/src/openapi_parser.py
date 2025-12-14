import yaml
import json
import httpx
from typing import Dict, Any, List
import prance
from urllib.parse import urlparse

class OpenAPIParser:
    async def parse_from_url(self, url: str) -> Dict[str, Any]:
        
        print(f"[DEBUG] parse_from_url вызван с URL: {url}")
        
        """Парсинг OpenAPI спецификации из URL"""
        headers = {
            "User-Agent": "TestOps-Copilot/1.0"
        }
        
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                
                # Определяем тип контента
                content_type = response.headers.get('content-type', '').lower()
                
                if 'yaml' in content_type or url.endswith('.yaml') or url.endswith('.yml'):
                    return yaml.safe_load(response.text)
                elif 'json' in content_type or url.endswith('.json'):
                    return response.json()
                else:
                    # Пробуем определить автоматически
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        try:
                            return yaml.safe_load(response.text)
                        except yaml.YAMLError:
                            raise ValueError(f"Не удалось распарсить ответ как JSON или YAML. Content-Type: {content_type}")
                            
            except httpx.HTTPStatusError as e:
                raise ValueError(f"Ошибка HTTP {e.response.status_code} при загрузке спецификации: {e}")
            except httpx.RequestError as e:
                raise ValueError(f"Ошибка сети при загрузке спецификации: {e}")
    
    def parse_from_content(self, content: str) -> Dict[str, Any]:
        """Парсинг OpenAPI спецификации из строки"""
        try:
            # Пробуем сначала как JSON
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                # Пробуем как YAML
                return yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValueError(f"Не удалось распарсить спецификацию: {e}")
    
    def validate_spec(self, spec: Dict[str, Any]) -> bool:
        """Валидация OpenAPI спецификации"""
        try:
            # Проверяем обязательные поля OpenAPI 3.0
            if not spec.get("openapi", "").startswith("3."):
                print(f"[WARNING] Версия OpenAPI не 3.x: {spec.get('openapi')}")
                # Все равно пытаемся обработать
            
            if not spec.get("paths"):
                print("[WARNING] Спецификация не содержит paths")
                return False
            
            # Пробуем использовать prance для более строгой валидации
            try:
                parser = prance.ResolvingParser(spec=spec)
                return True
            except Exception as e:
                print(f"[WARNING] Prance validation failed: {e}")
                # Возвращаем True если есть базовые поля
                return bool(spec.get("openapi") and spec.get("paths"))
                
        except Exception as e:
            print(f"[ERROR] Ошибка валидации спецификации: {e}")
            return False
    
    def get_endpoints_by_tag(self, spec: Dict[str, Any], tag: str) -> Dict[str, Any]:
        """Получение эндпоинтов по тегу"""
        endpoints = {}
        
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                tags = details.get("tags", [])
                if tag in tags:
                    endpoints[f"{method.upper()} {path}"] = {
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "parameters": details.get("parameters", []),
                        "responses": details.get("responses", {}),
                        "operationId": details.get("operationId", "")
                    }
        
        return endpoints
    
    def generate_test_scenarios(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Генерация тестовых сценариев из OpenAPI спецификации"""
        scenarios = []
        
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                operation_id = details.get("operationId", "")
                summary = details.get("summary", "")
                
                # Определяем тип операции
                method_lower = method.lower()
                if method_lower in ["get", "head"]:
                    test_type = "read"
                elif method_lower == "post":
                    test_type = "create"
                elif method_lower in ["put", "patch"]:
                    test_type = "update"
                elif method_lower == "delete":
                    test_type = "delete"
                else:
                    test_type = "operation"
                
                # Извлекаем теги
                tags = details.get("tags", [])
                if not tags and "tags" in spec.get("paths", {}).get(path, {}).get(method, {}):
                    tags = spec["paths"][path][method]["tags"]
                
                scenario = {
                    "path": path,
                    "method": method.upper(),
                    "operation_id": operation_id,
                    "summary": summary,
                    "type": test_type,
                    "tags": tags,
                    "parameters": self._extract_parameters(details),
                    "responses": self._extract_responses(details),
                    "security": details.get("security", []),
                    "requestBody": details.get("requestBody")
                }
                
                scenarios.append(scenario)
        
        return scenarios
    
    def _extract_parameters(self, operation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Извлечение параметров операции"""
        parameters = []
        
        for param in operation.get("parameters", []):
            param_info = {
                "name": param.get("name"),
                "in": param.get("in"),  # query, path, header, cookie
                "required": param.get("required", False),
                "type": param.get("schema", {}).get("type", "string"),
                "description": param.get("description", ""),
                "schema": param.get("schema", {})
            }
            parameters.append(param_info)
        
        # Также проверяем requestBody для параметров
        if "requestBody" in operation:
            content = operation["requestBody"].get("content", {})
            for content_type, schema_info in content.items():
                if "schema" in schema_info:
                    param_info = {
                        "name": "requestBody",
                        "in": "body",
                        "required": operation["requestBody"].get("required", False),
                        "type": "object",
                        "description": operation["requestBody"].get("description", ""),
                        "schema": schema_info["schema"],
                        "content_type": content_type
                    }
                    parameters.append(param_info)
        
        return parameters
    
    def _extract_responses(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечение ответов операции"""
        responses = {}
        
        for code, response in operation.get("responses", {}).items():
            content_types = list(response.get("content", {}).keys())
            responses[code] = {
                "description": response.get("description", ""),
                "content_types": content_types,
                "schema": response.get("content", {}).get(content_types[0], {}).get("schema") if content_types else None
            }
        
        return responses
    
    def filter_by_sections(self, spec: Dict[str, Any], sections: List[str]) -> Dict[str, Any]:
        """Фильтрация спецификации по секциям (тегам)"""
        if not sections:
            return spec
        
        filtered_paths = {}
        for path, methods in spec.get("paths", {}).items():
            filtered_methods = {}
            for method, details in methods.items():
                tags = details.get("tags", [])
                # Проверяем, есть ли пересечение тегов с запрошенными секциями
                if any(section in tags for section in sections):
                    filtered_methods[method] = details
            
            if filtered_methods:
                filtered_paths[path] = filtered_methods
        
        filtered_spec = spec.copy()
        filtered_spec["paths"] = filtered_paths
        return filtered_spec