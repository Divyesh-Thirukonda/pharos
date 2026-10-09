import json
import math

import pytest

from backend.tracking import build_tracks


def detection(x, y=0.4, label="car", width=0.08, height=0.08, confidence=0.9):
    return {"label": label, "confidence": confidence,
            "bbox": [x * 1000, y * 500, (x + width) * 1000, (y + height) * 500]}


def frame(index, *detections, time=None):
    return {"frameIndex": index, "timeSec": index / 4 if time is None else time,
            "shape": [500, 1000], "detections": list(detections)}


def test_observed_pixel_boxes_become_normalized_track_and_supported_projection():
    frames = [frame(i, detection(0.1 + i * 0.01)) for i in range(6)]
    result = build_tracks(frames)
    track, = result["tracks"]
    assert result["coordinateSpace"] == "normalized_image"
    assert track["observationCount"] == 6
    assert track["observations"][0]["bbox"] == [0.1, 0.4, 0.18, 0.48]
    assert track["observations"][0]["footpoint"] == [0.14, 0.48]
    assert track["forecasts"][0]["frameIndex"] == 3
    assert track["forecasts"][0]["velocity"] == [0.04, 0.0]
    assert track["forecasts"][-1]["points"][-1] == [0.27, 0.48]
    assert track["forecasts"][-1]["horizonSec"] == 2
    assert result["potentialConflicts"] == []
    assert build_tracks(frames) == result
    json.dumps(result, allow_nan=False)


def test_less_than_four_observations_cannot_project():
    result = build_tracks([frame(i, detection(0.1 + i * 0.01)) for i in range(3)])
    assert not result["tracks"][0]["forecasts"]


def test_missing_detection_ends_identity_and_requires_new_evidence():
    frames = [frame(i, detection(0.1 + i * 0.01)) for i in range(4)]
    frames += [frame(4)] + [frame(i, detection(0.1 + i * 0.01)) for i in range(5, 8)]
    first, second = build_tracks(frames)["tracks"]
    assert first["observationCount"] == 4
    assert second["observationCount"] == 3
    assert second["trackId"] != first["trackId"]
    assert not second["forecasts"]


@pytest.mark.parametrize("last", [frame(4, detection(0.14)), frame(3, detection(0.13), time=4)])
def test_missing_frame_or_timestamp_gap_cannot_extend_track(last):
    result = build_tracks([frame(i, detection(0.1 + i * 0.01)) for i in range(3)] + [last])
    assert [item["observationCount"] for item in result["tracks"]] == [3, 1]
    assert not any(item["forecasts"] for item in result["tracks"])


def test_jump_and_class_change_do_not_swap_identity():
    result = build_tracks([frame(0, detection(0.1)), frame(1, detection(0.7)),
                           frame(2, detection(0.71, label="person"))])
    assert [item["observationCount"] for item in result["tracks"]] == [1, 1, 1]


def test_ambiguous_overlapping_detections_break_previous_identity():
    frames = [frame(i, detection(0.1 + i * 0.01)) for i in range(4)]
    frames.append(frame(4, detection(0.14), detection(0.145)))
    frames.append(frame(5, detection(0.15)))
    result = build_tracks(frames)
    assert result["tracks"][0]["observationCount"] == 4
    assert all(item["observationCount"] == 1 for item in result["tracks"][1:])
    assert not any(item["forecasts"] for item in result["tracks"][1:])


def test_converging_supported_boxes_report_only_image_space_overlap():
    frames = [frame(i, detection(0.2 + i * 0.01), detection(0.46 - i * 0.01, label="bicycle")) for i in range(5)]
    result = build_tracks(frames)
    assert len(result["tracks"]) == 2
    assert result["potentialConflicts"]
    flag = result["potentialConflicts"][0]
    assert flag["label"] == "Potential projected image overlap"
    assert flag["physicalCalibration"] is False
    assert 0 < flag["projectedOffsetSec"] <= 2
    assert flag["trackIds"] == ["track-001", "track-002"]
    assert "ttc" not in json.dumps(result).lower()


def test_stationary_or_diverging_objects_do_not_flag_conflict():
    for frames in ([frame(i, detection(0.2), detection(0.46, label="bicycle")) for i in range(5)],
                   [frame(i, detection(0.2 - i * 0.01), detection(0.46 + i * 0.01, label="bicycle")) for i in range(5)]):
        assert build_tracks(frames)["potentialConflicts"] == []


def test_projection_stops_at_scene_edge():
    result = build_tracks([frame(i, detection(0.83 + i * 0.01)) for i in range(5)])
    forecast = result["tracks"][0]["forecasts"][-1]
    assert 0 < forecast["horizonSec"] < 2
    assert all(0 <= value <= 1 for box in forecast["boxes"] for value in box)


def test_abrupt_reversal_does_not_create_projection_from_noisy_motion():
    result = build_tracks([frame(i, detection(x)) for i, x in enumerate([0.1, 0.12, 0.10, 0.12])])
    assert not any(track["forecasts"] for track in result["tracks"])


def test_invalid_low_confidence_and_nonfinite_boxes_are_not_evidence():
    nan_box = detection(0.1)
    nan_box["bbox"][0] = math.nan
    result = build_tracks([frame(0, nan_box, detection(0.2, confidence=0.2), detection(0.3, width=-0.1))])
    assert result["tracks"] == []
    assert result["potentialConflicts"] == []
    json.dumps(result, allow_nan=False)


def test_frame_shape_change_resets_track_and_bad_cadence_is_rejected():
    changed = frame(1, detection(0.11))
    changed["shape"] = [1000, 2000]
    assert len(build_tracks([frame(0, detection(0.1)), changed])["tracks"]) == 2
    with pytest.raises(ValueError):
        build_tracks([], sample_fps=math.nan)
    with pytest.raises(ValueError):
        build_tracks([frame(0), frame(0)])
