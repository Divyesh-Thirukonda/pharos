import asyncio
import json
import os
import sys
import types

import httpx
from fastapi.testclient import TestClient

from backend import main


def row(identifier, on="East 34th Street", cross="3 Avenue", lat="40.746", lon="-73.979", injured="0", **extras):
    return {"collision_id": identifier, "borough": "MANHATTAN", "on_street_name": on, "off_street_name": cross, "latitude": lat, "longitude": lon, "number_of_persons_injured": injured, **extras}


def test_street_grouping_deduplicates_and_excludes_unlocated_collisions():
    data = [row("1", injured="2", contributing_factor_vehicle_1="Failure to Yield Right-of-Way", contributing_factor_vehicle_2="Failure to Yield Right-of-Way"),
            row("2", on="3 avenue", cross="E 34 ST", lat="40.748", number_of_persons_killed="1"),
            row("1", injured="2"), row("3", cross=""), row("4", lat="0"), row("5", lat="NaN")]
    result = main.aggregate_crashes(data)
    assert len(result["intersections"]) == 1
    item = result["intersections"][0]
    assert item["crashes"] == 2
    assert item["injuryCrashes"] == 1
    assert item["injuries"] == 2
    assert item["fatalities"] == 1
    assert item["lat"] == 40.747
    assert item["factors"] == [{"name": "Failure to Yield Right-of-Way", "count": 1}]
    assert item["locationAccuracy"] == "approximate"
    assert result["excludedRows"] == 3


def test_directional_streets_are_not_conflated():
    result = main.aggregate_crashes([row("1", on="EAST 34 STREET"), row("2", on="WEST 34 STREET")])
    assert len(result["intersections"]) == 2


def test_hourly_crash_counts_use_reported_times_without_inventing_midnight():
    rows = [row("1", crash_time="00:15"), row("2", crash_time="9:30"), row("2", crash_time="10:00"),
            row("3", crash_time="23:59:00"), row("4", crash_time=None), row("5", crash_time="24:00"),
            row("6", cross="", crash_time="12:20"), row("7", borough="QUEENS", crash_time="13:00")]
    data = main.aggregate_crashes(rows)
    intersection = data["intersections"][0]
    assert len(intersection["hourlyCounts"]) == 24
    assert intersection["hourlyCounts"][0] == 1
    assert intersection["hourlyCounts"][9] == 1
    assert intersection["hourlyCounts"][10] == 0  # Duplicate was excluded.
    assert intersection["hourlyCounts"][23] == 1
    assert intersection["hourlyKnownCrashes"] == 3
    assert intersection["hourlyMissingCrashes"] == 2
    assert sum(data["hourlyCounts"]) == 4  # Includes unlocated Manhattan row.
    assert data["hourlyCounts"][12] == 1
    assert data["hourlyCounts"][13] == 0  # Manhattan scope, not citywide NYC.
    assert data["hourlyKnownCrashes"] + data["hourlyMissingCrashes"] == 6
    assert data["hourlyTimeZone"] == "America/New_York"


def test_focus_context_is_preserved_outside_top100_without_changing_ranking():
    rows = [row(str(i), on=f"E {i + 50} ST", injured="1", crash_time="12:00") for i in range(100)]
    rows.append(row("focus", on="AVENUE OF THE AMERICAS", cross="W 23 ST", crash_time="17:30"))
    data = main.aggregate_crashes(rows)
    assert len(data["intersections"]) == 100
    focus = data["focusIntersections"][0]
    assert focus["rankByInjuryCrashes"] == 101
    assert focus["hourlyCounts"][17] == 1
    assert focus["id"] not in {item["id"] for item in data["intersections"]}


def test_focused_history_outside_top100_can_be_used_for_assessment(monkeypatch):
    async def data():
        return {"intersections": [], "metadata": {"focusIntersections": [{"id": "focus", "crashes": 10, "hourlyCounts": [0] * 24, "cameras": []}]}}
    async def review(context, clips, query):
        assert context["id"] == "focus" and context["crashes"] == 10
        assert "cameras" not in context
        return {"mode": "connected"}
    monkeypatch.setattr(main, "intersections", data)
    monkeypatch.setattr(main, "assessment_runner", lambda: review)
    response = TestClient(main.app).post("/api/assessments", json={"intersectionId": "focus"})
    assert response.status_code == 200 and response.json()["mode"] == "connected"


