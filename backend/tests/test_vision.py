import asyncio
import base64
import copy
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from pydantic import ValidationError

from backend import main, vision


def test_job_requires_one_known_source_and_private_gpu_configuration(monkeypatch):
    with pytest.raises(ValidationError):
        vision.VisionRequest(cameraId="camera", evidenceId="clip")
    with pytest.raises(ValidationError):
        vision.VisionRequest()
    monkeypatch.delenv("GPU_BEARER_TOKEN", raising=False)
    client = TestClient(main.app)
    response = client.post("/api/vision/jobs", json={"cameraId": vision.CAMERAS[0]["id"]})
    assert response.status_code == 503
    monkeypatch.setenv("GPU_BEARER_TOKEN", "secret-test-token")
    monkeypatch.setenv("COSMOS3_REASON_URL", "https://cosmos.test")
    monkeypatch.setenv("YOLO_URL", "https://yolo.test")
    response = client.post("/api/vision/jobs", json={"cameraId": "https://untrusted.test/video.m3u8"})
    assert response.status_code == 404
    assert "secret-test-token" not in client.get("/api/health").text
    assert "secret-test-token" not in client.get("/api/vision/cameras").text


def test_camera_directory_distinguishes_exact_still_camera_from_nearby_live_feeds():
    data = TestClient(main.app).get("/api/vision/cameras").json()
    assert data["focus"]["sourceKind"] == "latest_image"
    assert data["focus"]["cameraId"] == "fcc24aa5-4da0-48f2-aa43-e70e4677517c"
    first, second = data["cameras"][:2]
    assert first["id"] == "511ny-32997" and first["distanceMeters"] == 1343
    assert second["id"] == "511ny-32996" and second["distanceMeters"] == 1384
    assert [c["distanceRank"] for c in data["cameras"]] == list(range(1, len(data["cameras"]) + 1))
    assert all(c["association"] == "nearby_different_intersection" and not c["coverageVerified"] for c in data["cameras"])


def test_detection_boxes_and_times_come_from_actual_frame_output():
    raw = {"frames": [{"frame_index": 2, "shape": [240, 352], "detections": [{"label": "person", "confidence": .9, "bbox": [-5, 20, 30, 250]}, {"label": "car", "confidence": .8, "bbox": [20, 30, 10, 40]}]}]}
    result = vision.normalize_detections(raw, 4, 352, 240)
    frame = result["frames"][0]
    assert frame["timeSec"] == .5
    assert frame["detections"] == [{"label": "person", "confidence": .9, "bbox": [0, 20, 30, 240]}]
    assert result["countsAreFrameDetections"] is True


