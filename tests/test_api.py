import time

from fastapi.testclient import TestClient


def _wait_for_scan(client: TestClient, scan_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/scans/{scan_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"completed", "failed"}:
            return body
        time.sleep(0.05)
    raise AssertionError(f"scan {scan_id} did not finish")


class TestWatches:
    def test_create_and_get_watch(self, client: TestClient) -> None:
        created = client.post("/watches/", json={"query": "stoic cosmology"})
        assert created.status_code == 201
        body = created.json()
        assert body["query"] == "stoic cosmology"
        fetched = client.get(f"/watches/{body['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == body["id"]

    def test_create_watch_requires_query(self, client: TestClient) -> None:
        assert client.post("/watches/", json={"query": "  "}).status_code == 422

    def test_missing_watch_returns_404(self, client: TestClient) -> None:
        assert client.get("/watches/missing").status_code == 404


class TestScans:
    def test_scan_completes_with_findings(self, client: TestClient) -> None:
        watch = client.post("/watches/", json={"query": "Meditations"}).json()
        started = client.post(f"/watches/{watch['id']}/scans")
        assert started.status_code == 202
        scan = _wait_for_scan(client, started.json()["id"])
        assert scan["status"] == "completed"
        assert scan["finding_count"] == 3

        pending = client.get("/findings/", params={"status": "pending"})
        assert pending.status_code == 200
        findings = pending.json()["findings"]
        assert len(findings) == 3
        assert all(item["status"] == "pending" for item in findings)
        assert all("example.com" in item["url"] for item in findings)

    def test_scan_unknown_watch_returns_404(self, client: TestClient) -> None:
        assert client.post("/watches/nope/scans").status_code == 404

    def test_sse_replays_completed_scan(self, client: TestClient) -> None:
        watch = client.post("/watches/", json={"query": "Circe"}).json()
        scan_id = client.post(f"/watches/{watch['id']}/scans").json()["id"]
        _wait_for_scan(client, scan_id)

        with client.stream("GET", f"/scans/{scan_id}/events") as stream:
            assert stream.status_code == 200
            text = "".join(stream.iter_text())
        assert "event: scan.started" in text
        assert "event: scan.finding" in text
        assert "event: scan.completed" in text
        assert text.count("event: scan.finding") == 3


class TestReview:
    def test_approve_and_deny(self, client: TestClient) -> None:
        watch = client.post("/watches/", json={"query": "Dune"}).json()
        scan_id = client.post(f"/watches/{watch['id']}/scans").json()["id"]
        _wait_for_scan(client, scan_id)
        findings = client.get("/findings/").json()["findings"]
        first, second = findings[0], findings[1]

        approved = client.post(f"/findings/{first['id']}/approve")
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        denied = client.post(f"/findings/{second['id']}/deny")
        assert denied.status_code == 200
        assert denied.json()["status"] == "denied"

        stats = client.get("/stats").json()
        assert stats["approved"] == 1
        assert stats["denied"] == 1
        assert stats["pending"] == 1

    def test_denied_urls_are_skipped_on_next_scan(self, client: TestClient) -> None:
        watch = client.post("/watches/", json={"query": "Solaris"}).json()
        scan_id = client.post(f"/watches/{watch['id']}/scans").json()["id"]
        _wait_for_scan(client, scan_id)
        finding = client.get("/findings/").json()["findings"][0]
        client.post(f"/findings/{finding['id']}/deny")

        second_id = client.post(f"/watches/{watch['id']}/scans").json()["id"]
        second = _wait_for_scan(client, second_id)
        assert second["finding_count"] == 2
        urls = {item["url"] for item in client.get("/findings/", params={"scan_id": second_id}).json()["findings"]}
        assert finding["url"] not in urls

    def test_review_unknown_finding_returns_404(self, client: TestClient) -> None:
        assert client.post("/findings/missing/approve").status_code == 404


class TestDocs:
    def test_root_redirects_to_docs(self, client: TestClient) -> None:
        response = client.get("/", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert response.headers["location"] == "/docs"

    def test_openapi_has_watch_paths(self, client: TestClient) -> None:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/watches/" in paths
        assert "/watches/{watch_id}/scans" in paths
        assert "/scans/{scan_id}/events" in paths
        assert "/findings/{finding_id}/approve" in paths