def test_service_operation_status_does_not_equate_configuration_with_success(monkeypatch):
    monkeypatch.setattr(main, "service_events", {})
    assert main.operation_status("wandb", True)["status"] == "unverified"
    assert main.operation_status("wandb", False)["status"] == "unavailable"
    main.record_service_result("wandb", True, "Validated response.", "public-model-id")
    connected = main.operation_status("wandb", True)
    assert connected["status"] == "connected" and connected["lastSuccessAt"]
    main.service_events["wandb"]["_checkedEpoch"] -= 901
    assert main.operation_status("wandb", True)["status"] == "stale"
    main.record_service_result("wandb", False, "The source timed out.")
    failed = main.operation_status("wandb", True)
    assert failed["status"] == "unavailable"
    assert failed["lastSuccessAt"] == connected["lastSuccessAt"]


def test_system_status_uses_cheap_authenticated_health_and_runtime_evidence(monkeypatch):
    for key, value in {"COSMOS3_REASON_URL": "https://cosmos.test", "YOLO_URL": "https://yolo.test", "GPU_BEARER_TOKEN": "private-gpu-token", "WANDB_API_KEY": "private-wandb-key", "VSS_URL": "https://vss.test", "VSS_USERNAME": "team-12", "VSS_PASSWORD": "private-password"}.items():
        monkeypatch.setenv(key, value)
    for key in ("WEAVE_PROJECT", "WEAVE_ENABLED"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(main, "service_events", {})
    monkeypatch.setattr(main, "_gpu_health", {})
    monkeypatch.setattr(main, "_gpu_health_key", None)
    monkeypatch.setattr(main, "_gpu_health_at", 0)
    monkeypatch.setattr(main, "_gpu_health_lock", asyncio.Lock())
    requests = []
    def handler(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.headers["authorization"] == "Bearer private-gpu-token"
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "nvidia/cosmos3-nano-reasoner"}]})
        assert request.url.path == "/healthz"
        return httpx.Response(200, json={"ok": True, "model_loaded": False})
    original = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    client = TestClient(main.app)
    response = client.get("/api/system/status")
    services = response.json()["services"]
    assert services["cosmos"]["status"] == "connected"
    assert services["cosmos"]["lastInferenceAt"] is None
    assert services["yolo"]["status"] == "unavailable"  # HTTP200 is not readiness.
    assert services["wandb"]["status"] == services["vss"]["status"] == "unverified"
    assert services["weave"]["status"] == services["cursor"]["status"] == "unavailable"
    assert response.headers["cache-control"] == "no-store"
    assert "private-" not in response.text
    client.get("/api/system/status")
    assert len(requests) == 2  # Shared 30s health cache; no generation requests.


def test_socrata_off_street_field_is_cross_street_not_address_field():
    result = main.aggregate_crashes([row("1", cross="", cross_street_name="100 EAST 34 STREET")])
    assert result["intersections"] == []
    assert result["excludedRows"] == 1


def test_rank_is_injury_crash_count_not_injury_severity_weight():
    result = main.aggregate_crashes([row("1", on="E 34 ST", injured="1"), row("2", on="E 34 ST", injured="1"),
                                    row("3", on="E 35 ST", injured="20", number_of_persons_killed="2")])
    first, second = result["intersections"]
    assert first["streets"] == ["3 AVE", "E 34 ST"]
    assert first["injuryCrashes"] == 2
    assert first["riskScore"] == 100
    assert second["riskScore"] == 50
    assert "historicalBurden" not in first


def test_cache_retains_timestamp_and_marks_stale_on_source_failure(tmp_path):
    async def run():
        cache = main.PublicCache(tmp_path)
        async def success():
            return {"actual": 12}
        async def failure():
            raise httpx.ConnectError("private URL must not appear")
        data, first = await cache.get("public", 0, success)
        repeated, stale = await cache.get("public", 0, failure)
        assert repeated == data
        assert stale["mode"] == "stale"
        assert stale["fetchedAt"] == first["fetchedAt"]
        assert "private URL" not in stale["error"]
    asyncio.run(run())


def test_auth_relogs_once_after_expired_token(monkeypatch):
    monkeypatch.setenv("VSS_URL", "https://vss.test")
    monkeypatch.setenv("VSS_USERNAME", "team-12")
    monkeypatch.setenv("VSS_PASSWORD", "test-only")
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("login"):
            return httpx.Response(200, json={"access_token": f"token-{calls.count(request.url.path)}"})
        if request.headers["authorization"] == "Bearer token-1":
            return httpx.Response(401)
        return httpx.Response(200, json={"results": []})
    original = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result = asyncio.run(main.VSSClient().request("/api/v1/search", {"query": "turning"}))
    assert result == {"results": []}
    assert calls == ["/api/v1/auth/login", "/api/v1/search", "/api/v1/auth/login", "/api/v1/search"]


