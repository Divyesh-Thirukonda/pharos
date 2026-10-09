"""Conservative, window-local association of detections from a fixed camera.

Input boxes are pixels. Output geometry is normalized image coordinates. A
projection is a constant image-velocity box envelope, never a physical path,
time-to-collision measurement, or finding that a near miss occurred.
"""
from __future__ import annotations

from math import hypot, isfinite
from typing import Any


MIN_CONFIDENCE = 0.35
MIN_OBSERVATIONS = 4
HORIZON_SECONDS = 2.0
LIMITATIONS = [
    "Track IDs exist only within this captured window; no cross-camera identity tracking.",
    "Associations use class, bounding-box overlap and image position; they can be wrong.",
    "Projection assumes a fixed camera and short-term constant image velocity; turns and camera movement invalidate it.",
    "Overlapping projected boxes can be separated in depth. These flags do not establish a collision or near miss.",
    "No camera calibration: image-plane tracks carry no physical units. Approximate metres appear only under near-miss candidates, from box ground points.",
    "Missing detections and ambiguous associations end a track; absence of a flag does not establish safety.",
]


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _intersection(a: list[float], b: list[float]) -> list[float]:
    return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def _iou(a: list[float], b: list[float]) -> float:
    overlap = _area(_intersection(a, b))
    return overlap / max(1e-12, _area(a) + _area(b) - overlap)


def _point(box: list[float]) -> list[float]:
    return [(box[0] + box[2]) / 2, box[3]]


def _rounded(values: list[float]) -> list[float]:
    return [round(value, 6) for value in values]


def _normalize_frame(frame: dict, position: int, fps: float) -> dict | None:
    shape = frame.get("shape", [])
    if not isinstance(shape, (list, tuple)) or len(shape) != 2 or not all(_number(x) and x > 0 for x in shape):
        return None
    height, width = shape
    index = frame.get("frameIndex", position)
    time_sec = frame.get("timeSec", position / fps)
    if not isinstance(index, int) or isinstance(index, bool) or index < 0 or not _number(time_sec) or time_sec < 0:
        return None
    detections = []
    raw_detections = frame.get("detections", [])
    if not isinstance(raw_detections, list):
        return None
    for detection in raw_detections:
        if not isinstance(detection, dict):
            continue
        box = detection.get("bbox", [])
        label, confidence = detection.get("label"), detection.get("confidence")
        if (not isinstance(label, str) or not label.strip() or not _number(confidence)
                or not MIN_CONFIDENCE <= confidence <= 1
                or not isinstance(box, (list, tuple)) or len(box) != 4 or not all(_number(x) for x in box)):
            continue
        box = [max(0.0, min(1.0, value / scale)) for value, scale in zip(box, [width, height, width, height])]
        if _area(box) < 0.00001:
            continue
        detections.append({"frameIndex": index, "timeSec": float(time_sec), "label": label.strip().lower(),
                           "bbox": box, "footpoint": _point(box), "confidence": float(confidence)})
    detections.sort(key=lambda d: (d["label"], *d["bbox"], -d["confidence"]))
    # Duplicate or strongly overlapping same-class boxes do not supply reliable
    # identities. Keep observations, but prevent them from extending a track.
    for i, detection in enumerate(detections):
        detection["ambiguous"] = any(i != j and other["label"] == detection["label"]
                                     and _iou(other["bbox"], detection["bbox"]) > 0.55
                                     for j, other in enumerate(detections))
    return {"frameIndex": index, "timeSec": float(time_sec), "shape": tuple(shape), "detections": detections}


def _match_cost(track: dict, detection: dict) -> float | None:
    last = track["observations"][-1]
    if detection["ambiguous"] or track["ambiguous"] or track["label"] != detection["label"]:
        return None
    a, b = last["bbox"], detection["bbox"]
    scale_ratio = _area(b) / _area(a)
    if not 0.5 <= scale_ratio <= 2.0:
        return None
    distance = hypot(*(x - y for x, y in zip(last["footpoint"], detection["footpoint"])))
    gate = min(0.10, max(0.018, 0.6 * hypot(a[2] - a[0], a[3] - a[1])))
    if distance > gate:
        return None
    history = track["observations"]
    if len(history) >= 2:
        previous = history[-2]
        delta = last["timeSec"] - previous["timeSec"]
        forward = detection["timeSec"] - last["timeSec"]
        expected = [p + (p - q) * forward / delta for p, q in zip(last["footpoint"], previous["footpoint"])]
        residual = hypot(*(x - y for x, y in zip(expected, detection["footpoint"])))
        if residual > gate * 0.8:
            return None
    else:
        residual = distance
    return 0.6 * residual / gate + 0.4 * (1 - _iou(a, b))


