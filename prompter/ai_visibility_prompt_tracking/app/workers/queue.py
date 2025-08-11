import redis
from rq import Queue
from ..config import settings
_redis = redis.Redis.from_url(settings.REDIS_URL)
rq_default = Queue("default", connection=_redis)
