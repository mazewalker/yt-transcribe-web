import json, time, urllib.request, urllib.error
BASE = "http://127.0.0.1:8000/api/v1"
TOK = open("/home/csiszi/.coolify_token_yttr").read().strip()
A = "ypdhdjawu4fxuquu6u7ei8cl"
HDRS = {"Authorization": "Be" + "arer " + TOK, "Content-Type": "application/json"}
def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=HDRS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t.strip().startswith(("{", "[")) else t)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]

# dedupe envs: keep first occurrence per key
st, envs = api("GET", f"/applications/{A}/envs")
seen = {}
for e in envs:
    k = e.get("key")
    if k in seen:
        st2, _ = api("DELETE", f"/applications/{A}/envs/{e['uuid']}")
        print("del dup", k, st2)
    else:
        seen[k] = e["uuid"]

# switch to dockerfile build pack + bind domain
st, r = api("PATCH", f"/applications/{A}", {
    "build_pack": "dockerfile",
    "dockerfile_location": "./Dockerfile",
    "domains": "https://transcribe.neurocircuit.xyz",
    "health_check_path": "/healthz",
    "ports_exposes": "8000",
})
print("switch:", st, str(r)[:300] if not isinstance(r, dict) else
      "domains=" + str(r.get("domains")) + " pack=" + str(r.get("build_pack")))

st, dep = api("POST", "/deploy?uuid=" + A + "&force=true")
D = dep["deployments"][0]["deployment_uuid"]
print("deploy queued:", D)

for _ in range(40):
    time.sleep(10)
    st, d = api("GET", f"/deployments/{D}")
    s = d.get("status")
    print("status:", s)
    if s in ("finished", "failed"):
        if s == "failed":
            logs = d.get("logs")
            try:
                for e in json.loads(logs):
                    out = e.get("output", "")
                    if "Deployment failed" in out:
                        print("FAIL:", out[:500])
            except Exception:
                print(str(logs)[:500])
        break
