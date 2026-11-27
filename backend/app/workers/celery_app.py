from app.core.config import settings

try:
    from celery import Celery
    _HAS_CELERY = True
    celery_app = Celery(
        "brittle_worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,
    )
except ImportError:
    _HAS_CELERY = False
    class MockCelery:
        def task(self, *args, **kwargs):
            def decorator(fn):
                def delay(*task_args, **task_kwargs):
                    return None
                fn.delay = delay
                return fn
            return decorator
    celery_app = MockCelery()
