import json, urllib.request, urllib.error
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

st, app = api("GET", f"/applications/{A}")
if isinstance(app, dict):
    print("app:", app.get("name"), "| status:", app.get("status"), "| dcd:", app.get("docker_compose_domains"), "| domains:", app.get("domains"))
else:
    print("app:", st, str(app)[:300])

st, envs = api("GET", f"/applications/{A}/envs")
print("envs:", [e.get("key") for e in envs] if isinstance(envs, list) else str(envs)[:200])

st, deps = api("GET", "/deployments")
if isinstance(deps, list):
    for d in deps:
        if d.get("application_uuid") == A:
            print("DEP:", d.get("deployment_uuid"), d.get("status"), d.get("created_at"))
