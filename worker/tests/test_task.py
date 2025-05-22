import pandas as pd
from celery.app.task import Context

from worker.tasks import run_deconvolve

#-- helpers ---------------------------------------------------------

class DummySelf:
    def __init__(self, task_id):
        self.request = Context(id=task_id)

class FakeRedis:
    """Capture all .set() calls in-memory."""
    def __init__(self):
        self.store = {}
    def set(self, key, value, ex=None):
        self.store[key] = value

#-- test ------------------------------------------------------------

def test_run_deconvolve_minimal(monkeypatch):

    dummy = DummySelf("task-123")
    fake_redis = FakeRedis()
    monkeypatch.setattr("worker.tasks.redis_client", fake_redis)
    monkeypatch.setattr("worker.tasks.devconvolve", lambda **kwargs: {"ok": True})

    df_counts = pd.DataFrame({"m": [1, 2]})
    df_matrix = pd.DataFrame([[0.1, 0.9], [0.5, 0.5]])
    bootstraps = 2

    # Call the run method directly
    result = run_deconvolve(dummy, df_counts, df_matrix, bootstraps)

    assert result == {"ok": True}
