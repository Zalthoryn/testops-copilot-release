#!/usr/bin/env python3
import redis
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Подключение к Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.Redis.from_url(redis_url, decode_responses=True)

print("=== Просмотр всех job в Redis ===\n")

# Получаем все ключи с job
all_keys = r.keys("job:*")
print(f"Найдено ключей: {len(all_keys)}")

for key in all_keys:
    print(f"\n{'='*60}")
    print(f"Ключ: {key}")
    
    # Получаем данные
    data = r.get(key)
    if data:
        try:
            job_data = json.loads(data)
            
            # Основная информация
            print(f"Job ID: {job_data.get('job_id')}")
            print(f"Тип: {job_data.get('type')}")
            print(f"Статус: {job_data.get('status')}")
            print(f"Создано: {job_data.get('created_at')}")
            
            # Если есть результат
            if 'result' in job_data and isinstance(job_data['result'], list):
                testcases = job_data['result']
                print(f"\nКоличество тест-кейсов: {len(testcases)}")
                
                # Показываем первые 3 тест-кейса
                for i, tc in enumerate(testcases[:3], 1):
                    print(f"\n--- Тест-кейс {i} ---")
                    print(f"Название: {tc.get('title')}")
                    print(f"Приоритет: {tc.get('priority')}")
                    print(f"Функционал: {tc.get('feature')}")
                    print(f"История: {tc.get('story')}")
                    
                    # Показываем первые 2 шага
                    steps = tc.get('steps', [])
                    if steps:
                        print(f"Шаги (первые 2): {steps[:2]}")
                    
                    # Длина Python кода
                    python_code = tc.get('python_code', '')
                    print(f"Длина кода: {len(python_code)} символов")
                    if python_code:
                        # Показываем первые 200 символов кода
                        print(f"Код (начало): {python_code[:200]}...")
                
                if len(testcases) > 3:
                    print(f"\n... и еще {len(testcases) - 3} тест-кейсов")
            
            # Если есть ошибка
            if 'error' in job_data:
                print(f"\n❌ Ошибка: {job_data['error']}")
                
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
            print(f"Сырые данные: {data[:500]}...")
    
    print(f"{'='*60}")

# Также проверяем списки jobs
print("\n\n=== Списки задач ===\n")
list_keys = r.keys("jobs:*")
for key in list_keys:
    print(f"\nСписок: {key}")
    items = r.lrange(key, 0, -1)
    print(f"Элементов: {len(items)}")
    if items:
        print(f"Первые 5: {items[:5]}")