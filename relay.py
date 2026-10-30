"""osm-relay: kjører OpenStreetMap/Overpass-søk på vegne av skraperne (Overpass blokkerer Cloudflare-IP-er).
Henter køen fra relay-workeren, kjører hvert søk mot offentlige Overpass-speil (ett om gangen, høflig tempo),
og poster svaret tilbake. Ingen persondata – bare offentlige kartdata om bedrifter."""
import json, os, sys, time, urllib.request, urllib.parse

URL = os.environ["RELAY_URL"].rstrip("/")
KEY = os.environ["RELAY_KEY"]
MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
UA = "BaseAITools-OSM-relay/1.0 (hello@baseaitools.com)"

def relay(path, body=None):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"x-relay-key": KEY, "content-type": "application/json", "user-agent": UA},
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def overpass(q):
    last = None
    for m in MIRRORS:
        try:
            data = urllib.parse.urlencode({"data": q}).encode()
            req = urllib.request.Request(m, data=data, headers={"user-agent": UA, "content-type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.load(r)
            rem = str(d.get("remark") or "")
            if rem and any(x in rem.lower() for x in ("error", "timed out", "timeout", "out of memory", "rate")):
                last = f"{m.split('/')[2]}: {rem[:80]}"; continue
            return True, d.get("elements") or [], m.split("/")[2]
        except Exception as e:
            last = f"{m.split('/')[2]}: {str(e)[:80]}"
            time.sleep(3)
    return False, [], last

def main():
    t0 = time.time(); done = fail = 0
    while time.time() - t0 < 14 * 60:
        jobs = relay("/jobs?n=30").get("jobs", [])
        if not jobs: break
        for j in jobs:
            if time.time() - t0 > 14 * 60: break
            ok, els, info = overpass(j["q"])
            try:
                if ok:
                    relay("/result", {"h": j["h"], "ok": True, "elements": els, "mirror": info}); done += 1
                else:
                    relay("/result", {"h": j["h"], "ok": False, "err": info}); fail += 1
            except Exception as e:
                print("kunne ikke levere", j.get("h"), str(e)[:80]); fail += 1
            time.sleep(2)
        if fail and not done: break
    print(f"ferdig: {done} ok, {fail} feilet, {int(time.time()-t0)} s")

if __name__ == "__main__":
    main()
