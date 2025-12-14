import yaml
import json
import httpx
from typing import Dict, Any, List
import prance

class OpenAPIParser:
    async def parse_from_url(self, url: str) -> Dict[str, Any]:
        
        print(f"[DEBUG] parse_from_url вызван с URL: {url}") # Отладка

        """Парсинг OpenAPI спецификации из URL"""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            
            if url.endswith('.yaml') or url.endswith('.yml'):
                return yaml.safe_load(response.text)
            else:
                return response.json()
    
    def parse_from_content(self, content: str) -> Dict[str, Any]:
        """Парсинг OpenAPI спецификации из строки"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return yaml.safe_load(content)
    
    def validate_spec(self, spec: Dict[str, Any]) -> bool:
        """Валидация OpenAPI спецификации"""
        try:
            parser = prance.ResolvingParser(spec=spec)
            return True
        except Exception:
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
                        "responses": details.get("responses", {})
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
                if method.lower() in ["get", "head"]:
                    test_type = "read"
                elif method.lower() == "post":
                    test_type = "create"
                elif method.lower() in ["put", "patch"]:
                    test_type = "update"
                elif method.lower() == "delete":
                    test_type = "delete"
                else:
                    test_type = "operation"
                
                scenario = {
                    "path": path,
                    "method": method.upper(),
                    "operation_id": operation_id,
                    "summary": summary,
                    "type": test_type,
                    "tags": details.get("tags", []),
                    "parameters": self._extract_parameters(details),
                    "responses": self._extract_responses(details)
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
                "type": param.get("schema", {}).get("type", "string")
            }
            parameters.append(param_info)
        
        return parameters
    
    def _extract_responses(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечение ответов операции"""
        responses = {}
        
        for code, response in operation.get("responses", {}).items():
            responses[code] = {
                "description": response.get("description", ""),
                "content_type": list(response.get("content", {}).keys())[0] if response.get("content") else None
            }
        
        return responses