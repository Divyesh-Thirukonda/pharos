from backend.nearmiss import measure


def frame(t, car_x, ped_x):
    return {"timeSec": t, "detections": [
        {"label": "car", "confidence": 0.9, "bbox": [car_x, 300, car_x + 150, 400]},
        {"label": "person", "confidence": 0.9, "bbox": [ped_x, 310, ped_x + 30, 400]}]}


def test_car_passes_close_to_walker_then_separates():
    frames = [frame(i * 0.25, 10 + i * 60, 700 - (i - 6) * 3) for i in range(24)]
    result = measure(frames)
    assert result["tracksConsidered"] == 2
    assert result["limitations"]
    for e in result["events"]:
        assert e["min_dist_m"] <= 2.0 and e["peak_closing_mps"] >= 1.5


def test_parked_car_is_not_a_candidate():
    frames = [frame(i * 0.25, 300, 100 + i * 20) for i in range(24)]
    assert measure(frames)["events"] == []


def test_bad_input_is_ignored():
    assert measure(None)["events"] == []
    assert measure([{"timeSec": "x", "detections": [{"label": 1}]}, {"detections": []}])["events"] == []
