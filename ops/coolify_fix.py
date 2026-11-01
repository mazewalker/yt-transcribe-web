import json, urllib.request, urllib.error
BASE = "http://127.0.0.1:8000/api/v1"
TOK = open("/home/csiszi/.coolify_token_yttr").read().strip()
A = "ypdhdjawu4fxuquu6u7ei8cl"
YT_TOKEN = open("/home/csiszi/.config/yt-transcribe/token").read().strip()
WEB_PASS = open("/home/csiszi/.config/yt-transcribe-web/webpass").read().strip()
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

st, r = api("PATCH", f"/applications/{A}", {"docker_compose_domains": [
    {"name": "web", "domain": "https://transcribe.neurocircuit.xyz"}]})
print("dcd:", st, str(r)[:250])

for name, val in [("YT_API_URL", "https://yt-api.airobotika.com"),
                  ("YT_API_TOKEN", YT_TOKEN),
                  ("WEB_USER", "airobotika"),
                  ("WEB_PASS", WEB_PASS)]:
    st, r = api("POST", f"/applications/{A}/envs",
                {"key": name, "value": val, "is_literal": True, "is_shown_once": True})
    print("env", name, "->", st)

st, envs = api("GET", f"/applications/{A}/envs")
print("envs now:", [e.get("key") for e in envs] if isinstance(envs, list) else str(envs)[:200])

st, dep = api("POST", "/deploy?uuid=" + A + "&force=true")
print("redeploy:", st, str(dep)[:200])