def test_cosmos_receives_real_video_bytes_and_discovers_actual_model(monkeypatch):
    monkeypatch.setenv("COSMOS3_REASON_URL", "https://cosmos.test")
    monkeypatch.setenv("COSMOS3_REASON_MODEL", "stale-documentation-model")
    monkeypatch.setenv("GPU_BEARER_TOKEN", "private-gpu-token")
    received = []
    def handler(request):
        assert request.headers["authorization"] == "Bearer private-gpu-token"
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "nvidia/current-reasoner"}]})
        received.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "request-1", "choices": [{"finish_reason": "stop", "message": {"content": "A person waits at the curb. The requested collision is not observed."}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(vision.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    raw_video = b"actual video bytes, not an indexed caption"
    encoded = base64.b64encode(raw_video).decode()
    job = {"query": "a collision", "video": {"durationSec": 8, "sha256": "input-hash"}, "models": {}, "timings": {}}
    asyncio.run(vision.run_cosmos(job, encoded))
    request = received[0]
    assert request["model"] == "nvidia/current-reasoner"
    assert request["messages"][0]["content"][1] == {"type": "video_url", "video_url": {"url": "data:video/mp4;base64," + encoded}}
    assert vision.CRITERIA_RULE in request["messages"][0]["content"][0]["text"]
    assert job["cosmosInference"]["reusedIndexedDescription"] is False
    assert job["cosmosInference"]["videoSha256"] == "input-hash"
    assert "private-gpu-token" not in json.dumps(vision.public_job(job))


def test_video_assessment_rejects_unobserved_support_fake_times_and_motion():
    valid = {"verdict": "not_observed", "summary": "No collision observed.", "observations": [], "nextSteps": [], "limitations": ["Low resolution."]}
    vision.validate_assessment(valid, 8, [])
    with pytest.raises(ValueError):
        vision.validate_assessment({**valid, "verdict": "supported"}, 8, [])
    with pytest.raises(ValueError):
        vision.validate_assessment({**valid, "observations": [{"startSec": 7, "endSec": 9}]}, 8, [])
    with pytest.raises(ValueError):
        vision.validate_assessment({**valid, "summary": "The vehicle travels at 30 mph."}, 8, [])


def test_completed_job_media_supports_range_without_arbitrary_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(vision, "JOB_DIR", tmp_path)
    job_id = "a" * 32
    directory = tmp_path / job_id
    directory.mkdir()
    (directory / "window.mp4").write_bytes(b"0123456789abcdef")
    monkeypatch.setattr(vision, "jobs", {job_id: {"mediaUrl": "ready"}})
    response = TestClient(main.app).get(f"/api/vision/jobs/{job_id}/media", headers={"Range": "bytes=0-3"})
    assert response.status_code == 206
    assert response.content == b"0123"
    assert response.headers["cache-control"] == "private, no-store"


def test_strict_schema_requires_model_reported_video_times_and_approved_urls():
    schema = vision.assessment_schema(8, ["https://official.test/guidance"])
    assert schema["$defs"]["NextStep"]["properties"]["sourceUrl"]["enum"] == ["https://official.test/guidance"]
    assert schema["$defs"]["Observation"]["properties"]["startSec"]["anyOf"][0]["maximum"] == 8
    assert set(schema["required"]) == set(schema["properties"])


def test_recorded_camera_tracks_do_not_claim_fixed_camera_forecasts(monkeypatch):
    from backend import tracking
    monkeypatch.setenv("YOLO_URL", "https://yolo.test")
    monkeypatch.setenv("GPU_BEARER_TOKEN", "private-gpu-token")
    original = httpx.AsyncClient
    monkeypatch.setattr(vision.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"frames": [{"frame_index": 0, "shape": [352, 640], "detections": []}]})), **kwargs))
    monkeypatch.setattr(tracking, "build_tracks", lambda *a, **k: {"tracks": [{"observations": [{"frameIndex": 0}], "forecasts": [{"frameIndex": 0}]}], "potentialConflicts": [{"frameIndex": 0}], "limitations": []})
    job = {"source": {"sourceKind": "recorded_video"}, "video": {"fps": 4, "width": 640, "height": 352}, "models": {}, "timings": {}}
    asyncio.run(vision.run_yolo(job, "encoded-real-window"))
    assert job["tracking"]["tracks"][0]["observations"] == [{"frameIndex": 0}]
    assert job["tracking"]["tracks"][0]["forecasts"] == []
    assert job["tracking"]["potentialConflicts"] == []
    assert "camera motion" in job["tracking"]["limitations"][0]


def test_ffmpeg_uses_explicit_system_binary_and_reports_signal_without_stderr(monkeypatch):
    monkeypatch.setenv("IMAGEIO_FFMPEG_EXE", "/usr/bin/ffmpeg")
    received = []
    class FailedProcess:
        returncode = -11
        async def communicate(self):
            return None, b"private input details must not be exposed"
    async def create(*arguments, **kwargs):
        received.append(arguments)
        return FailedProcess()
    monkeypatch.setattr(vision.asyncio, "create_subprocess_exec", create)
    with pytest.raises(HTTPException) as failure:
        asyncio.run(vision.ffmpeg_run(["-version"]))
    assert received == [("/usr/bin/ffmpeg", "-version")]
    assert failure.value.status_code == 502
    assert "signal 11" in failure.value.detail
    assert "private input" not in failure.value.detail


def test_capture_keeps_hls_input_and_transcoding_bounded(tmp_path, monkeypatch):
    received = []
    async def ffmpeg(arguments, timeout=50):
        received.extend(arguments)
        (tmp_path / "window.mp4").write_bytes(b"x" * 2048)
    monkeypatch.setattr(vision, "ffmpeg_run", ffmpeg)
    monkeypatch.setattr(vision, "inspect_video", lambda path: {"durationSec": 8, "fps": 4, "width": 640, "height": 352})
    job = {"id": "test", "source": vision.CAMERAS[0], "timings": {}}
    _, data = asyncio.run(vision.capture_video(job, tmp_path))
    assert received[received.index("-i") + 1] == vision.CAMERAS[0]["streamUrl"]
    assert received[received.index("-protocol_whitelist") + 1] == "http,https,tcp,tls,crypto"
    assert received[received.index("-t") + 1] == "4"
    assert received[received.index("-vf") + 1] == "scale='min(640,iw)':-2,fps=8"
    assert received[received.index("-fs") + 1] == str(vision.MAX_VIDEO_BYTES)
    assert job["video"]["bytes"] == len(data)
    assert job["video"]["sourceCapturedAt"] is None


