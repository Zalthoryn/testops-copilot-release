import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Удалить все ключи, начинающиеся с 'job:'
keys = r.keys("job:*")
for key in keys:
    r.delete(key)

# Также удалить списки jobs
list_keys = r.keys("jobs:*")
for key in list_keys:
    r.delete(key)