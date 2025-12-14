#!/usr/bin/env python3
import uvicorn
import os
import sys

if __name__ == "__main__":
    try:
        print("Запуск TestOps Copilot API...")
        
        uvicorn.run(
            "src.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )

    except KeyboardInterrupt:
        print("\nСервер остановлен")
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка запуска сервера: {e}")
        sys.exit(1)