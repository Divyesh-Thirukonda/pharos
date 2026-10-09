import asyncio
import json
import types

import httpx
from fastapi.testclient import TestClient

from backend import main, search


def test_conjunctive_request_remains_unverified_and_preserves_phone_requirement():
    plan = search.lexical_plan("near miss pedestrian on phone")
    assert len(plan["retrievalQueries"]) == 3
    assert "near miss pedestrian on phone" in plan["requiredEvidence"][0]
    assert any("Phone use" in condition for condition in plan["requiredEvidence"])
    assert "eventCount" not in plan
    assert any("cannot be inferred" in limit for limit in plan["unobservableClaims"])


def test_failed_planner_preserves_literal_user_question(monkeypatch):
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.setenv("WANDB_MODEL", "test-model")
    original = httpx.AsyncClient
    monkeypatch.setattr(search.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(lambda request: httpx.Response(503)), **kwargs))
    result = asyncio.run(search.create_retrieval_plan("potentially speeding cars"))
    assert result["planner"] == "lexical_fallback"
    assert result["retrievalQueries"][0] == "potentially speeding cars"
    assert any("cannot establish physical speed" in limit for limit in result["unobservableClaims"])


def test_planner_cannot_drop_original_condition(monkeypatch):
    monkeypatch.setenv("WANDB_API_KEY", "test-only")
    monkeypatch.setenv("WANDB_MODEL", "test-model")
    def handler(request):
        payload = json.loads(request.content)
        assert payload["response_format"]["type"] == "json_schema"
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"interpretation": "Look for crossing paths", "retrievalQueries": ["pedestrian crossing"], "requiredEvidence": ["Crossing paths are visible"], "unobservableClaims": []})}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(search.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    plan = asyncio.run(search.create_retrieval_plan("near miss pedestrian on phone"))
    assert plan["planner"] == "wandb"
    assert plan["retrievalQueries"][0] == "near miss pedestrian on phone"
    assert "near miss pedestrian on phone" in plan["requiredEvidence"][0]
    assert any("simple proximity is insufficient" in item for item in plan["requiredEvidence"])
    assert any("Phone use" in item for item in plan["requiredEvidence"])
    assert any("cannot be inferred" in item for item in plan["unobservableClaims"])


def test_retrieval_fuses_candidates_but_never_counts_them_as_events(monkeypatch):
    monkeypatch.delenv("WANDB_API_KEY", raising=False)
    async def request(path, body):
        if body["query"] == "near misses":
            return {"results": [], "llm_synthesis": "There were seven near misses"}
        return {"results": [{"source": "s3://team/one.mp4", "location": "new_york"}, {"source": "s3://team/two.mp4", "location": "new_york"}], "llm_synthesis": "There were seven near misses"}
    monkeypatch.setattr(main, "vss", types.SimpleNamespace(configured=True, request=request))
    result = TestClient(main.app).post("/api/evidence/search", json={"query": "near misses", "location": "new_york"}).json()
    assert result["mode"] == "connected"
    assert len(result["clips"]) == 2
    assert result["candidateCount"] == 2
    assert result["eventCount"] is None
    assert all(clip["verificationStatus"] == "not_analyzed" for clip in result["clips"])
    assert "seven near misses" not in json.dumps(result)


def test_partial_retrieval_retains_successful_candidates(monkeypatch):
    monkeypatch.delenv("WANDB_API_KEY", raising=False)
    async def request(path, body):
        if body["query"] == "near misses":
            raise httpx.ConnectError("provider outage")
        return {"results": [{"source": "s3://team/one.mp4"}]}
    monkeypatch.setattr(main, "vss", types.SimpleNamespace(configured=True, request=request))
    result = TestClient(main.app).post("/api/evidence/search", json={"query": "near misses"}).json()
    assert result["partialSearch"] is True
    assert result["candidateCount"] == 1
    assert result["eventCount"] is None


def test_distracted_walker_ranking_keeps_phone_with_walking_actor():
    query = "distracted walker almost hit"
    walking = search.candidate_relevance(query, "A pedestrian walks across the road looking at a phone. A car drives past.")
    ordinary = search.candidate_relevance(query, "Pedestrians cross a crosswalk. A car drives past.")
    unrelated_phone = search.candidate_relevance(query, "A cyclist stands by a bicycle with a mounted phone. Pedestrians walk in the background.")
    assert walking > ordinary
    assert walking > unrelated_phone
    assert search.lexical_plan(query)["requiredEvidence"]


def test_obstruction_ranking_requires_blockage_at_requested_location():
    query = "Obstructed crosswalk"
    obstruction = search.candidate_relevance(query, "A barricade partially blocks the crosswalk.")
    lane = search.candidate_relevance(query, "A van obstructs the lane. Pedestrians cross the crosswalk.")
    ordinary = search.candidate_relevance(query, "Pedestrians cross the crosswalk beside a parked truck.")
    assert obstruction > lane
    assert obstruction > ordinary


def test_real_cached_review_promotes_only_same_query_source(monkeypatch, tmp_path):
    import time
    from backend import vision
    monkeypatch.delenv('WANDB_API_KEY', raising=False)
    rows = [{'source': 's3://team/ordinary.mp4'}, {'source': 's3://team/phone.mp4'}]
    clip = main.normalize_clip(rows[1])
    directory = tmp_path / 'verified'
    directory.mkdir()
    (directory / 'window.mp4').write_bytes(b'actual analyzed fixture')
    monkeypatch.setattr(vision, 'JOB_DIR', tmp_path)
    monkeypatch.setattr(vision, 'jobs', {'verified': {'id': 'verified', 'status': 'completed', 'query': 'Pedestrian phone crossing',
        'source': {'id': clip['id'], 'sourceKind': 'recorded_video'}, '_createdEpoch': time.time(),
        'analysis': {'verdict': 'supported'}, 'mediaUrl': 'api/vision/jobs/verified/media'}})
    async def request(path, body):
        return {'results': rows}
    monkeypatch.setattr(main, 'vss', types.SimpleNamespace(configured=True, request=request))
    client = TestClient(main.app)
    result = client.post('/api/evidence/search', json={'query': 'Pedestrian phone crossing'}).json()
    assert result['clips'][0]['id'] == clip['id']
    assert result['clips'][0]['verificationStatus'] == 'supported'
    assert result['clips'][0]['mediaUrl'] == 'api/vision/jobs/verified/media'
    different = client.post('/api/evidence/search', json={'query': 'pedestrian almost hit'}).json()
    assert all(c['verificationStatus'] == 'not_analyzed' for c in different['clips'])
    assert all(c['mediaUrl'].startswith('api/evidence/') for c in different['clips'])
