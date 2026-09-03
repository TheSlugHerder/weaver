from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Metrics
redis_up = Gauge('weaver_redis_up', 'Redis availability (1=up,0=down)')
rate_limiter_fallbacks = Counter('weaver_rate_limiter_fallbacks_total', 'Count of in-memory fallback occurrences')


def metrics_response() -> Response:
    """Return a Prometheus exposition Response."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