def test_unconfigured_services_are_honestly_unavailable(monkeypatch):
    for key in ("VSS_URL", "INGRESS_URL", "VSS_USERNAME", "TEAM_USERNAME", "VSS_PASSWORD", "WANDB_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    client = TestClient(main.app)
    health = client.get("/api/health").json()
    assert health["services"]["vss"]["configured"] is False
    result = client.post("/api/evidence/search", json={"query": "pedestrian turning conflict", "location": "new_york"}).json()
    assert result["mode"] == "unavailable" and result["clips"] == []
    assessment = client.post("/api/assessments", json={}).json()
    assert assessment["source"] == "curated_guidance"
    assert assessment["inferenceStatus"] == "unavailable"
    assert assessment["factors"] == []


def test_media_requires_retrieved_evidence_allowlist():
    client = TestClient(main.app)
    response = client.get("/api/evidence/not-searched/media?source=http://127.0.0.1/private")
    assert response.status_code == 404


def test_media_preserves_range_without_exposing_token(monkeypatch):
    monkeypatch.setenv("VSS_URL", "https://vss.test")
    monkeypatch.setenv("VSS_USERNAME", "team-12")
    monkeypatch.setenv("VSS_PASSWORD", "test-only")
    monkeypatch.setattr(main, "vss", main.VSSClient())
    monkeypatch.setattr(main, "evidence_records", {"known": {"source": "s3://team-12/segment.mp4"}})
    class Bytes(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"abc"
    def handler(request):
        if request.url.path.endswith("login"):
            return httpx.Response(200, json={"access_token": "private-test-token"})
        assert request.url.params["source"] == "s3://team-12/segment.mp4"
        assert request.headers["range"] == "bytes=0-2"
        return httpx.Response(206, stream=Bytes(), headers={"Content-Type": "video/mp4", "Content-Range": "bytes 0-2/100", "Content-Length": "3", "Accept-Ranges": "bytes"})
    original = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    response = TestClient(main.app).get("/api/evidence/known/media", headers={"Range": "bytes=0-2"})
    assert response.status_code == 206
    assert response.content == b"abc"
    assert response.headers["content-range"] == "bytes 0-2/100"
    assert "private-test-token" not in str(response.headers)


def test_clip_does_not_infer_recording_date_or_exact_location():
    clip = main.normalize_clip({"source": "s3://team/20261008_clip.mp4", "location": "new_york", "upload_timestamp": "2026-10-09", "similarity_score": 0.9})
    assert clip["recordedAt"] is None
    assert clip["uploadedAt"] == "2026-10-09"
    assert clip["measurementStatus"] == "not_calibrated"
    assert clip["locationAccuracy"] == "source_label_only"
    assert clip["isLive"] is False


def test_distinct_intervals_in_one_source_have_distinct_evidence_ids():
    a = main.normalize_clip({"source": "s3://team/parent.mp4", "segment_start_sec": 0, "segment_end_sec": 5})
    b = main.normalize_clip({"source": "s3://team/parent.mp4", "segment_start_sec": 5, "segment_end_sec": 10})
    assert a["id"] != b["id"]
    assert a["mediaUrl"] != b["mediaUrl"]


def test_inference_cannot_return_unmeasured_motion_estimates(monkeypatch):
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.setenv("WANDB_MODEL", "test-model")
    output = {"summary": "A vehicle traveled at 40 mph.", "factors": [], "recommendations": [{"title": "Check the evidence", "detail": "Review video.", "evidenceIds": [], "sourceUrl": main.GUIDANCE[0]["sourceUrl"], "kind": "next_measurement"}], "limitations": []}
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(output)}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    response = asyncio.run(main.infer_assessment(None, [], "Assess the crossing"))
    assert response["mode"] == "unavailable"
    assert response["source"] == "curated_guidance"
    assert "40 mph" not in json.dumps(response)


def test_inference_prefers_instruction_model_and_handles_empty_truncation(monkeypatch):
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.delenv("WANDB_MODEL", raising=False)
    posts = []
    def handler(request):
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "Qwen/Qwen3.8-27B"}, {"id": "vendor/Thinking-Instruct"}, {"id": "vendor/Text-Instruct"}]})
        body = json.loads(request.content)
        posts.append(body)
        return httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": None}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result = asyncio.run(main.infer_assessment(None, [], "Review this crossing"))
    assert posts[0]["model"] == "vendor/Text-Instruct"
    assert posts[0]["max_tokens"] == 4096
    assert posts[0]["response_format"]["type"] == "json_schema"
    assert posts[0]["response_format"]["json_schema"]["strict"] is True
    assert result["mode"] == "unavailable"
    assert "output limit" in result["error"]


