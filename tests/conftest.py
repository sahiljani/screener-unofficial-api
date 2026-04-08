import pytest
from collections import defaultdict, deque

from app.main import app


@pytest.fixture(autouse=True)
def reset_app_state_between_tests():
    app.state.api_key = None
    app.state.rate_limit_per_minute = 120
    app.state.rate_limit_backend = 'memory'
    app.state.redis_client = None
    app.state.rate_buckets = defaultdict(deque)
    app.state.metrics = {
        'requests_total': 0,
        'auth_failed_total': 0,
        'rate_limited_total': 0,
    }
    yield
