import ast
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

class StandardsChecker:
    """
    Проверка тест-кейсов на соответствие стандартам Allure TestOps as Code
    
    Проверки:
    - Структура тест-кейса (обязательные поля, декораторы)
    - Соответствие паттерну AAA (Arrange-Act-Assert)
    - Корректность Allure декораторов
    - Качество именования
    - Наличие документации
    - Валидация типов данных
    """
    
    def __init__(self):
        # Обязательные декораторы Allure
        self.required_decorators = [
            "@allure.manual",
            "@allure.feature",
            "@allure.story",
            "@allure.title"
        ]
        
        # Опциональные но рекомендуемые декораторы
        self.recommended_decorators = [
            "@allure.tag",
            "@allure.label",
            "@allure.link",
            "@mark.manual"
        ]
        
        # Валидные значения приоритета
        self.valid_priorities = ["CRITICAL", "HIGH", "NORMAL", "LOW"]
        
        # Валидные типы тестов
        self.valid_test_types = ["smoke", "regression", "integration", "e2e", "api", "ui"]
    
    async def check_testcase(self, testcase_code: str) -> Dict[str, Any]:
        """
        ✅ Главная функция проверки тест-кейса
        
        Проводит полную проверку и возвращает детальный отчет
        
        Args:
            testcase_code: Python код тест-кейса
            
        Returns:
            Dict с результатами всех проверок
        """
        print("[STANDARDS_CHECKER] Начинаем проверку тест-кейса...")
        
        results = {
            "valid": True,
            "score": 100.0,
            "checks": {},
            "issues": [],
            "recommendations": [],
            "metadata": {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "standards_version": "1.0"
            }
        }
        
        # 1. Проверка структуры
        structure_result = await self.check_testcase_structure(testcase_code)
        results["checks"]["structure"] = structure_result
        
        if not structure_result["valid"]:
            results["valid"] = False
            results["score"] -= 30
            results["issues"].extend(structure_result.get("issues", []))
        
        # ✅ НОВОЕ: Проверяем наличие синтаксической ошибки
        has_syntax_error = any(
            issue.get("type") == "syntax_error" 
            for issue in structure_result.get("issues", [])
        )
        
        # 2. Проверка паттерна AAA (пропускаем при синтаксической ошибке)
        if not has_syntax_error:
            aaa_result = await self.check_aaa_pattern(testcase_code)
            results["checks"]["aaa_pattern"] = aaa_result
            
            if not aaa_result["valid"]:
                results["score"] -= 25
                results["issues"].extend(aaa_result.get("issues", []))
        else:
            # Добавляем информационное сообщение
            results["checks"]["aaa_pattern"] = {
                "valid": False,
                "issues": [],
                "details": {"skipped": "Пропущено из-за синтаксических ошибок"}
            }
        
        # 3. ✅ ВАЖНО: Проверка декораторов ВСЕГДА (работает через regex!)
        decorators_result = await self.check_allure_decorators(testcase_code)
        results["checks"]["allure_decorators"] = decorators_result
        
        if not decorators_result["valid"]:
            results["valid"] = False
            results["score"] -= 25
            results["issues"].extend(decorators_result.get("issues", []))
        
        # 4. Проверка именования (пропускаем при синтаксической ошибке)
        if not has_syntax_error:
            naming_result = self._check_naming_conventions(testcase_code)
            results["checks"]["naming"] = naming_result
            
            if not naming_result["valid"]:
                results["score"] -= 10
                results["recommendations"].extend(naming_result.get("recommendations", []))
        else:
            results["checks"]["naming"] = {
                "valid": True,
                "issues": [],
                "recommendations": [],
                "details": {"skipped": "Пропущено из-за синтаксических ошибок"}
            }
        
        # 5. Проверка документации (пропускаем при синтаксической ошибке)
        if not has_syntax_error:
            docs_result = self._check_documentation(testcase_code)
            results["checks"]["documentation"] = docs_result
            
            if not docs_result["valid"]:
                results["score"] -= 10
                results["recommendations"].extend(docs_result.get("recommendations", []))
        else:
            results["checks"]["documentation"] = {
                "valid": True,
                "issues": [],
                "recommendations": [],
                "details": {"skipped": "Пропущено из-за синтаксических ошибок"}
            }
        
        # Генерация общих рекомендаций
        results["recommendations"].extend(self._generate_general_recommendations(results))
        
        # Финальная оценка
        results["score"] = max(0, results["score"])
        results["grade"] = self._calculate_grade(results["score"])
        
        print(f"[STANDARDS_CHECKER] Проверка завершена. Оценка: {results['score']}/100 ({results['grade']})")
        
        return results

    
    async def check_testcase_structure(self, testcase_code: str) -> Dict[str, Any]:
        """
        ✅ УЛУЧШЕНО: Проверка структуры тест-кейса
        
        Проверяет:
        - Наличие класса с тестами
        - Наличие тестовых методов
        - Обязательные импорты
        - Базовую синтаксическую корректность
        """
        result = {
            "valid": True,
            "issues": [],
            "details": {}
        }
        
        # 1. Проверка синтаксиса Python
        try:
            tree = ast.parse(testcase_code)
            result["details"]["syntax"] = "valid"
        except SyntaxError as e:
            result["valid"] = False
            result["issues"].append({
                "type": "syntax_error",
                "severity": "critical",
                "message": f"Синтаксическая ошибка: {str(e)}",
                "line": e.lineno
            })
            return result
        
        # 2. Проверка импортов
        required_imports = ["allure", "pytest"]
        found_imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found_imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    found_imports.add(node.module.split('.')[0])
        
        missing_imports = set(required_imports) - found_imports
        if missing_imports:
            result["issues"].append({
                "type": "missing_import",
                "severity": "high",
                "message": f"Отсутствуют обязательные импорты: {', '.join(missing_imports)}"
            })
        
        result["details"]["imports"] = {
            "found": list(found_imports),
            "required": required_imports,
            "missing": list(missing_imports)
        }
        
        # 3. Проверка наличия тестового класса
        test_classes = []
        test_methods = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                test_classes.append(node.name)
                
                # Проверяем методы в классе
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name.startswith('test_'):
                            test_methods.append(item.name)
        
        if not test_classes:
            result["valid"] = False
            result["issues"].append({
                "type": "no_test_class",
                "severity": "critical",
                "message": "Не найден тестовый класс"
            })
        
        if not test_methods:
            result["valid"] = False
            result["issues"].append({
                "type": "no_test_methods",
                "severity": "critical",
                "message": "Не найдены тестовые методы (должны начинаться с 'test_')"
            })
        
        result["details"]["classes"] = test_classes
        result["details"]["methods"] = test_methods
        
        # 4. Проверка структуры методов
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # Проверяем наличие шагов (allure.step или with allure_step)
                has_steps = False
                for child in ast.walk(node):
                    if isinstance(child, ast.With):
                        has_steps = True
                        break
                
                if not has_steps:
                    result["issues"].append({
                        "type": "no_steps",
                        "severity": "medium",
                        "message": f"Метод {node.name} не содержит шагов (allure.step или with allure_step)",
                        "method": node.name
                    })
        
        return result
    
    async def check_aaa_pattern(self, testcase_code: str) -> Dict[str, Any]:
        """
        ✅ УЛУЧШЕНО: Проверка соответствия паттерну AAA (Arrange-Act-Assert)
        
        Анализирует структуру теста и проверяет последовательность фаз
        """
        result = {
            "valid": True,
            "issues": [],
            "details": {}
        }
        
        try:
            tree = ast.parse(testcase_code)
        except SyntaxError:
            result["valid"] = False
            result["issues"].append({
                "type": "syntax_error",
                "severity": "critical",
                "message": "Невозможно проверить паттерн AAA из-за синтаксических ошибок"
            })
            return result
        
        # Ищем тестовые методы
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                method_name = node.name
                
                # Анализируем with блоки (allure steps)
                steps = []
                for child in node.body:
                    if isinstance(child, ast.With):
                        # Извлекаем название шага
                        for item in child.items:
                            if isinstance(item.context_expr, ast.Call):
                                # Пытаемся получить название шага
                                if item.context_expr.args:
                                    arg = item.context_expr.args[0]
                                    if isinstance(arg, ast.Constant):
                                        steps.append(arg.value.lower())
                
                result["details"][method_name] = {
                    "steps_count": len(steps),
                    "steps": steps
                }
                
                # Проверяем наличие фаз AAA
                has_arrange = any("подгот" in step or "arrange" in step or "откр" in step for step in steps)
                has_act = any("выполн" in step or "act" in step or "нажа" in step or "ввод" in step for step in steps)
                has_assert = any("провер" in step or "assert" in step or "убед" in step for step in steps)
                
                result["details"][method_name]["aaa_phases"] = {
                    "arrange": has_arrange,
                    "act": has_act,
                    "assert": has_assert
                }
                
                # Проверяем последовательность
                if len(steps) < 2:
                    result["issues"].append({
                        "type": "insufficient_steps",
                        "severity": "medium",
                        "message": f"Метод {method_name} содержит менее 2 шагов",
                        "method": method_name
                    })
                
                if not (has_arrange or has_act or has_assert):
                    result["issues"].append({
                        "type": "aaa_not_detected",
                        "severity": "low",
                        "message": f"Не удалось четко определить фазы AAA в методе {method_name}",
                        "method": method_name,
                        "recommendation": "Используйте явные названия шагов, отражающие фазы Arrange-Act-Assert"
                    })
        
        if result["issues"]:
            result["valid"] = False
        
        return result
    
    async def check_allure_decorators(self, testcase_code: str) -> Dict[str, Any]:
        """
        ✅ УЛУЧШЕНО: Проверка Allure декораторов
        
        Проверяет:
        - Наличие обязательных декораторов
        - Корректность значений декораторов
        - Валидность параметров
        """
        result = {
            "valid": True,
            "issues": [],
            "details": {
                "found_decorators": [],
                "missing_required": [],
                "invalid_values": []
            }
        }
        
        # Извлекаем все декораторы
        decorators_in_code = re.findall(r'@[\w\.]+(?:\([^)]*\))?', testcase_code)
        result["details"]["found_decorators"] = decorators_in_code
        
        # 1. Проверяем наличие обязательных декораторов
        for required in self.required_decorators:
            pattern = required.replace(".", r"\.")
            if not re.search(pattern, testcase_code):
                result["valid"] = False
                result["details"]["missing_required"].append(required)
                result["issues"].append({
                    "type": "missing_decorator",
                    "severity": "critical",
                    "message": f"Отсутствует обязательный декоратор: {required}"
                })
        
        # 2. Проверяем правильность значений декораторов
        
        # Проверка @allure.tag
        tag_matches = re.findall(r'@allure\.tag\(["\'](\w+)["\']\)', testcase_code)
        for tag in tag_matches:
            if tag.upper() not in self.valid_priorities:
                result["details"]["invalid_values"].append({
                    "decorator": "@allure.tag",
                    "value": tag,
                    "expected": self.valid_priorities
                })
                result["issues"].append({
                    "type": "invalid_tag_value",
                    "severity": "medium",
                    "message": f"Недопустимое значение приоритета в @allure.tag: '{tag}'. Допустимые: {self.valid_priorities}"
                })
        
        # Проверка @allure.label("priority", ...)
        priority_matches = re.findall(r'@allure\.label\(["\']priority["\']\s*,\s*["\'](\w+)["\']\)', testcase_code)
        for priority in priority_matches:
            if priority.upper() not in self.valid_priorities:
                result["details"]["invalid_values"].append({
                    "decorator": "@allure.label(priority)",
                    "value": priority,
                    "expected": self.valid_priorities
                })
                result["issues"].append({
                    "type": "invalid_priority_value",
                    "severity": "medium",
                    "message": f"Недопустимое значение приоритета: '{priority}'. Допустимые: {self.valid_priorities}"
                })
        
        # 3. Проверяем наличие хотя бы одного способа указания приоритета
        has_priority = "@allure.tag" in testcase_code or '@allure.label("priority"' in testcase_code
        if not has_priority:
            result["issues"].append({
                "type": "no_priority",
                "severity": "medium",
                "message": "Не указан приоритет теста (@allure.tag или @allure.label('priority'))"
            })
        
        # 4. Проверяем наличие @allure.feature и @allure.story
        if "@allure.feature" not in testcase_code:
            result["valid"] = False
            result["issues"].append({
                "type": "missing_feature",
                "severity": "high",
                "message": "Отсутствует @allure.feature - укажите тестируемую функцию"
            })
        
        if "@allure.story" not in testcase_code:
            result["valid"] = False
            result["issues"].append({
                "type": "missing_story",
                "severity": "high",
                "message": "Отсутствует @allure.story - укажите пользовательскую историю"
            })
        
        # 5. Проверяем @allure.title
        if "@allure.title" not in testcase_code:
            result["valid"] = False
            result["issues"].append({
                "type": "missing_title",
                "severity": "critical",
                "message": "Отсутствует @allure.title - обязательно указывайте название теста"
            })
        
        return result
    
    def _check_naming_conventions(self, testcase_code: str) -> Dict[str, Any]:
        """Проверка соглашений об именовании"""
        result = {
            "valid": True,
            "issues": [],
            "recommendations": []
        }
        
        try:
            tree = ast.parse(testcase_code)
        except SyntaxError:
            # При синтаксической ошибке возвращаем пустой результат
            return result
        
        # ✅ НОВОЕ: Проверка именования класса через regex (работает и без AST)
        class_matches = re.findall(r'class\s+(\w+)', testcase_code)
        for class_name in class_matches:
            # Класс должен заканчиваться на Tests или Test
            if not (class_name.endswith('Tests') or class_name.endswith('Test')):
                result["valid"] = False
                result["recommendations"].append({
                    "type": "class_naming",
                    "message": f"Класс '{class_name}' должен заканчиваться на 'Tests' или 'Test'",
                    "suggestion": f"Переименуйте в '{class_name}Tests'"
                })
            
            # Класс должен быть в CamelCase
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                result["valid"] = False
                result["recommendations"].append({
                    "type": "class_naming",
                    "message": f"Класс '{class_name}' должен быть в CamelCase"
                })
        
        # Проверяем имена методов через AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                method_name = node.name
                
                if method_name.startswith('test_'):
                    # Метод должен быть в snake_case
                    if not re.match(r'^test_[a-z0-9_]+$', method_name):
                        result["valid"] = False
                        result["recommendations"].append({
                            "type": "method_naming",
                            "message": f"Метод '{method_name}' должен быть в snake_case"
                        })
                    
                    # Имя должно быть описательным (минимум 3 слова)
                    words = method_name.split('_')
                    if len(words) < 3:
                        result["recommendations"].append({
                            "type": "method_naming",
                            "message": f"Имя метода '{method_name}' слишком короткое. Используйте описательные имена",
                            "suggestion": "Например: test_user_can_login_with_valid_credentials"
                        })
        
        return result
    
    def _check_documentation(self, testcase_code: str) -> Dict[str, Any]:
        """Проверка наличия документации"""
        result = {
            "valid": True,
            "issues": [],
            "recommendations": []
        }
        
        try:
            tree = ast.parse(testcase_code)
        except SyntaxError:
            return result
        
        # Проверяем docstrings
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Проверяем docstring класса
                docstring = ast.get_docstring(node)
                if not docstring:
                    result["valid"] = False
                    result["recommendations"].append({
                        "type": "missing_docstring",
                        "message": f"Класс '{node.name}' не имеет docstring",
                        "suggestion": "Добавьте описание назначения тестового класса"
                    })
            
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # Проверяем docstring метода
                docstring = ast.get_docstring(node)
                if not docstring:
                    result["recommendations"].append({
                        "type": "missing_docstring",
                        "message": f"Метод '{node.name}' не имеет docstring",
                        "suggestion": "Добавьте краткое описание теста"
                    })
        
        return result
    
    def _generate_general_recommendations(self, results: Dict[str, Any]) -> List[Dict]:
        """Генерация общих рекомендаций по улучшению"""
        recommendations = []
        
        score = results.get("score", 100)
        
        if score < 70:
            recommendations.append({
                "type": "general",
                "priority": "high",
                "message": "Тест-кейс требует значительной доработки",
                "suggestion": "Обратите внимание на критические ошибки в секции issues"
            })
        elif score < 85:
            recommendations.append({
                "type": "general",
                "priority": "medium",
                "message": "Тест-кейс в целом соответствует стандартам, но есть улучшения",
                "suggestion": "Устраните найденные замечания для повышения качества"
            })
        
        # Рекомендации по missing decorators
        decorators_check = results.get("checks", {}).get("allure_decorators", {})
        missing = decorators_check.get("details", {}).get("missing_required", [])
        
        if missing:
            recommendations.append({
                "type": "decorators",
                "priority": "critical",
                "message": f"Добавьте обязательные декораторы: {', '.join(missing)}",
                "suggestion": "Используйте полный набор Allure декораторов для корректной интеграции"
            })
        
        return recommendations
    
    def _calculate_grade(self, score: float) -> str:
        """Вычисление буквенной оценки"""
        if score >= 95:
            return "A+ (Отлично)"
        elif score >= 85:
            return "A (Очень хорошо)"
        elif score >= 75:
            return "B (Хорошо)"
        elif score >= 65:
            return "C (Удовлетворительно)"
        elif score >= 50:
            return "D (Требует доработки)"
        else:
            return "F (Неудовлетворительно)"
    
    async def generate_standards_report(
        self,
        testcase_code: str,
        include_suggestions: bool = True
    ) -> Dict[str, Any]:
        """
        ✅ Генерация полного отчета о соответствии стандартам
        
        Args:
            testcase_code: Код тест-кейса
            include_suggestions: Включать ли предложения по улучшению
            
        Returns:
            Детальный отчет с результатами всех проверок
        """
        check_result = await self.check_testcase(testcase_code)
        
        report = {
            "summary": {
                "valid": check_result["valid"],
                "score": check_result["score"],
                "grade": check_result["grade"],
                "total_issues": len(check_result["issues"]),
                "critical_issues": len([i for i in check_result["issues"] if i.get("severity") == "critical"]),
                "checked_at": check_result["metadata"]["checked_at"]
            },
            "detailed_checks": check_result["checks"],
            "issues": check_result["issues"],
            "recommendations": check_result["recommendations"] if include_suggestions else []
        }
        
        # Группируем проблемы по severity
        issues_by_severity = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for issue in check_result["issues"]:
            severity = issue.get("severity", "medium")
            issues_by_severity[severity].append(issue)
        
        report["issues_by_severity"] = issues_by_severity
        
        return report


# Вспомогательные функции для API

async def validate_testcase_code(testcase_code: str) -> Dict[str, Any]:
    """
    Быстрая валидация кода тест-кейса
    
    Returns:
        Dict с базовым результатом проверки
    """
    checker = StandardsChecker()
    result = await checker.check_testcase(testcase_code)
    
    return {
        "valid": result["valid"],
        "score": result["score"],
        "critical_issues": len([i for i in result["issues"] if i.get("severity") == "critical"]),
        "total_issues": len(result["issues"])
    }
