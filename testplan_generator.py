import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .llm_client import LLMClient

class TestPlanGenerator:
    """
    Генератор тест-планов на основе тест-кейсов и аналитики
    
    Создает:
    - Structured test plan в JSON формате
    - Human-readable test plan в Markdown
    - Приоритизацию тестов
    - Оценку трудозатрат
    - Распределение по спринтам
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    async def generate_testplan(
        self,
        testcases: List[Dict[str, Any]],
        requirements: Optional[str] = None,
        sprint_duration_days: int = 14,
        team_size: int = 2,
        include_automation: bool = True
    ) -> Dict[str, Any]:
        """
        ✅ Генерация тест-плана на основе тест-кейсов
        
        Args:
            testcases: Список тест-кейсов
            requirements: Требования к продукту (опционально)
            sprint_duration_days: Длительность спринта в днях
            team_size: Размер команды тестирования
            include_automation: Включать ли автоматизацию
            
        Returns:
            Dict с тест-планом в разных форматах
        """
        print(f"[TESTPLAN] Генерируем тест-план для {len(testcases)} тест-кейсов...")
        
        # 1. Анализ и приоритизация тест-кейсов
        prioritized = await self._prioritize_testcases(testcases, requirements)
        
        # 2. Группировка по фичам и типам
        grouped = self._group_testcases(prioritized)
        
        # 3. Оценка трудозатрат
        effort_estimates = self._estimate_effort(prioritized)
        
        # 4. Распределение по спринтам
        sprint_plan = self._distribute_by_sprints(
            prioritized, 
            effort_estimates, 
            sprint_duration_days, 
            team_size
        )
        
        # 5. Генерация итогового плана
        testplan = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_testcases": len(testcases),
                "sprint_duration_days": sprint_duration_days,
                "team_size": team_size,
                "include_automation": include_automation
            },
            "summary": {
                "total_effort_hours": effort_estimates["total_hours"],
                "estimated_duration_days": effort_estimates["total_days"],
                "sprints_required": len(sprint_plan),
                "automation_candidates": effort_estimates.get("automation_count", 0),
                "coverage_by_priority": self._calculate_priority_coverage(prioritized)
            },
            "testcases_grouped": grouped,
            "effort_estimates": effort_estimates,
            "sprint_plan": sprint_plan,
            "prioritized_testcases": prioritized,
            "recommendations": await self._generate_plan_recommendations(
                prioritized, 
                effort_estimates, 
                requirements
            )
        }
        
        # 6. Генерация Markdown версии
        testplan["markdown"] = self._generate_markdown(testplan)
        
        # 7. Генерация JSON версии
        testplan["json"] = self._generate_json(testplan)
        
        print(f"[TESTPLAN] Тест-план готов: {len(sprint_plan)} спринтов, {effort_estimates['total_hours']} часов")
        
        return testplan
    
    async def _prioritize_testcases(
        self, 
        testcases: List[Dict], 
        requirements: Optional[str]
    ) -> List[Dict]:
        """Приоритизация тест-кейсов через LLM"""
        
        # Подготовка данных для LLM
        testcases_summary = []
        for tc in testcases[:50]:  # Берем первые 50
            testcases_summary.append({
                "id": tc.get("id", "unknown"),
                "title": tc.get("title", ""),
                "feature": tc.get("feature", ""),
                "priority": tc.get("priority", "NORMAL"),
                "steps_count": len(tc.get("steps", []))
            })
        
        prompt = f"""Проанализируй тест-кейсы и определи оптимальный порядок выполнения.

ТЕСТ-КЕЙСЫ:
{json.dumps(testcases_summary, indent=2, ensure_ascii=False)}

ТРЕБОВАНИЯ (если есть):
{requirements if requirements else "Не указаны"}

Определи для каждого тест-кейса:
1. Приоритет выполнения (1-5, где 1 - самый высокий)
2. Рекомендуемую очередь выполнения
3. Зависимости от других тестов
4. Является ли кандидатом на автоматизацию

Критерии приоритизации:
- Критичность функционала
- Частота использования
- Риски
- Сложность тестирования
- Зависимости

