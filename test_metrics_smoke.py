
def test_metrics_smoke(client):
    # Trigger at least one request so middleware records metrics
    r = client.get("/api/prompt-templates/health")
    assert r.status_code == 200

    # Now scrape /metrics
    m = client.get("/metrics")
    assert m.status_code == 200
    ctype = m.headers.get("content-type", "")
    assert "text/plain" in ctype and "version=0.0.4" in ctype

    body = m.text
    # Core HTTP metric should be present
    assert "starlette_requests_total" in body
    # Our domain metrics should be registered (may be zero) 
    assert "prompter_prompt_results_insert_total" in body