def _forecast(observations: list[dict], fps: float) -> dict | None:
    if len(observations) < MIN_OBSERVATIONS:
        return None
    recent = observations[-6:]
    last = recent[-1]
    times = [item["timeSec"] - last["timeSec"] for item in recent]
    mean_t = sum(times) / len(times)
    variance_t = sum((value - mean_t) ** 2 for value in times)
    if variance_t <= 0:
        return None
    velocity, residuals = [], []
    for axis in range(2):
        values = [item["footpoint"][axis] for item in recent]
        mean_value = sum(values) / len(values)
        slope = sum((t - mean_t) * (v - mean_value) for t, v in zip(times, values)) / variance_t
        velocity.append(slope)
        residuals.append([v - (mean_value + slope * (t - mean_t)) for t, v in zip(times, values)])
    box = last["bbox"]
    tolerance = max(0.004, min(box[2] - box[0], box[3] - box[1]) * 0.15)
    if max(hypot(x, y) for x, y in zip(*residuals)) > tolerance:
        return None
    # Abrupt reversal/turn or detector jitter is not evidence for a straight
    # future trajectory, even if a least-squares line happens to fit.
    speed = hypot(*velocity)
    if speed < 0.008:
        velocity = [0.0, 0.0]
    else:
        for first, second in zip(recent, recent[1:]):
            step = [b - a for a, b in zip(first["footpoint"], second["footpoint"])]
            step_size = hypot(*step)
            if step_size > tolerance and sum(a * b for a, b in zip(step, velocity)) / (step_size * speed) < 0.7:
                return None
    if max(_area(item["bbox"]) for item in recent) / min(_area(item["bbox"]) for item in recent) > 1.6:
        return None
    offsets, points, boxes = [], [], []
    for step in range(round(HORIZON_SECONDS * fps) + 1):
        offset = step / fps
        shift = [axis * offset for axis in velocity]
        projected = [box[0] + shift[0], box[1] + shift[1], box[2] + shift[0], box[3] + shift[1]]
        if min(projected) < 0 or max(projected) > 1:
            break
        offsets.append(round(offset, 6))
        boxes.append(_rounded(projected))
        points.append(_rounded([last["footpoint"][0] + shift[0], last["footpoint"][1] + shift[1]]))
    if len(points) < 2:
        return None
    return {"frameIndex": last["frameIndex"], "timeSec": last["timeSec"], "horizonSec": offsets[-1],
            "velocity": _rounded(velocity), "offsetsSec": offsets, "points": points, "boxes": boxes,
            "basis": "constant_image_velocity", "physicalCalibration": False}


def _conflicts(frame_forecasts: list[tuple[dict, dict]]) -> list[dict]:
    result = []
    for i, (track_a, a) in enumerate(frame_forecasts):
        for track_b, b in frame_forecasts[i + 1:]:
            if hypot(*a["velocity"]) < 0.008 and hypot(*b["velocity"]) < 0.008:
                continue
            if _area(_intersection(a["boxes"][0], b["boxes"][0])) > 0:
                continue
            initial_distance = hypot(*(x - y for x, y in zip(a["points"][0], b["points"][0])))
            for index in range(1, min(len(a["boxes"]), len(b["boxes"]))):
                overlap = _intersection(a["boxes"][index], b["boxes"][index])
                overlap_fraction = _area(overlap) / min(_area(a["boxes"][index]), _area(b["boxes"][index]))
                future_distance = hypot(*(x - y for x, y in zip(a["points"][index], b["points"][index])))
                if overlap_fraction >= 0.1 and future_distance < initial_distance - 0.005:
                    result.append({"frameIndex": a["frameIndex"], "timeSec": a["timeSec"],
                                   "trackIds": [track_a["trackId"], track_b["trackId"]],
                                   "label": "Potential projected image overlap", "projectedOffsetSec": a["offsetsSec"][index],
                                   "overlapBox": _rounded(overlap), "physicalCalibration": False})
                    break
    return result


