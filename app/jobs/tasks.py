from __future__ import annotations

try:
    from celery import shared_task
except Exception:  # pragma: no cover - celery optional
    shared_task = None  # type: ignore

from app.jobs.async_jobs import execute_async_job


if shared_task:

    @shared_task(bind=True, name="app.run_async_job")
    def run_async_job(self, job_id: str) -> None:
        """Celery entrypoint to execute a registered async job."""
        execute_async_job(job_id)