def test_inference_accepts_valid_structured_assessment(monkeypatch):
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.setenv("WANDB_MODEL", "test-model")
    output = {"summary": "Collect crossing evidence for review.", "factors": [], "recommendations": [{"title": "Review the crossing", "detail": "Collect calibrated video.", "evidenceIds": [], "sourceUrl": main.GUIDANCE[0]["sourceUrl"], "kind": "next_measurement"}], "limitations": []}
    def handler(request):
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(output)}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result = asyncio.run(main.infer_assessment(None, [], "Review this crossing"))
    assert result["mode"] == "connected"
    assert result["source"] == "wandb_inference"
    assert result["recommendations"][0]["sourceUrl"] == main.GUIDANCE[0]["sourceUrl"]


def test_assessment_schema_limits_citations_to_provided_sources():
    schema = main.assessment_schema({"clip-one"}, has_history=False)
    factor = schema["$defs"]["AssessmentFactor"]
    recommendation = schema["$defs"]["AssessmentRecommendation"]
    assert factor["properties"]["evidenceIds"]["items"]["enum"] == ["clip-one"]
    assert "historical_report" not in factor["properties"]["source"]["enum"]
    assert "" not in recommendation["properties"]["sourceUrl"]["enum"]
    assert set(recommendation["properties"]["sourceUrl"]["enum"]) == {main.CRASH_PAGE, *(g["sourceUrl"] for g in main.GUIDANCE)}
    for node in [schema, *schema["$defs"].values()]:
        assert node["additionalProperties"] is False
        assert set(node["required"]) == set(node["properties"])
    empty = main.assessment_schema(set(), has_history=True)
    assert empty["$defs"]["AssessmentFactor"]["properties"]["evidenceIds"]["maxItems"] == 0


def test_html_does_not_reuse_colliding_size_and_mtime_etag(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    index = dist / "index.html"
    index.write_text("<html>old</html>")
    os.utime(index, (0, 0))
    assets = dist / "assets"
    assets.mkdir()
    (assets / "app-abc.js").write_text("const a = 1;")
    client = TestClient(main.FrontendFiles(directory=str(dist), html=True))
    first = client.get("/")
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store, max-age=0"
    assert "etag" not in first.headers
    assert "last-modified" not in first.headers
    index.write_text("<html>new</html>")
    os.utime(index, (0, 0))
    response = client.get("/", headers={"If-None-Match": '"old-etag"', "If-Modified-Since": "Thu, 01 Jan 1970 00:00:00 GMT"})
    assert response.status_code == 200
    assert response.text == "<html>new</html>"
    assert client.get("/assets/app-abc.js").headers.get("etag")


def test_optional_weave_wraps_real_assessment_without_secret_arguments(monkeypatch):
    monkeypatch.setenv("WEAVE_PROJECT", "test-team/pharos")
    monkeypatch.setenv("WANDB_API_KEY", "secret-test-key")
    monkeypatch.setattr(main, "_weave_runner", None)
    monkeypatch.setattr(main, "_weave_status", "disabled")
    calls = []
    async def assessment(context, clips, query):
        return {"mode": "connected", "summary": "Grounded result"}
    def op():
        def decorate(fn):
            async def wrapper(*args):
                calls.append(args)
                return await fn(*args)
            return wrapper
        return decorate
    fake = types.ModuleType("weave")
    fake.init = lambda project: calls.append(project)
    fake.op = op
    monkeypatch.setitem(sys.modules, "weave", fake)
    monkeypatch.setattr(main, "infer_assessment", assessment)
    result = asyncio.run(main.assessment_runner()(None, [], "Review this crossing"))
    assert result["mode"] == "connected"
    assert calls == ["test-team/pharos", (None, [], "Review this crossing")]
    assert "secret-test-key" not in str(calls)


def test_search_preserves_clips_with_string_or_structured_synthesis(monkeypatch):
    for synthesis in ("An indexed turning interaction.", {"response": "An indexed turning interaction."}, None):
        async def request(path, body):
            return {"results": [{"source": "s3://team-12/segment.mp4", "segment_start_sec": 5, "segment_end_sec": 10, "location": "new_york"}], "llm_synthesis": synthesis}
        monkeypatch.setattr(main, "vss", types.SimpleNamespace(configured=True, request=request))
        result = TestClient(main.app).post("/api/evidence/search", json={"query": "turning conflict"}).json()
        assert result["mode"] == "connected"
        assert len(result["clips"]) == 1
        assert result["clips"][0]["mediaStartSec"] == 0
        assert isinstance(result["summary"], str)
