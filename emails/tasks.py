import redis
import time
import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)

RATE_LIMIT_KEY = 'email_rate_limit'
MAX_EMAILS_PER_MINUTE = 200
def check_rate_limit():
    lua_script = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local unique = ARGV[4]

    -- remove entries older than 60 seconds
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

    -- count how many emails sent in last 60 seconds
    local count = redis.call('ZCARD', key)

    if count < limit then
        -- use unique id as member, timestamp as score
        redis.call('ZADD', key, now, unique)
        redis.call('EXPIRE', key, window)
        return 1
    else
        return 0
    end
    """
    import uuid
    now = int(time.time() * 1000)
    window = 60000

    result = redis_client.eval(
        lua_script, 1,
        RATE_LIMIT_KEY, now, window, MAX_EMAILS_PER_MINUTE, str(uuid.uuid4())
    )
    return result == 1

@shared_task(
    bind=True,
    max_retries=3,
    acks_late=True,         # only acknowledge AFTER task completes
    reject_on_worker_lost=True,  # requeue if worker dies mid-task
)
def send_email_task(self, email_to, subject, body):
    """
    Send a transactional email with rate limiting and retry logic.
    
    acks_late=True means: if worker is SIGKILL'd mid-task,
    the task goes back to queue instead of being lost.
    """
    try:
        # check rate limit before sending
        if not check_rate_limit():
            # rate limited — retry after 2 seconds
            raise self.retry(countdown=2)

        # simulate sending email (replace with real provider call)
        logger.info(f"Sending email to {email_to}: {subject}")
        
        # simulate occasional failure for testing
        if body == 'FAIL':
            raise Exception("Simulated email provider failure")

        logger.info(f"Email sent successfully to {email_to}")
        return f"sent:{email_to}"

    except Exception as exc:
        if self.request.retries >= self.max_retries:
            # dead letter — move to failed queue after max retries
            logger.error(f"Email to {email_to} permanently failed. Moving to dead letter.")
            redis_client.lpush('dead_letter_queue', f"{email_to}:{subject}")
            return f"dead_letter:{email_to}"
        
        # exponential backoff: 2s, 4s, 8s
        countdown = 2 ** self.request.retries
        logger.warning(f"Retrying email to {email_to} in {countdown}s (attempt {self.request.retries + 1})")
        raise self.retry(exc=exc, countdown=countdown)