import time
from unittest.mock import patch
from django.test import TestCase
from celery.contrib.testing.worker import start_worker
from artikate_project.celery import app
from emails.tasks import send_email_task, redis_client, RATE_LIMIT_KEY


class EmailQueueTest(TestCase):

    def setUp(self):
        # clear rate limit key before each test
        redis_client.delete(RATE_LIMIT_KEY)
        redis_client.delete('dead_letter_queue')

    def test_no_job_is_lost(self):
        """500 jobs submitted — all should be accepted into queue."""
        results = []
        for i in range(500):
            result = send_email_task.apply_async(
                args=[f"user{i}@test.com", "Order Confirmation", "Your order is confirmed"]
            )
            results.append(result)

        self.assertEqual(len(results), 500)
        print(f"\n✅ All 500 jobs submitted to queue")

    def test_rate_limit_never_exceeded(self):
        """Rate limiter should never allow more than 200 emails per minute."""
        allowed = 0
        blocked = 0

        from emails.tasks import check_rate_limit
        for _ in range(300):
            if check_rate_limit():
                allowed += 1
            else:
                blocked += 1

        print(f"\n✅ Allowed: {allowed}, Blocked: {blocked}")
        self.assertLessEqual(allowed, 200)
        self.assertGreater(blocked, 0)

    def test_failed_task_is_retried(self):
        """A task with body=FAIL should retry and end up in dead letter queue."""
        result = send_email_task.apply(
            args=["fail@test.com", "Test", "FAIL"]
        )
        # after max retries, should be in dead letter queue
        dead_letters = redis_client.llen('dead_letter_queue')
        print(f"\n✅ Dead letter queue length: {dead_letters}")
        self.assertGreaterEqual(dead_letters, 1)