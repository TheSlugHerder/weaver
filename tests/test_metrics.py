from src.weaver import metrics


def test_metrics_module_exports():
    assert hasattr(metrics, "redis_up")
    assert hasattr(metrics, "rate_limiter_fallbacks")


def test_metrics_response_media_type():
    resp = metrics.metrics_response()
    assert resp.media_type == metrics.CONTENT_TYPE_LATEST
