# DESIGN.md — Section 2: Async Job Queue

## Why Celery + Redis

I looked at three options:

- **Django Q** — uses the database as a queue. Fine for low traffic but
  would get hammered under 2000 requests in 10 seconds. Ruled out.
- **Custom implementation** — too much to rebuild when Celery already
  handles retries, backoff, and worker management.
- **Celery + Redis** — Redis holds jobs in memory, Celery processes them.
  The main reason I picked this is acks_late — it protects against job
  loss if the worker crashes mid-task.

## Rate Limiter — Sliding Window

I used a Redis sorted set. Each email sent is stored with its timestamp
as the score. Before every send, entries older than 60 seconds are
removed, then we count what's left. If under 200, allow. If not, block.

I chose this over fixed window because fixed window has a boundary
problem — 200 emails at 0:59 and 200 at 1:01 means 400 emails in
2 seconds. Sliding window doesn't have that problem.

All three steps run inside a Lua script so Redis executes them
atomically. No race conditions.

## If Redis fails

App fails closed — task retries, no email sent above the limit.
Safer than failing open for a rate limited provider.

## If Worker is SIGKILL'd

With default settings the task is lost — Celery acknowledges it the
moment it receives it.

With acks_late=True (what we use) — Celery only acknowledges after the
task finishes. If the worker dies mid-task, Redis still has it as
unacknowledged and redelivers it to the next worker.

We also set CELERY_WORKER_PREFETCH_MULTIPLIER=1 so each worker holds
only one task at a time. Without this a killed worker could drop
multiple tasks at once.