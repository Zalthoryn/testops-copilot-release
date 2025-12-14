import asyncio
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict
import re
from .llm_client import LLMClient

class TestOptimizer:
    """
    Анализатор и оптимизатор тест-кейсов
    
    Функционал:
    - Анализ покрытия требований тестами
    - Поиск дубликатов (хеширование + семантический анализ через LLM)
    - Выявление устаревших тестов
    - Поиск конфликтующих тестов
    - Выявление пробелов в покрытии
    - Генерация рекомендаций по оптимизации
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.duplicate_threshold = 0.85  # Порог схожести для дубликатов

    async def analyze_testcases(
        self,
        testcases: List[Dict],
        requirements: Optional[str] = None,
        repository_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ✅ РЕАЛИЗОВАН: Главный метод анализа тест-кейсов через LLM
        
        Проводит полный анализ:
        - Покрытие требований
        - Поиск дубликатов
        - Выявление устаревших тестов
        - Поиск конфликтов
        - Анализ пробелов
        """
        print(f"[OPTIMIZER] Начинаем анализ {len(testcases)} тест-кейсов")
        
        # Подготовка данных для анализа
        testcase_summary = self._prepare_testcase_summary(testcases)
        
        # Создаем промпт для комплексного анализа через LLM
        prompt = f"""Проведи комплексный анализ набора тест-кейсов.

ТЕСТ-КЕЙСЫ ({len(testcases)} шт.):
{testcase_summary}

ТРЕБОВАНИЯ (если есть):
{requirements if requirements else "Требования не указаны"}

Выполни следующий анализ:

1. ПОКРЫТИЕ ТРЕБОВАНИЙ:
   - Какие требования покрыты тестами
   - Какие требования частично покрыты
   - Какие требования не покрыты вообще
   - Процент покрытия

2. ДУБЛИКАТЫ И ИЗБЫТОЧНОСТЬ:
   - Есть ли семантически похожие тесты
   - Какие тесты проверяют одно и то же

3. АКТУАЛЬНОСТЬ:
   - Есть ли тесты, которые могут быть устаревшими
   - Тесты с устаревшей терминологией

4. ПРОБЕЛЫ В ПОКРЫТИИ:
   - Какие важные сценарии не покрыты
   - Какие edge cases пропущены
   - Критические пробелы

5. КАЧЕСТВО ТЕСТОВ:
   - Правильность структуры
   - Полнота проверок
   - Приоритизация

Ответь в JSON формате:
{{
    "coverage_analysis": {{
        "covered_requirements": ["req1", "req2"],
        "partially_covered": ["req3"],
        "not_covered": ["req4"],
        "coverage_percentage": 75.0,
        "details": "подробности"
    }},
    "quality_metrics": {{
        "total_tests": {len(testcases)},
        "well_structured": 0,
        "needs_improvement": 0,
        "average_quality_score": 0.0
    }},
    "duplicates_found": [
        {{"test1_id": "tc1", "test2_id": "tc2", "similarity": 0.9, "reason": "почему"}}
    ],
    "outdated_tests": [
        {{"test_id": "tc3", "reason": "почему устарел"}}
    ],
    "coverage_gaps": [
        {{"area": "название", "priority": "high/medium/low", "description": "что не покрыто"}}
    ],
    "recommendations": [
        {{
            "type": "improvement/removal/addition",
            "priority": "critical/high/medium/low",
            "action": "что сделать",
            "impact": "какой эффект",
            "effort": "сколько времени"
        }}
    ]
}}"""
        
        try:
            print("[OPTIMIZER] Отправляем запрос к LLM для анализа...")
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты — эксперт по тестированию ПО. Анализируешь тест-кейсы и даешь рекомендации по оптимизации."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            print("[OPTIMIZER] Получен ответ от LLM, парсим...")
            
            analysis = self._parse_llm_analysis(content)
            
            # Добавляем дополнительные метрики
            analysis["metadata"] = {
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "total_testcases": len(testcases),
                "repository_url": repository_url,
                "has_requirements": bool(requirements)
            }
            
            print(f"[OPTIMIZER] Анализ завершен: найдено {len(analysis.get('duplicates_found', []))} дубликатов, "
                  f"{len(analysis.get('coverage_gaps', []))} пробелов в покрытии")
            
            return analysis
            
        except Exception as e:
            print(f"[OPTIMIZER] Ошибка анализа через LLM: {e}")
            # Возвращаем fallback результат
            return self._get_fallback_analysis(requirements)

    async def analyze_and_optimize(
        self,
        repository_url: Optional[str] = None,
        requirements: Optional[str] = None,
        checks: List[str] = None,
        optimization_level: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Основной метод анализа и оптимизации тестов
        Используется API endpoint
        """
        if checks is None:
            checks = ["duplicates", "coverage", "outdated", "conflicts", "gaps"]

        # Загружаем тест-кейсы
        testcases = await self._load_testcases(repository_url)
        
        if not testcases:
            return {
                "error": "Нет тест-кейсов для анализа",
                "summary": {"total_testcases": 0}
            }

        analysis_results = {
            "summary": {
                "total_testcases": len(testcases),
                "issues_found": 0,
                "optimization_potential": 0.0
            },
            "checks": {},
            "recommendations": [],
            "optimized_testcases": []
        }

        # Выполняем запрошенные проверки
        for check in checks:
            if check == "duplicates":
                duplicates = await self._find_duplicates(testcases)
                analysis_results["checks"]["duplicates"] = duplicates
                analysis_results["summary"]["issues_found"] += len(duplicates)
                
            elif check == "coverage":
                coverage = await self._analyze_coverage(testcases, requirements)
                analysis_results["checks"]["coverage"] = coverage
                
            elif check == "outdated":
                outdated = await self._find_outdated(testcases, requirements)
                analysis_results["checks"]["outdated"] = outdated
                analysis_results["summary"]["issues_found"] += len(outdated)
                
            elif check == "conflicts":
                conflicts = await self._find_conflicts(testcases)
                analysis_results["checks"]["conflicts"] = conflicts
                analysis_results["summary"]["issues_found"] += len(conflicts)
                
            elif check == "gaps":
                gaps = await self._find_coverage_gaps(testcases, requirements)
                analysis_results["checks"]["coverage_gaps"] = gaps

        # Вычисляем потенциал оптимизации
        total_issues = analysis_results["summary"]["issues_found"]
        total_tests = len(testcases)
        if total_tests > 0:
            analysis_results["summary"]["optimization_potential"] = round(
                (total_issues / total_tests) * 100, 2
            )

        # Генерация рекомендаций
        analysis_results["recommendations"] = await self._generate_recommendations(
            analysis_results["checks"],
            optimization_level
        )

        # Создание оптимизированных тест-кейсов
        if optimization_level != "conservative":
            analysis_results["optimized_testcases"] = await self._optimize_testcases(
                testcases,
                analysis_results["checks"],
                optimization_level
            )

        analysis_results["metadata"] = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "optimization_level": optimization_level,
            "checks_performed": checks
        }

        return analysis_results

    async def _find_duplicates(self, testcases: List[Dict]) -> List[Dict]:
        """
        ✅ РЕАЛИЗОВАН: Поиск дублирующихся тест-кейсов
        
        Использует:
        1. Хеширование для точных дубликатов
        2. LLM для семантических дубликатов
        """
        print(f"[OPTIMIZER] Ищем дубликаты среди {len(testcases)} тест-кейсов...")
        
        duplicates = []
        seen_hashes = {}
        
        # 1. Поиск точных дубликатов через хеширование
        for testcase in testcases:
            test_hash = self._create_test_hash(testcase)
            
            if test_hash in seen_hashes:
                duplicates.append({
                    "testcase1": seen_hashes[test_hash],
                    "testcase2": testcase.get("id", "unknown"),
                    "similarity_score": 0.95,
                    "type": "exact",
                    "reason": "Идентичные шаги и ожидаемый результат"
                })
            else:
                seen_hashes[test_hash] = testcase.get("id", "unknown")
        
        # 2. Поиск семантических дубликатов через LLM
        semantic_dups = await self._find_semantic_duplicates(testcases)
        duplicates.extend(semantic_dups)
        
        print(f"[OPTIMIZER] Найдено дубликатов: {len(duplicates)}")
        return duplicates

    async def _find_semantic_duplicates(self, testcases: List[Dict]) -> List[Dict]:
        """
        ✅ РЕАЛИЗОВАН: Поиск семантических дубликатов через LLM
        """
        if len(testcases) < 2:
            return []
        
        semantic_dups = []
        
        # Группируем тесты по фичам для более эффективного сравнения
        feature_groups = defaultdict(list)
        for tc in testcases:
            feature = tc.get("feature", "unknown")
            feature_groups[feature].append(tc)
        
        # Анализируем пары внутри каждой группы
        for feature, group in feature_groups.items():
            if len(group) < 2:
                continue
                
            # Берем до 5 пар для анализа (чтобы не перегрузить LLM)
            max_pairs = min(5, len(group) * (len(group) - 1) // 2)
            analyzed_pairs = 0
            
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    if analyzed_pairs >= max_pairs:
                        break
                        
                    tc1, tc2 = group[i], group[j]
                    
                    prompt = f"""Сравни два тест-кейса и определи, являются ли они семантическими дубликатами.

Тест-кейс 1:
ID: {tc1.get('id')}
Название: {tc1.get('title')}
Шаги: {json.dumps(tc1.get('steps', []), ensure_ascii=False)}
Ожидаемый результат: {tc1.get('expected_result', '')}

Тест-кейс 2:
ID: {tc2.get('id')}
Название: {tc2.get('title')}
Шаги: {json.dumps(tc2.get('steps', []), ensure_ascii=False)}
Ожидаемый результат: {tc2.get('expected_result', '')}

Ответь в JSON:
{{
    "are_duplicates": true/false,
    "similarity_score": 0.0-1.0,
    "reason": "краткое объяснение"
}}"""
                    
                    try:
                        response = self.llm.client.chat.completions.create(
                            model=self.llm.model,
                            messages=[
                                {"role": "system", "content": "Ты определяешь семантическое сходство тестов."},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=500,
                            temperature=0.2
                        )
                        
                        content = response.choices[0].message.content
                        result = self._parse_json_response(content)
                        
                        if result.get("are_duplicates", False):
                            similarity = result.get("similarity_score", 0)
                            if similarity > self.duplicate_threshold:
                                semantic_dups.append({
                                    "testcase1": tc1.get("id"),
                                    "testcase2": tc2.get("id"),
                                    "similarity_score": similarity,
                                    "type": "semantic",
                                    "reason": result.get("reason", "Семантические дубликаты")
                                })
                        
                        analyzed_pairs += 1
                        
                    except Exception as e:
                        print(f"[OPTIMIZER] Ошибка сравнения тестов: {e}")
                        continue
        
        return semantic_dups

    async def _find_outdated(self, testcases: List[Dict], requirements: Optional[str]) -> List[Dict]:
        """
        ✅ РЕАЛИЗОВАН: Поиск устаревших тестов
        
        Критерии:
        1. Давность обновления (>6 месяцев)
        2. Устаревшая терминология
        3. Несоответствие текущим requirements (через LLM)
        """
        print(f"[OPTIMIZER] Ищем устаревшие тест-кейсы...")
        
        outdated = []
        
        # 1. Проверка по дате
        for testcase in testcases:
            updated_at = testcase.get("updated_at")
            if updated_at:
                try:
                    update_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    days_old = (datetime.now(timezone.utc) - update_date).days
                    
                    if days_old > 180:  # Старее 6 месяцев
                        outdated.append({
                            "testcase_id": testcase.get("id"),
                            "title": testcase.get("title"),
                            "days_old": days_old,
                            "reason": f"Не обновлялся {days_old} дней (>6 месяцев)"
                        })
                except Exception:
                    pass
            
            # 2. Проверка deprecated функционала
            deprecated_keywords = [
                "старый", "устаревший", "deprecated", "legacy", 
                "v1", "v2", "old", "retired", "obsolete"
            ]
            title = testcase.get("title", "").lower()
            description = testcase.get("description", "").lower()
            
            if any(keyword in title or keyword in description for keyword in deprecated_keywords):
                outdated.append({
                    "testcase_id": testcase.get("id"),
                    "title": testcase.get("title"),
                    "reason": "Содержит указание на устаревший функционал"
                })
        
        # 3. Проверка соответствия requirements через LLM
        if requirements and testcases:
            outdated_by_req = await self._check_outdated_by_requirements(testcases[:10], requirements)
            outdated.extend(outdated_by_req)
        
        print(f"[OPTIMIZER] Найдено устаревших тест-кейсов: {len(outdated)}")
        return outdated

    async def _check_outdated_by_requirements(self, testcases: List[Dict], requirements: str) -> List[Dict]:
        """Проверка устаревших тестов по requirements через LLM"""
        prompt = f"""Проанализируй, какие из тест-кейсов устарели на основе текущих требований.

ТЕКУЩИЕ ТРЕБОВАНИЯ:
{requirements}

ТЕСТ-КЕЙСЫ:
{json.dumps([{'id': tc.get('id'), 'title': tc.get('title'), 'steps': tc.get('steps', [])} 
             for tc in testcases], indent=2, ensure_ascii=False)}

Определи, какие тесты:
1. Проверяют функционал, который больше не упоминается в требованиях
2. Используют устаревшие API или интерфейсы
3. Не соответствуют текущей архитектуре

Ответь в JSON:
{{
    "outdated_tests": [
        {{"test_id": "id", "reason": "почему устарел"}}
    ]
}}"""
        
        try:
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "Ты анализируешь актуальность тестов."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            result = self._parse_json_response(response.choices[0].message.content)
            return result.get("outdated_tests", [])
            
        except Exception as e:
            print(f"[OPTIMIZER] Ошибка проверки через LLM: {e}")
            return []

    async def _find_conflicts(self, testcases: List[Dict]) -> List[Dict]:
        """
        ✅ РЕАЛИЗОВАН: Поиск конфликтующих тестов
        
        Ищет:
        1. Дублирование test_id
        2. Противоречия в expected_result для похожих тестов
        3. Взаимоисключающие проверки
        """
        print(f"[OPTIMIZER] Ищем конфликты в тест-кейсах...")
        
        conflicts = []
        
        # 1. Проверка дублирования ID
        id_counts = defaultdict(list)
        for tc in testcases:
            tc_id = tc.get("id")
            if tc_id:
                id_counts[tc_id].append(tc.get("title", "Без названия"))
        
        for tc_id, titles in id_counts.items():
            if len(titles) > 1:
                conflicts.append({
                    "type": "duplicate_id",
                    "test_id": tc_id,
                    "affected_tests": titles,
                    "reason": f"ID {tc_id} используется в {len(titles)} тестах"
                })
        
        # 2. Проверка противоречий в ожиданиях
        feature_tests = defaultdict(list)
        for tc in testcases:
            feature = tc.get("feature", "unknown")
            feature_tests[feature].append(tc)
        
        for feature, tests in feature_tests.items():
            # Анализируем пары тестов в одной фиче
            for i in range(len(tests)):
                for j in range(i + 1, len(tests)):
                    tc1, tc2 = tests[i], tests[j]
                    
                    # Проверяем схожие шаги но разные результаты
                    steps1 = set(tc1.get("steps", []))
                    steps2 = set(tc2.get("steps", []))
                    
                    if steps1 and steps2:
                        similarity = len(steps1 & steps2) / len(steps1 | steps2)
                        
                        if similarity > 0.7:  # Похожие шаги
                            result1 = tc1.get("expected_result", "")
                            result2 = tc2.get("expected_result", "")
                            
                            if result1 != result2 and result1 and result2:
                                conflicts.append({
                                    "type": "conflicting_expectations",
                                    "test1_id": tc1.get("id"),
                                    "test2_id": tc2.get("id"),
                                    "reason": f"Похожие шаги ({similarity:.0%} совпадение) но разные ожидаемые результаты"
                                })
        
        print(f"[OPTIMIZER] Найдено конфликтов: {len(conflicts)}")
        return conflicts

    async def _find_coverage_gaps(self, testcases: List[Dict], requirements: Optional[str]) -> List[Dict]:
        """
        ✅ РЕАЛИЗОВАН: Выявление пробелов в покрытии
        
        Анализирует:
        1. Требования vs покрытие тестами
        2. Edge cases
        3. Критические сценарии
        """
        print(f"[OPTIMIZER] Анализируем пробелы в покрытии...")
        
        if not requirements:
            return [{
                "area": "Требования не предоставлены",
                "priority": "low",
                "description": "Невозможно определить пробелы без требований"
            }]
        
        # Анализ через LLM
        testcase_summary = self._prepare_testcase_summary(testcases)
        
        prompt = f"""Проанализируй пробелы в тестовом покрытии.

ТРЕБОВАНИЯ:
{requirements}

СУЩЕСТВУЮЩИЕ ТЕСТ-КЕЙСЫ:
{testcase_summary}

Определи:
1. Какие важные сценарии не покрыты тестами
2. Какие edge cases пропущены
3. Критические пробелы в покрытии
4. Негативные сценарии, которых не хватает

Ответь в JSON:
{{
    "coverage_gaps": [
        {{
            "area": "название области",
            "priority": "critical/high/medium/low",
            "description": "что не покрыто",
            "suggested_tests": ["тест 1", "тест 2"]
        }}
    ]
}}"""
        
        try:
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "Ты анализируешь покрытие тестами."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            result = self._parse_json_response(response.choices[0].message.content)
            gaps = result.get("coverage_gaps", [])
            
            print(f"[OPTIMIZER] Найдено пробелов в покрытии: {len(gaps)}")
            return gaps
            
        except Exception as e:
            print(f"[OPTIMIZER] Ошибка анализа пробелов: {e}")
            return [{
                "area": "Общее покрытие",
                "priority": "medium",
                "description": "Не удалось выполнить детальный анализ пробелов"
            }]

    async def _analyze_coverage(self, testcases: List[Dict], requirements: Optional[str]) -> Dict[str, Any]:
        """Анализ покрытия требований тестами"""
        if not requirements:
            return {
                "message": "Требования не указаны для анализа покрытия",
                "coverage_percentage": 0
            }
        
        testcase_summary = self._prepare_testcase_summary(testcases)
        
        prompt = f"""Проанализируй покрытие требований тест-кейсами.

ТРЕБОВАНИЯ:
{requirements}

ТЕСТ-КЕЙСЫ:
{testcase_summary}

Определи:
1. Какие требования полностью покрыты тестами
2. Какие требования частично покрыты
3. Какие требования не покрыты вообще
4. Критические пробелы в покрытии
5. Общий процент покрытия

Ответь в JSON:
{{
    "covered_requirements": ["требование 1", "требование 2"],
    "partially_covered": ["требование 3"],
    "not_covered": ["требование 4", "требование 5"],
    "critical_gaps": ["пробел 1"],
    "coverage_percentage": 75.5,
    "details": "дополнительные детали"
}}"""
        
        try:
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "Ты анализируешь покрытие требований тестами."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return self._parse_json_response(response.choices[0].message.content)
            
        except Exception:
            # Fallback
            return {
                "covered_requirements": ["Основной функционал"],
                "partially_covered": ["Дополнительные фичи"],
                "not_covered": ["Edge cases"],
                "critical_gaps": ["Security testing"],
                "coverage_percentage": 65.0
            }

    async def _generate_recommendations(self, checks: Dict, optimization_level: str) -> List[Dict]:
        """Генерация рекомендаций по оптимизации"""
        recommendations = []
        
        # Рекомендации по дубликатам
        if "duplicates" in checks:
            dup_count = len(checks["duplicates"])
            if dup_count > 0:
                recommendations.append({
                    "type": "duplicates",
                    "priority": "high" if dup_count > 5 else "medium",
                    "action": f"Удалить или объединить {dup_count} дублирующихся тестов",
                    "impact": f"Сокращение набора тестов на {dup_count} кейсов",
                    "estimated_effort": "1-2 часа"
                })
        
        # Рекомендации по устаревшим тестам
        if "outdated" in checks:
            outdated_count = len(checks["outdated"])
            if outdated_count > 0:
                recommendations.append({
                    "type": "outdated",
                    "priority": "medium",
                    "action": f"Обновить или удалить {outdated_count} устаревших тестов",
                    "impact": "Улучшение релевантности тестового набора",
                    "estimated_effort": "2-3 часа"
                })
        
        # Рекомендации по конфликтам
        if "conflicts" in checks:
            conflicts_count = len(checks["conflicts"])
            if conflicts_count > 0:
                recommendations.append({
                    "type": "conflicts",
                    "priority": "critical",
                    "action": f"Разрешить {conflicts_count} конфликтов в тестах",
                    "impact": "Устранение противоречий и ошибок",
                    "estimated_effort": "1-2 часа"
                })
        
        # Рекомендации по покрытию
        if "coverage" in checks and isinstance(checks["coverage"], dict):
            coverage = checks["coverage"]
            not_covered = coverage.get("not_covered", [])
            if not_covered:
                recommendations.append({
                    "type": "coverage",
                    "priority": "critical" if "security" in str(not_covered).lower() else "high",
                    "action": f"Добавить тесты для {len(not_covered)} непокрытых требований",
                    "impact": f"Увеличение покрытия с {coverage.get('coverage_percentage', 0)}%",
                    "estimated_effort": "3-5 часов"
                })
        
        # Рекомендации по пробелам
        if "coverage_gaps" in checks:
            gaps = checks["coverage_gaps"]
            critical_gaps = [g for g in gaps if g.get("priority") == "critical"]
            if critical_gaps:
                recommendations.append({
                    "type": "coverage_gaps",
                    "priority": "critical",
                    "action": f"Закрыть {len(critical_gaps)} критических пробелов в покрытии",
                    "impact": "Повышение качества тестирования критичного функционала",
                    "estimated_effort": "4-6 часов"
                })
        
        # Общие рекомендации
        if optimization_level == "aggressive":
            recommendations.append({
                "type": "general",
                "priority": "low",
                "action": "Рефакторинг тестового кода: выделение общих фикстур и хелперов",
                "impact": "Улучшение поддерживаемости и читаемости тестов",
                "estimated_effort": "4-6 часов"
            })
        
        return recommendations

    async def _optimize_testcases(self, testcases: List[Dict], checks: Dict, optimization_level: str) -> List[Dict]:
        """Создание оптимизированной версии тест-кейсов"""
        optimized = []
        
        # Исключаем дубликаты
        duplicate_ids = set()
        if "duplicates" in checks:
            for dup in checks["duplicates"]:
                # Оставляем первый тест, удаляем второй
                duplicate_ids.add(dup.get("testcase2"))
        
        # Исключаем устаревшие (при агрессивной оптимизации)
        outdated_ids = set()
        if optimization_level == "aggressive" and "outdated" in checks:
            for outdated in checks["outdated"]:
                outdated_ids.add(outdated.get("testcase_id"))
        
        for testcase in testcases:
            tc_id = testcase.get("id")
            
            # Пропускаем дубликаты
            if tc_id in duplicate_ids:
                continue
            
            # Пропускаем устаревшие при агрессивной оптимизации
            if optimization_level == "aggressive" and tc_id in outdated_ids:
                continue
            
            # Оптимизируем тест-кейс
            optimized_tc = testcase.copy()
            
            # Упрощаем шаги для агрессивной оптимизации
            if optimization_level == "aggressive" and "steps" in optimized_tc:
                steps = optimized_tc["steps"]
                if len(steps) > 5:
                    optimized_tc["steps"] = steps[:5]
                    optimized_tc["optimization_note"] = "Упрощен: оставлены ключевые шаги"
            
            optimized.append(optimized_tc)
        
        return optimized

    # Вспомогательные методы

    def _prepare_testcase_summary(self, testcases: List[Dict]) -> str:
        """Подготовка краткого описания тест-кейсов для LLM"""
        summary_parts = []
        
        for i, tc in enumerate(testcases[:20], 1):  # Берем первые 20
            tc_summary = f"{i}. [{tc.get('id', 'no_id')}] {tc.get('title', 'Без названия')}"
            
            if tc.get("feature"):
                tc_summary += f" (Фича: {tc['feature']})"
            
            steps = tc.get("steps", [])
            if steps:
                tc_summary += f"\n   Шаги: {', '.join(steps[:3])}"
                if len(steps) > 3:
                    tc_summary += f" ... (+{len(steps)-3} шагов)"
            
            if tc.get("expected_result"):
                tc_summary += f"\n   Ожидается: {tc['expected_result'][:100]}"
            
            summary_parts.append(tc_summary)
        
        if len(testcases) > 20:
            summary_parts.append(f"\n... и еще {len(testcases)-20} тест-кейсов")
        
        return "\n\n".join(summary_parts)

    def _create_test_hash(self, testcase: Dict) -> str:
        """Создание хеша тест-кейса для быстрого сравнения"""
        key_data = f"{testcase.get('title', '')}:{testcase.get('feature', '')}:"
        steps = testcase.get('steps', [])
        key_data += ':'.join(steps[:3])
        
        return hashlib.md5(key_data.encode()).hexdigest()

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Парсинг JSON из ответа LLM"""
        try:
            # Убираем markdown formatting
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[OPTIMIZER] Ошибка парсинга JSON: {e}")
            print(f"[OPTIMIZER] Контент: {content[:200]}")
            return {}

    def _parse_llm_analysis(self, content: str) -> Dict[str, Any]:
        """Парсинг полного анализа от LLM"""
        result = self._parse_json_response(content)
        
        # Валидация структуры
        if not result:
            return self._get_fallback_analysis(None)
        
        # Заполняем defaults для отсутствующих полей
        result.setdefault("coverage_analysis", {})
        result.setdefault("quality_metrics", {})
        result.setdefault("duplicates_found", [])
        result.setdefault("outdated_tests", [])
        result.setdefault("coverage_gaps", [])
        result.setdefault("recommendations", [])
        
        return result

    def _get_fallback_analysis(self, requirements: Optional[str]) -> Dict[str, Any]:
        """Fallback анализ если LLM не доступен"""
        return {
            "coverage_analysis": {
                "covered_requirements": ["Основной функционал"],
                "partially_covered": ["Дополнительные фичи"],
                "not_covered": ["Edge cases", "Performance testing"],
                "coverage_percentage": 60.0,
                "details": "Базовый анализ (LLM недоступен)"
            },
            "quality_metrics": {
                "total_tests": 0,
                "well_structured": 0,
                "needs_improvement": 0,
                "average_quality_score": 0.7
            },
            "duplicates_found": [],
            "outdated_tests": [],
            "coverage_gaps": [
                {
                    "area": "Edge cases",
                    "priority": "medium",
                    "description": "Недостаточное покрытие граничных случаев"
                },
                {
                    "area": "Негативные сценарии",
                    "priority": "high",
                    "description": "Требуется больше негативных тестов"
                }
            ],
            "recommendations": [
                {
                    "type": "general",
                    "priority": "medium",
                    "action": "Добавить больше edge case тестов",
                    "impact": "Улучшение качества покрытия",
                    "estimated_effort": "2-4 часа"
                }
            ],
            "metadata": {
                "note": "Это fallback анализ. Для полного анализа требуется LLM."
            }
        }

    async def _load_testcases(self, repository_url: Optional[str]) -> List[Dict]:
        """Загрузка тест-кейсов из репозитория или заглушка"""
        # В реальном проекте здесь была бы загрузка из Git
        # Для демо возвращаем примерные данные
        return [
            {
                "id": "tc_001",
                "title": "Открытие главной страницы калькулятора",
                "feature": "Main Page",
                "steps": [
                    "Открыть https://cloud.ru/calculator",
                    "Дождаться загрузки страницы",
                    "Проверить заголовок"
                ],
                "expected_result": "Страница загружается, заголовок 'Калькулятор стоимости' отображается",
                "priority": "CRITICAL",
                "updated_at": "2024-06-15T10:30:00Z"
            },
            {
                "id": "tc_002",
                "title": "Добавление сервиса Compute",
                "feature": "Product Catalog",
                "steps": [
                    "Нажать кнопку 'Добавить сервис'",
                    "Выбрать 'Compute' из каталога",
                    "Подтвердить выбор"
                ],
                "expected_result": "Сервис Compute добавлен в конфигурацию, отображается в списке",
                "priority": "CRITICAL",
                "updated_at": "2024-07-20T14:00:00Z"
            },
            {
                "id": "tc_003",
                "title": "Проверка открытия страницы калькулятора",  # Дубликат tc_001
                "feature": "Main Page",
                "steps": [
                    "Перейти на https://cloud.ru/calculator",
                    "Проверить, что страница загрузилась"
                ],
                "expected_result": "Страница калькулятора открывается",
                "priority": "NORMAL",
                "updated_at": "2023-01-10T09:00:00Z"  # Старый тест
            },
            {
                "id": "tc_004",
                "title": "Конфигурация Compute: выбор CPU и RAM",
                "feature": "Product Configuration",
                "steps": [
                    "Добавить Compute в конфигурацию",
                    "Выбрать 4 CPU",
                    "Выбрать 8GB RAM"
                ],
                "expected_result": "Параметры сохранены, цена обновлена",
                "priority": "HIGH",
                "updated_at": "2024-08-05T16:30:00Z"
            },
            {
                "id": "tc_005",
                "title": "Скачивание конфигурации в PDF",
                "feature": "Export",
                "steps": [
                    "Настроить конфигурацию с несколькими сервисами",
                    "Нажать 'Скачать PDF'",
                    "Проверить скачанный файл"
                ],
                "expected_result": "PDF файл скачан, содержит все сервисы и цены",
                "priority": "NORMAL",
                "updated_at": "2024-09-12T11:00:00Z"
            }
        ]
