import redis
import json
import datetime
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

def log_event(event_type, details):
    try:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        r.lpush("careerpilot:telemetry", json.dumps(event))
        r.ltrim("careerpilot:telemetry", 0, 999) # Keep last 1000 logs
    except Exception as e:
        print(f"Failed to log event: {e}")