@pytest.mark.parametrize("verdict,observations", [
    ("not_observed", [{"detail": "Cars move along the roadway.", "startSec": None, "endSec": None, "evidence": "direct_video"}]),
    ("uncertain", []),
])
@pytest.mark.parametrize("source_kind", ["live_video", "recorded_video"])
def test_no_preventive_filler_when_event_absent_or_without_observations(monkeypatch, verdict, observations, source_kind):
    monkeypatch.setenv("WANDB_API_KEY", "private-test-key")
    proposed = {"verdict": verdict, "summary": "The requested conflict is not established.", "observations": observations,
                "nextSteps": [{"title": "Generic safety advice", "detail": "Add a crossing improvement without an observed issue.", "sourceUrl": main.GUIDANCE[0]["sourceUrl"]}],
                "limitations": ["The short window cannot establish conditions outside the view."]}
    received = []
    def handler(request):
        received.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposed)}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(vision.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    job = {"query": "near miss", "cosmosObservation": "Cars move along the roadway. No requested conflict is observed.", "source": {"sourceKind": source_kind}, "video": {"durationSec": 8}, "models": {}, "timings": {}}
    asyncio.run(vision.assess_fresh_video(job))
    assert job["analysis"]["assessmentStatus"] == "connected"
    assert job["analysis"]["verdict"] == verdict
    assert job["analysis"]["observations"] == observations
    assert job["analysis"]["nextSteps"] == []
    assert vision.CRITERIA_RULE in received[0]["messages"][0]["content"]
    source_limit = job["analysis"]["limitations"][1]
    prompt = received[0]["messages"][0]["content"]
    if source_kind == "live_video":
        assert "Live acquisition timestamps" in source_limit
        assert "Archive recording time" not in source_limit
        assert "official camera-registry location" in prompt
        assert "This is an archive clip" not in prompt
    else:
        assert "Archive recording time" in source_limit
        assert "Live acquisition timestamps" not in source_limit
        assert "This is an archive clip" in prompt
        assert "live fixed-camera feed" not in prompt


@pytest.mark.parametrize("single_frame,bounded_interval,expected", [
    (True, False, "uncertain"),
    (True, True, "uncertain"),
    (False, False, "uncertain"),
    (False, True, "supported"),
])
def test_actual_monitoring_regression_requires_temporal_conflict_evidence(single_frame, bounded_interval, expected):
    # Sanitized actual hosted response, job 2c1a8161c773445f94a5dd90c452ada2.
    job = json.loads((Path(__file__).parent / "fixtures" / "single_frame_conflict.json").read_text())
    result = copy.deepcopy(job["analysis"])
    if not single_frame:
        job["cosmosObservation"] = "Across frames from 1 to 2 seconds, the black car moves toward the white car's lane. Review this possible conflict."
    if bounded_interval:
        result["observations"][0].update(startSec=1.0, endSec=2.0)
    original_cosmos = job["cosmosObservation"]
    original_details = [o["detail"] for o in result["observations"]]
    vision.validate_assessment(result, 8, [g["sourceUrl"] for g in main.GUIDANCE])
    vision.apply_evidence_guards(result, job, main.GUIDANCE)
    assert result["verdict"] == expected
    assert result["nextSteps"] == []  # Copied generic guidance is never retained.
    assert job["cosmosObservation"] == original_cosmos
    if expected == "uncertain":
        assert result["modelVerdict"] == "supported"
        assert "not established" in result["summary"]
        assert result["reviewReason"] in result["limitations"]
        for observed, original in zip(result["observations"], original_details):
            assert observed["detail"] == "Unverified model interpretation: " + original
    else:
        assert "reviewReason" not in result


def test_generic_guidance_is_filtered_without_rejecting_a_static_observation():
    job = {"query": "Is a car visible?", "cosmosObservation": "A car is visible in a single frame.", "video": {"fps": 4}}
    result = {"verdict": "supported", "observations": [{"detail": "A car is visible.", "startSec": None, "endSec": None}],
              "nextSteps": [{**main.GUIDANCE[0], "detail": main.GUIDANCE[0]["detail"].upper().replace(" ", "\n")}], "limitations": []}
    vision.apply_evidence_guards(result, job, main.GUIDANCE)
    assert result["verdict"] == "supported"
    assert result["nextSteps"] == []
