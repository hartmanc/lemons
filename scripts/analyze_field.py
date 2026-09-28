"""Stint, pit-stop and pace analysis for the top of the field, from the official laps.

Usage: python3 scripts/analyze_field.py
Writes buttonwillow/data/field.json and field.js (the same data as a script the page can load from disk).
"""
import csv, json, statistics as st
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "buttonwillow" / "data"
TOP = 20
US, RIVAL = "619", "192"  # us, and the class B winner
RED_AT = datetime(2026, 9, 27, 10, 32)  # the day 2 red flag (Pinto rollover) was out at this moment
SLOW = 1.25  # a green lap over 1.25x the car's median is an incident / off-pace lap, not pace
DRIVE_THROUGH = 45  # an in-pit lap costing less than this (s) is a drive-through, not a stop
CODE = {"clean": "c", "slow": "o", "stop": "p", "start": "g", "yellow": "y", "red": "r", "overnight": "n"}
# Stops we know were black flags rather than driver changes (in-pit lap numbers).
BLACK = {"619": {224, 236}}
# Our drivers, by the lap each stint starts on.
OUR_STINTS = [(1, "Sarah"), (28, "Thomas"), (60, "Coby"), (94, "Pablo"), (127, "Elias"), (159, "Sarah"),
              (184, "Thomas"), (209, "Elias"), (238, "Pablo"), (263, "Coby")]

cls = list(csv.DictReader(open(DATA / "classification.csv")))
cars = {r["num"]: r for r in csv.DictReader(open(DATA / "cars.csv"))}  # from the Lemons entry list
laps = defaultdict(list)
for r in csv.DictReader(open(DATA / "laps.csv")):
    end = datetime.fromisoformat(r["time_of_day"]).timestamp()
    t = float(r["secs"])
    laps[r["num"]].append({"lap": int(r["lap"]), "t": t, "end": end, "start": end - t,
                           "pos": int(r["field_pos"]), "pit": r["in_pit"] == "1", "yellow": r["yellow"] == "1"})
race_start = min(l["start"] for ls in laps.values() for l in ls if l["lap"] == 1)
hhmm = lambda ts: datetime.fromtimestamp(ts).strftime("%a %H:%M")


