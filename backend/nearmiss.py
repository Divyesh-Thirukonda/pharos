"""Measured near-miss candidates from YOLO detections of one captured window.

Ported from the PharOS detector (github.com/elmir132/pharos-elmir, nm.py). It pairs a moving
vehicle with a pedestrian or cyclist and reports approximate distance, closing speed and time to
collision. Distances are metres from each box's ground point, scaled by a typical object height:
no camera calibration, so treat them as rough. Output is candidates for human review, never alarms,
and never a statement about who was at fault.
"""
import math
from itertools import combinations

REF_H = {"person": 1.7, "bicycle": 1.7, "motorcycle": 1.5, "car": 1.5, "truck": 3.0, "bus": 3.2}
VRU, VEH = {"person", "bicycle", "motorcycle"}, {"car", "truck", "bus"}
NEAR_M, CLOSE_MPS, SEP_M = 2.0, 1.5, 0.8
MAX_CLOSE_MPS, MIN_VEH_MPS, DEPTH_LO, DEPTH_HI = 12.0, 1.5, 0.6, 1.6


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / ua if ua > 0 else 0.0


def build_tracks(rows):
    by_t = {}
    for t, c, b in rows:
        if c in REF_H:
            by_t.setdefault(t, []).append((c, b))
    tracks = []
    for t in sorted(by_t):
        used = set()
        for c, b in by_t[t]:
            best, bv = None, 0.25
            for i, tr in enumerate(tracks):
                lt, lb = tr["pts"][-1]
                if i in used or tr["cls"] != c or t - lt > 1.0 or t == lt:
                    continue
                v = iou(lb, b)
                if v > bv:
                    best, bv = i, v
            if best is None:
                tracks.append({"cls": c, "pts": [(t, b)]})
            else:
                tracks[best]["pts"].append((t, b))
                used.add(best)
    return [t for t in tracks if len(t["pts"]) >= 6]


def dist_m(ca, ba, cb, bb):
    ga, gb = ((ba[0] + ba[2]) / 2, ba[3]), ((bb[0] + bb[2]) / 2, bb[3])
    sa = REF_H[ca] / max(ba[3] - ba[1], 1.0)
    sb = REF_H[cb] / max(bb[3] - bb[1], 1.0)
    return math.hypot(ga[0] - gb[0], ga[1] - gb[1]) * (sa + sb) / 2


def speed(tr):
    """Median ground speed of a track in m/s (ground point, scaled by typical object height)."""
    cls, v = tr["cls"], []
    for (t0, b0), (t1, b1) in zip(tr["pts"], tr["pts"][1:]):
        dt = t1 - t0
        if dt > 0:
            s = REF_H[cls] / max(b1[3] - b1[1], 1.0)
            v.append(math.hypot((b1[0] + b1[2]) / 2 - (b0[0] + b0[2]) / 2, b1[3] - b0[3]) * s / dt)
    v.sort()
    return v[len(v) // 2] if v else 0.0


def box_at(tr, t):
    return min(tr["pts"], key=lambda p: abs(p[0] - t))[1]


def pair_event(a, b):
    """A vehicle and a pedestrian/cyclist that came close while the vehicle was moving, then moved apart.
    Requires a sustained approach and a sustained separation, a moving vehicle, a plausible closing speed
    and similar apparent depth. Returns None otherwise."""
    veh, vru = (a, b) if a["cls"] in VEH else (b, a)
    if not (veh["cls"] in VEH and vru["cls"] in VRU):
        return None
    bt = {round(t, 3): bx for t, bx in b["pts"]}
    pr = [(t, bx, bt[round(t, 3)]) for t, bx in a["pts"] if round(t, 3) in bt]
    if len(pr) < 6:
        return None
    ts = [p[0] for p in pr]
    raw = [dist_m(a["cls"], p[1], b["cls"], p[2]) for p in pr]
    d = [sum(raw[max(0, i - 1): i + 2]) / len(raw[max(0, i - 1): i + 2]) for i in range(len(raw))]
    cl = [0.0] + [(d[i - 1] - d[i]) / max(ts[i] - ts[i - 1], 1e-6) for i in range(1, len(d))]
    k = min(range(len(d)), key=lambda i: d[i])
    peak = max(cl[: k + 1])
    if d[k] > NEAR_M or peak < CLOSE_MPS or peak > MAX_CLOSE_MPS:
        return None
    if sum(1 for i in range(max(1, k - 3), k + 1) if cl[i] >= CLOSE_MPS) < 2:
        return None  # a single fast sample is noise, not an approach
    j = min(k + 2, len(d) - 1)
    if max(d[k:]) - d[k] < SEP_M or d[j] - d[k] < SEP_M / 2:
        return None  # they did not clearly move apart again
    vs = speed(veh)
    if vs < MIN_VEH_MPS:
        return None  # parked or crawling vehicle
    bv, bp = box_at(veh, ts[k]), box_at(vru, ts[k])
    ratio = (REF_H[veh["cls"]] / max(bv[3] - bv[1], 1.0)) / (REF_H[vru["cls"]] / max(bp[3] - bp[1], 1.0))
    if not DEPTH_LO <= ratio <= DEPTH_HI:
        return None  # probably at different depths, one behind the other
    kc = max(range(k + 1), key=lambda i: cl[i])
    ttc = d[kc] / cl[kc] if cl[kc] > 1e-6 else None
    sev = 0.5 * max(0, 1 - d[k] / NEAR_M) + 0.3 * min(1, peak / 6) + 0.2 * (max(0, 1 - ttc / 2) if ttc else 0)
    return {"classes": [a["cls"], b["cls"]], "t_closest": round(ts[k], 2), "t_start": round(ts[0], 2), "t_end": round(ts[-1], 2),
            "severity": round(sev, 3), "min_dist_m": round(d[k], 2), "peak_closing_mps": round(peak, 2),
            "ttc_s": None if ttc is None else round(ttc, 2), "vehicle_speed_mps": round(vs, 2)}


def find_events(tracks):
    ev = [e for a, b in combinations(tracks, 2) for e in [pair_event(a, b)] if e]
    return sorted(ev, key=lambda e: e["severity"], reverse=True)


LIMITATIONS = [
    "Approximate metres: ground point of each box scaled by typical object height, no camera calibration.",
    "Needs a fixed camera. Archive footage from moving cameras is not measured.",
    "A candidate is a vehicle and a person that came close while the vehicle moved, then separated. A reviewer must confirm it.",
    "No event does not mean safe: detections can be missed and the window is a few seconds.",
]


def measure(frames, min_conf=0.4):
    """frames: [{timeSec, detections:[{label, confidence, bbox:[x1,y1,x2,y2] pixels}]}] -> candidates, most severe first."""
    rows = []
    for fr in frames or []:
        t = fr.get("timeSec")
        if not isinstance(t, (int, float)):
            continue
        for d in fr.get("detections", []):
            box, label, conf = d.get("bbox"), d.get("label"), d.get("confidence")
            if (isinstance(box, (list, tuple)) and len(box) == 4 and isinstance(label, str)
                    and isinstance(conf, (int, float)) and conf >= min_conf):
                rows.append((float(t), label.strip().lower(), [float(x) for x in box]))
    tracks = build_tracks(rows)
    events = find_events(tracks)
    return {"events": events, "tracksConsidered": len(tracks), "limitations": LIMITATIONS}
