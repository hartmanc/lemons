"""Download official MYLAPS Speedhive results for a session into buttonwillow/data.

Usage: python3 scripts/fetch_speedhive.py [session_id]

Writes classification.csv (one row per car) and laps.csv (one row per lap, every car).
"""
import csv, json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SESSION = sys.argv[1] if len(sys.argv) > 1 else "12906863"
API = "https://eventresults-api.speedhive.com/api/v0.2.3/eventresults/sessions/" + SESSION
OUT = Path(__file__).resolve().parent.parent / "buttonwillow" / "data"


def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def secs(s):
    t = 0.0
    for part in s.split(":"):
        t = t * 60 + float(part)
    return round(t, 3)


rows = get("/classification")["rows"]
OUT.mkdir(parents=True, exist_ok=True)
with open(OUT / "classification.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["pos", "num", "class", "class_pos", "team", "laps", "best", "best_lap", "total_time"])
    for r in rows:
        w.writerow([r["position"], r["startNumber"], r["resultClass"], r["positionInClass"], r["name"],
                    r["numberOfLaps"], r["bestTime"], r["bestLap"], r["totalTime"]])

with ThreadPoolExecutor(8) as ex:
    lapdata = list(ex.map(lambda r: get(f"/lapdata/{r['position']}/laps"), rows))

with open(OUT / "laps.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["num", "lap", "secs", "time_of_day", "field_pos", "in_pit", "yellow"])
    for r, d in zip(rows, lapdata):
        for l in d["laps"]:
            w.writerow([r["startNumber"], l["lapNr"], secs(l["lapTime"]), l["timeOfDay"],
                        l["fieldComparison"]["position"], int(l["inPit"]), int("YELLOW" in l["status"])])
print(f"{len(rows)} cars, {sum(len(d['laps']) for d in lapdata)} laps -> {OUT}")