def analyze(num):
    L = laps[num]
    for l in L:
        l["overnight"] = l["t"] > 6 * 3600
        l["red"] = l["start"] <= RED_AT.timestamp() <= l["end"]
    # Consecutive in-pit laps are one stop; the lap after them is the out-lap.
    stops, i = [], 0
    while i < len(L):
        if L[i]["pit"] and not L[i]["overnight"]:
            j = i
            while j + 1 < len(L) and L[j + 1]["pit"]:
                j += 1
            if j + 1 < len(L) and not L[j + 1]["overnight"]:
                j += 1
            stops.append(list(range(i, j + 1)))
            i = j + 1
        else:
            i += 1
    in_stop = {i for s in stops for i in s}
    night = [i for i, l in enumerate(L) if l["overnight"]]
    first = {0} | {i + 1 for i in night}
    green = [l["t"] for i, l in enumerate(L) if i not in in_stop and i not in first
             and not (l["yellow"] or l["red"] or l["overnight"])]
    med = st.median(green)
    for i, l in enumerate(L):
        l["kind"] = ("overnight" if l["overnight"] else "stop" if i in in_stop else "red" if l["red"] else
                     "yellow" if l["yellow"] else "start" if i in first else
                     "slow" if l["t"] > SLOW * med else "clean")
    clean = sorted(l["t"] for l in L if l["kind"] == "clean")
    ref = st.mean(clean)

    # Excess time over the car's own clean average, by kind of lap. A stop costs its in-lap(s) and
    # out-lap minus that many clean laps. If the red flag came out during a stop, the red-flag
    # lap goes to "red" instead, since the wait wasn't pit time.
    excess = defaultdict(float)
    stop_rows = []
    for s in stops:
        ls = [L[i] for i in s]
        red = [l for l in ls if l["red"]]
        for l in red:
            excess["red"] += l["t"] - ref
        loss = sum(l["t"] - ref for l in ls if not l["red"])
        black = ls[0]["lap"] in BLACK.get(num, ())
        excess["black" if black else "stop"] += loss
        stop_rows.append({"lap": ls[0]["lap"], "loss": round(loss), "at": hhmm(ls[0]["end"]), "t": ls[0]["end"],
                          "yellow": any(l["yellow"] for l in ls), "red": bool(red), "black": black,
                          "drive": loss < DRIVE_THROUGH})
    for l in L:
        if l["kind"] in ("red", "yellow", "start", "slow"):
            excess[l["kind"]] += l["t"] - ref

    # Stints: running between stops (known black flags aside) and the overnight break. A stint
    # starts with its out-lap.
    breaks = [s for s, r in zip(stops, stop_rows) if not (r["black"] or r["drive"])]
    ins = {i for s in breaks for i in s[:-1]}
    outs = {s[-1] for s in breaks}
    stints, cur = [], []
    for i, l in enumerate(L):
        if i in ins or l["overnight"] or i in outs:
            if cur:
                stints.append(cur)
            cur = [l] if i in outs and not l["overnight"] else []
        else:
            cur.append(l)
    if cur:
        stints.append(cur)
    stint_rows = []
    for s in stints:
        c = [l["t"] for l in s if l["kind"] == "clean"]
        stint_rows.append({"from": s[0]["lap"], "to": s[-1]["lap"], "laps": len(s), "t0": s[0]["start"],
                           "t1": s[-1]["end"], "mins": round((s[-1]["end"] - s[0]["start"]) / 60, 1),
                           "avg": round(st.mean(c), 3) if c else None})

    # Start, overnight restart and checkered timing: time not spent driving counted laps.
    driving = sum(l["t"] for l in L if not l["overnight"])
    return {"laps": len(L), "ref": round(ref, 3), "median": round(med, 3), "best": clean[0],
            "top10": round(st.mean(clean[:max(1, len(clean) // 10)]), 3), "sd": round(st.stdev(clean), 2),
            "grid_delay": round(L[0]["start"] - race_start, 1), "driving": round(driving, 1),
            "excess": {k: round(v, 1) for k, v in excess.items()},
            "counts": {k: sum(1 for l in L if l["kind"] == k) for k in ("clean", "slow", "yellow", "stop", "red")},
            "stops": stop_rows, "stints": stint_rows,
            "lap_rows": [[l["lap"], round(l["t"], 3), l["pos"], CODE[l["kind"]], round(l["end"])] for l in L]}


def gap(a, b):
    """Split car a's lap advantage over car b into parts that add up exactly.

    Laps driven = (driving time - excess time) / clean pace, so the gap splits into pace,
    each kind of excess time (converted to laps at a's pace), and "timing": the difference in
    driving time from grid slot, overnight restart order and where each car was at the checkered.
    """
    parts = {"pace": (b["driving"] - sum(b["excess"].values())) * (1 / a["ref"] - 1 / b["ref"])}
    for k in sorted(set(a["excess"]) | set(b["excess"])):
        parts[k] = (b["excess"].get(k, 0) - a["excess"].get(k, 0)) / a["ref"]
    # Crossing the start line later (grid slot) leaves less time to drive; the rest of the timing
    # term is the overnight restart order and where each car was when the checkered came out.
    parts["grid"] = (b["grid_delay"] - a["grid_delay"]) / a["ref"]
    parts["timing"] = (a["driving"] - b["driving"]) / a["ref"] - parts["grid"]
    return {k: round(v, 2) for k, v in parts.items()}


def window_avg(num, t0, t1):
    """A car's average clean lap between two clock times."""
    ts = [l["t"] for l in laps[num] if l.get("kind") == "clean" and t0 <= l["end"] <= t1]
    return (round(st.mean(ts), 3), len(ts)) if ts else (None, 0)


out = []
for r in cls:
    if int(r["pos"]) > TOP:
        continue
    out.append({"pos": int(r["pos"]), "num": r["num"], "class": r["class"], "class_pos": int(r["class_pos"]),
                "team": r["team"], "classified": int(r["laps"]),
                "car": cars.get(r["num"], {}).get("car"), "car_conf": cars.get(r["num"], {}).get("confidence"), **analyze(r["num"])})
by = {c["num"]: c for c in out}
us, rival = by[US], by[RIVAL]
for c in out:
    c["penalty"] = c["laps"] - c["classified"]
    c["gap_to_us"] = gap(c, us) if c is not us else None

# Each of our stints next to the rival's and the top 20's clean pace over the same clock window.
starts = [s for s, _ in OUR_STINTS] + [us["laps"] + 1]
by_lap = {r[0]: r for r in us["lap_rows"]}
compare = []
for (s, name), nxt in zip(OUR_STINTS, starts[1:]):
    rows = [by_lap[n] for n in range(s, nxt)]
    day = [r for r in rows if r[3] != "n"]
    t0, t1 = day[0][4] - day[0][1], day[-1][4]
    ours = [r[1] for r in rows if r[3] == "c"]
    racing = [r[1] for r in rows if r[3] in "co"]  # clean + off-pace laps: all green running
    riv, rn = window_avg(RIVAL, t0, t1)
    field = [a for c in out if c["class"] == "B" and c is not us for a in [window_avg(c["num"], t0, t1)[0]] if a]
    compare.append({"driver": name, "from": s, "to": nxt - 1, "day": 1 if s < 159 else 2,
                    "at": hhmm(t0) + "–" + datetime.fromtimestamp(t1).strftime("%H:%M"),
                    "avg": round(st.mean(ours), 3), "clean": len(ours), "green": len(racing),
                    "green_avg": round(st.mean(racing), 3), "rival": riv, "class_b_top": round(st.median(field), 3),
                    "lost_s": round(sum(racing) - len(racing) * riv, 1) if riv else None})

data = {"us": US, "rival": RIVAL, "race_start": race_start, "red_at": RED_AT.timestamp(),
        "cars": out, "our_stints": compare}
json.dump(data, open(DATA / "field.json", "w"), indent=1)
(DATA / "field.js").write_text("// Generated by scripts/analyze_field.py from laps.csv\nconst FIELD_DATA = "
                               + json.dumps(data, separators=(",", ":")) + ";\n")
print(f"{len(out)} cars -> {DATA / 'field.json'}")