def build_tracks(frames: list[dict], sample_fps: float = 4.0) -> dict:
    """Associate adjacent sampled detections; return JSON-ready local geometry.

    A detection frame has ``frameIndex``, ``timeSec``, ``shape: [h, w]`` and
    ``detections: [{label, confidence, bbox: [x1,y1,x2,y2]}]`` in pixels.
    Missing/invalid frames, time gaps and ambiguous matches break associations.
    """
    if not _number(sample_fps) or not 0 < sample_fps <= 60:
        raise ValueError("sample_fps must be finite and between 0 and 60")
    normalized = [_normalize_frame(frame, i, sample_fps) for i, frame in enumerate(frames) if isinstance(frame, dict)]
    normalized = sorted((frame for frame in normalized if frame), key=lambda frame: frame["frameIndex"])
    if len({frame["frameIndex"] for frame in normalized}) != len(normalized):
        raise ValueError("frameIndex must be unique within a captured window")
    tracks: list[dict] = []
    previous = None
    potential_conflicts = []
    for frame in normalized:
        consecutive = (previous is not None and frame["frameIndex"] == previous["frameIndex"] + 1
                       and frame["shape"] == previous["shape"]
                       and 0.65 / sample_fps <= frame["timeSec"] - previous["timeSec"] <= 1.35 / sample_fps)
        active = [track for track in tracks if consecutive and track["observations"][-1]["frameIndex"] == previous["frameIndex"]]
        candidates = []
        for track_index, track in enumerate(active):
            for detection_index, detection in enumerate(frame["detections"]):
                cost = _match_cost(track, detection)
                if cost is not None:
                    candidates.append((cost, track_index, detection_index))
        # Require a clear winner from both sides. Crossing/occluded detections
        # are allowed to start fresh identities, not silently swap identities.
        ambiguous_tracks, ambiguous_detections = set(), set()
        for column, ambiguous in ((1, ambiguous_tracks), (2, ambiguous_detections)):
            for index in {candidate[column] for candidate in candidates}:
                costs = sorted(candidate[0] for candidate in candidates if candidate[column] == index)
                if len(costs) > 1 and costs[1] - costs[0] < 0.15:
                    ambiguous.add(index)
        used_tracks, used_detections = set(), set()
        assigned = {}
        for _, track_index, detection_index in sorted(candidates):
            if (track_index in used_tracks or detection_index in used_detections
                    or track_index in ambiguous_tracks or detection_index in ambiguous_detections):
                continue
            assigned[detection_index] = active[track_index]
            used_tracks.add(track_index)
            used_detections.add(detection_index)
        frame_forecasts = []
        for detection_index, detection in enumerate(frame["detections"]):
            track = assigned.get(detection_index)
            if track is None:
                track = {"trackId": f"track-{len(tracks) + 1:03d}", "label": detection["label"],
                         "observations": [], "forecasts": [], "ambiguous": detection["ambiguous"]}
                tracks.append(track)
            observation = {key: detection[key] for key in ("frameIndex", "timeSec", "bbox", "footpoint", "confidence")}
            track["observations"].append(observation)
            forecast = _forecast(track["observations"], sample_fps)
            if forecast:
                track["forecasts"].append(forecast)
                frame_forecasts.append((track, forecast))
        potential_conflicts.extend(_conflicts(frame_forecasts))
        previous = frame
    for track in tracks:
        track.pop("ambiguous")
        track["observationCount"] = len(track["observations"])
        for observation in track["observations"]:
            observation["bbox"] = _rounded(observation["bbox"])
            observation["footpoint"] = _rounded(observation["footpoint"])
    return {"coordinateSpace": "normalized_image", "sampleFps": float(sample_fps),
            "minConsistentObservations": MIN_OBSERVATIONS, "tracks": tracks,
            "potentialConflicts": potential_conflicts, "limitations": list(LIMITATIONS)}