Ответь в JSON:
{{
    "prioritized_tests": [
        {{
            "test_id": "tc_001",
            "execution_priority": 1,
            "execution_order": 1,
            "priority_reason": "Критичный smoke тест",
            "automation_candidate": true,
            "dependencies": ["tc_002"],
            "risk_level": "high"
        }}
    ]
}}"""
        
        try:
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "Ты эксперт по планированию тестирования."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            result = self._parse_json_response(content)
            
            # Объединяем результаты с исходными тест-кейсами
            prioritization_map = {}
            for item in result.get("prioritized_tests", []):
                test_id = item.get("test_id")
                prioritization_map[test_id] = item
            
            prioritized = []
            for tc in testcases:
                tc_id = tc.get("id")
                priority_info = prioritization_map.get(tc_id, {
                    "execution_priority": 3,
                    "execution_order": 999,
                    "automation_candidate": False
                })
                
                enhanced_tc = tc.copy()
                enhanced_tc.update({
                    "execution_priority": priority_info.get("execution_priority", 3),
                    "execution_order": priority_info.get("execution_order", 999),
                    "priority_reason": priority_info.get("priority_reason", ""),
                    "automation_candidate": priority_info.get("automation_candidate", False),
                    "dependencies": priority_info.get("dependencies", []),
                    "risk_level": priority_info.get("risk_level", "medium")
                })
                
                prioritized.append(enhanced_tc)
            
            # Сортируем по execution_order
            prioritized.sort(key=lambda x: x.get("execution_order", 999))
            
            return prioritized
            
        except Exception as e:
            print(f"[TESTPLAN] Ошибка приоритизации через LLM: {e}")
            # Fallback: базовая приоритизация
            return self._fallback_prioritization(testcases)
    
    def _fallback_prioritization(self, testcases: List[Dict]) -> List[Dict]:
        """Fallback приоритизация без LLM"""
        priority_order = {
            "CRITICAL": 1,
            "HIGH": 2,
            "NORMAL": 3,
            "LOW": 4
        }
        
        enhanced = []
        for i, tc in enumerate(testcases):
            priority = tc.get("priority", "NORMAL")
            enhanced_tc = tc.copy()
            enhanced_tc.update({
                "execution_priority": priority_order.get(priority, 3),
                "execution_order": i + 1,
                "automation_candidate": priority in ["CRITICAL", "HIGH"],
                "dependencies": [],
                "risk_level": "high" if priority == "CRITICAL" else "medium"
            })
            enhanced.append(enhanced_tc)
        
        enhanced.sort(key=lambda x: (x["execution_priority"], x["execution_order"]))
        return enhanced
    
    def _group_testcases(self, testcases: List[Dict]) -> Dict[str, Any]:
        """Группировка тест-кейсов по фичам и типам"""
        grouped = {
            "by_feature": {},
            "by_priority": {
                "CRITICAL": [],
                "HIGH": [],
                "NORMAL": [],
                "LOW": []
            },
            "by_type": {
                "smoke": [],
                "regression": [],
                "integration": [],
                "other": []
            },
            "automation_candidates": []
        }
        
        for tc in testcases:
            # По фиче
            feature = tc.get("feature", "Uncategorized")
            if feature not in grouped["by_feature"]:
                grouped["by_feature"][feature] = []
            grouped["by_feature"][feature].append(tc)
            
            # По приоритету
            priority = tc.get("priority", "NORMAL")
            if priority in grouped["by_priority"]:
                grouped["by_priority"][priority].append(tc)
            
            # По типу
            test_type = tc.get("test_type", "other")
            if test_type in grouped["by_type"]:
                grouped["by_type"][test_type].append(tc)
            else:
                grouped["by_type"]["other"].append(tc)
            
            # Кандидаты на автоматизацию
            if tc.get("automation_candidate", False):
                grouped["automation_candidates"].append(tc)
        
        return grouped
    
    def _estimate_effort(self, testcases: List[Dict]) -> Dict[str, Any]:
        """Оценка трудозатрат на выполнение тестов"""
        
        # Базовые оценки времени в минутах
        effort_by_priority = {
            "CRITICAL": 30,  # Критичные тесты обычно сложнее
            "HIGH": 20,
            "NORMAL": 15,
            "LOW": 10
        }
        
        total_minutes = 0
        automation_count = 0
        automation_minutes = 0
        
        estimates_by_test = []
        
        for tc in testcases:
            priority = tc.get("priority", "NORMAL")
            steps_count = len(tc.get("steps", []))
            
            # Базовая оценка + время на каждый шаг
            base_minutes = effort_by_priority.get(priority, 15)
            step_minutes = steps_count * 2  # 2 минуты на шаг
            
            test_minutes = base_minutes + step_minutes
            total_minutes += test_minutes
            
            # Оценка для автоматизации
            is_automation_candidate = tc.get("automation_candidate", False)
            if is_automation_candidate:
                automation_count += 1
                # Автоматизация занимает примерно в 3-4 раза больше времени
                automation_minutes += test_minutes * 3.5
            
            estimates_by_test.append({
                "test_id": tc.get("id"),
                "manual_minutes": test_minutes,
                "automation_minutes": test_minutes * 3.5 if is_automation_candidate else 0
            })
        
        # Переводим в часы и дни
        manual_hours = round(total_minutes / 60, 1)
        manual_days = round(manual_hours / 8, 1)  # 8-часовой рабочий день
        
        automation_hours = round(automation_minutes / 60, 1)
        automation_days = round(automation_hours / 8, 1)
        
        return {
            "total_hours": manual_hours,
            "total_days": manual_days,
            "automation_count": automation_count,
            "automation_hours": automation_hours,
            "automation_days": automation_days,
            "estimates_by_test": estimates_by_test
        }
    
    def _distribute_by_sprints(
        self, 
        testcases: List[Dict], 
        effort_estimates: Dict,
        sprint_duration_days: int,
        team_size: int
    ) -> List[Dict]:
        """Распределение тест-кейсов по спринтам"""
        
        # Доступная емкость команды на спринт (в часах)
        hours_per_person_per_day = 6  # Эффективные часы работы
        sprint_capacity = sprint_duration_days * team_size * hours_per_person_per_day
        
        sprints = []
        current_sprint = {
            "sprint_number": 1,
            "testcases": [],
            "total_hours": 0,
            "capacity_hours": sprint_capacity
        }
        
        # Распределяем тесты по спринтам
        for tc in testcases:
            tc_id = tc.get("id")
            
            # Находим оценку времени для этого теста
            tc_estimate = next(
                (e for e in effort_estimates["estimates_by_test"] if e["test_id"] == tc_id),
                {"manual_minutes": 15}
            )
            
            tc_hours = tc_estimate["manual_minutes"] / 60
            
            # Если тест не помещается в текущий спринт, создаем новый
            if current_sprint["total_hours"] + tc_hours > sprint_capacity:
                sprints.append(current_sprint)
                current_sprint = {
                    "sprint_number": len(sprints) + 1,
                    "testcases": [],
                    "total_hours": 0,
                    "capacity_hours": sprint_capacity
                }
            
            # Добавляем тест в текущий спринт
            current_sprint["testcases"].append({
                "test_id": tc.get("id"),
                "title": tc.get("title"),
                "priority": tc.get("priority"),
                "estimated_hours": round(tc_hours, 2)
            })
            current_sprint["total_hours"] += tc_hours
        
        # Добавляем последний спринт
        if current_sprint["testcases"]:
            sprints.append(current_sprint)
        
        # Округляем total_hours
        for sprint in sprints:
            sprint["total_hours"] = round(sprint["total_hours"], 1)
            sprint["utilization_percent"] = round(
                (sprint["total_hours"] / sprint["capacity_hours"]) * 100, 1
            )
        
        return sprints
    
    def _calculate_priority_coverage(self, testcases: List[Dict]) -> Dict[str, int]:
        """Подсчет покрытия по приоритетам"""
        coverage = {
            "CRITICAL": 0,
            "HIGH": 0,
            "NORMAL": 0,
            "LOW": 0
        }
        
        for tc in testcases:
            priority = tc.get("priority", "NORMAL")
            if priority in coverage:
                coverage[priority] += 1
        
        return coverage
    
    async def _generate_plan_recommendations(
        self, 
        testcases: List[Dict],
        effort_estimates: Dict,
        requirements: Optional[str]
    ) -> List[Dict]:
        """Генерация рекомендаций по тест-плану"""
        recommendations = []
        
        # Анализ покрытия
        priority_coverage = self._calculate_priority_coverage(testcases)
        
        if priority_coverage["CRITICAL"] < 5:
            recommendations.append({
                "type": "coverage",
                "priority": "high",
                "message": f"Недостаточно критичных тестов ({priority_coverage['CRITICAL']})",
                "suggestion": "Добавьте больше smoke и критичных тестов"
            })
        
        # Анализ автоматизации
        automation_candidates = len([tc for tc in testcases if tc.get("automation_candidate")])
        total_tests = len(testcases)
        
        if automation_candidates / total_tests < 0.3:
            recommendations.append({
                "type": "automation",
                "priority": "medium",
                "message": f"Только {automation_candidates} тестов ({round(automation_candidates/total_tests*100)}%) подходят для автоматизации",
                "suggestion": "Рассмотрите возможность автоматизации регрессионных тестов"
            })
        
        # Анализ трудозатрат
        if effort_estimates["total_days"] > 30:
            recommendations.append({
                "type": "effort",
                "priority": "high",
                "message": f"Выполнение тестов займет {effort_estimates['total_days']} дней",
                "suggestion": "Рассмотрите возможность параллельного выполнения или сокращения набора тестов"
            })
        
        return recommendations
    
    def _generate_markdown(self, testplan: Dict) -> str:
        """Генерация тест-плана в Markdown формате"""
        md = []
        
        md.append("# Test Plan")
        md.append(f"\nСоздан: {testplan['metadata']['generated_at']}")
        md.append(f"\n## Summary")
        md.append(f"\n- **Всего тест-кейсов**: {testplan['metadata']['total_testcases']}")
        md.append(f"- **Общие трудозатраты**: {testplan['summary']['total_effort_hours']} часов ({testplan['summary']['estimated_duration_days']} дней)")
        md.append(f"- **Спринтов требуется**: {testplan['summary']['sprints_required']}")
        md.append(f"- **Кандидатов на автоматизацию**: {testplan['summary']['automation_candidates']}")
        
        md.append(f"\n## Распределение по приоритетам")
        for priority, count in testplan['summary']['coverage_by_priority'].items():
            md.append(f"- **{priority}**: {count} тестов")
        
        md.append(f"\n## План по спринтам")
        for sprint in testplan['sprint_plan']:
            md.append(f"\n### Спринт {sprint['sprint_number']}")
            md.append(f"- Тестов: {len(sprint['testcases'])}")
            md.append(f"- Трудозатраты: {sprint['total_hours']} часов")
            md.append(f"- Загрузка: {sprint['utilization_percent']}%")
            md.append(f"\nТест-кейсы:")
            for tc in sprint['testcases']:
                md.append(f"- [{tc['priority']}] {tc['title']} ({tc['estimated_hours']}h)")
        
        if testplan.get('recommendations'):
            md.append(f"\n## Рекомендации")
            for rec in testplan['recommendations']:
                md.append(f"\n### {rec['type'].upper()}")
                md.append(f"- **Приоритет**: {rec['priority']}")
                md.append(f"- **Проблема**: {rec['message']}")
                md.append(f"- **Рекомендация**: {rec['suggestion']}")
        
        return "\n".join(md)
    
    def _generate_json(self, testplan: Dict) -> str:
        """Генерация тест-плана в JSON формате"""
        # Убираем поля markdown и json для избежания рекурсии
        clean_plan = testplan.copy()
        clean_plan.pop("markdown", None)
        clean_plan.pop("json", None)
        
        return json.dumps(clean_plan, indent=2, ensure_ascii=False)
    
    def _parse_json_response(self, content: str) -> Dict:
        """Парсинг JSON из ответа LLM"""
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            print(f"[TESTPLAN] Ошибка парсинга JSON")
            return {}


# API helper functions

async def create_testplan_from_testcases(
    llm_client: LLMClient,
    testcases: List[Dict],
    requirements: Optional[str] = None,
    sprint_duration: int = 14,
    team_size: int = 2
) -> Dict[str, Any]:
    """
    Быстрое создание тест-плана
    
    Returns:
        Тест-план в различных форматах
    """
    generator = TestPlanGenerator(llm_client)
    return await generator.generate_testplan(
        testcases=testcases,
        requirements=requirements,
        sprint_duration_days=sprint_duration,
        team_size=team_size
    )
