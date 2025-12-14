## Redis
```cmd
redis-server
```

## Backend
```cmd
python -u -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
ИЛИ
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
ИЛИ
run.py
```

## Frontend
```cmd
npm run dev
```

D:\MyWorks\Testops-copilot-project\backend>