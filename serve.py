#!/usr/bin/env python3
"""
Zero-dependency local server for the ResearchOps GUI.

  GET  /            -> app/index.html
  GET  /api/data    -> data/projects.json
  POST /api/save    -> overwrite data/projects.json with posted JSON (atomic + backup)

Run:  python3 serve.py           (defaults to http://127.0.0.1:8765)
      python3 serve.py 9000      (custom port)
"""
import http.server, socketserver, json, os, sys, shutil, datetime, re, urllib.request, urllib.error
import threading, time, imaplib, email
from email.header import decode_header
from urllib.parse import urlparse, parse_qs, urlencode
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import report as report_mod

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data", "projects.json")
INDEX = os.path.join(ROOT, "app", "index.html")
BACKUPS = os.path.join(ROOT, "data", "backups")
CONFIG = os.path.join(ROOT, "data", "config.json")   # holds the Anthropic API key locally (not tracked)
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

# ---------- LLM update assistant ----------
def load_config():
    try:
        with open(CONFIG) as f: return json.load(f)
    except Exception: return {}

def get_api_key(cfg):
    return os.environ.get("ANTHROPIC_API_KEY") or cfg.get("anthropic_api_key") or ""

def call_claude(api_key, model, prompt):
    body = json.dumps({"model": model, "max_tokens": 2000,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        resp = json.load(r)
    return "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")

def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text); text = re.sub(r"\n?```$", "", text).strip()
    i, j = text.find("{"), text.rfind("}")
    if i >= 0 and j > i: text = text[i:j + 1]
    return json.loads(text)

STAGES = ("idea, data-collection, analysis, manuscript-prep, ready-for-feedback, "
          "responding-to-feedback, prepared-for-submission, in-submission, in-review, "
          "in-revision, rejected, accepted")

def build_llm_prompt(update, data):
    lines = []
    for p in data.get("projects", []):
        tasks = [i.get("text", "") for tr in p.get("tracks", {}).values()
                 for i in tr.get("items", []) if not i.get("done")][:6]
        line = f"- id={p['id']} | {p.get('name','')} (lab: {p.get('lab','')}, stage: {p.get('stage','')})"
        if tasks: line += " | open: " + " ; ".join(tasks)
        lines.append(line)
    idx = "\n".join(lines)
    return f"""You maintain a research project tracker. Below are the user's projects, then an UPDATE they pasted (an email, Slack thread, or note). Decide which project(s) it concerns and propose concise, structured changes.

PROJECTS:
{idx}

UPDATE:
\"\"\"{update}\"\"\"

Return ONLY a JSON object (no prose, no markdown) shaped exactly like:
{{"matches":[{{"project_id":"<existing id or NEW>","project_name":"<name>","lab":"<lab if NEW>","confidence":"high|medium|low","summary":"<one sentence>","changes":[{{"type":"add_task|update_stage|add_note|flag","track":"paper|data|analysis|funding","text":"<concise>","stage":"<new stage if type=update_stage>"}}]}}]}}

Rules: only propose changes clearly implied by the update; keep text short and actionable; use type "flag" for anything needing the user's reply/follow-up; if nothing matches, use project_id "NEW" and suggest a name + lab. If the update is not about any research project (spam, personal, admin), return {{"matches":[]}}. Valid stages: {STAGES}."""

# ---------- email auto-ingest (Gmail IMAP) ----------
PENDING = os.path.join(ROOT, "data", "pending.json")
EMAIL_STATE = os.path.join(ROOT, "data", "email_state.json")

def load_pending():
    try:
        with open(PENDING) as f: return json.load(f)
    except Exception: return []

def save_pending(items):
    tmp = PENDING + ".tmp"
    with open(tmp, "w") as f: json.dump(items, f, indent=2)
    os.replace(tmp, PENDING)

def _hdr(s):
    out = ""
    for txt, enc in decode_header(s or ""):
        out += txt.decode(enc or "utf-8", "ignore") if isinstance(txt, bytes) else txt
    return out

def _body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attach" not in str(part.get("Content-Disposition", "")):
                try: return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "ignore")
                except Exception: pass
        return ""
    try: return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "ignore")
    except Exception: return str(msg.get_payload() or "")

def guess_imap(addr):
    d = (addr.split("@")[-1] if "@" in addr else "").lower()
    if any(k in d for k in ("gmail.com", "googlemail.com")): return "imap.gmail.com"
    if any(k in d for k in ("outlook.", "hotmail.", "live.", "office365", "upenn.edu", "pennmedicine", "onmicrosoft")): return "outlook.office365.com"
    if "yahoo" in d: return "imap.mail.yahoo.com"
    if "icloud" in d or "me.com" in d: return "imap.mail.me.com"
    return "imap.gmail.com"

def check_email_once(cfg):
    addr, pw = cfg.get("gmail_address"), cfg.get("gmail_app_password")
    if not (addr and pw): return {"error": "email not configured"}
    if not get_api_key(cfg): return {"error": "no_key"}
    host = cfg.get("imap_server") or guess_imap(addr)
    try:
        M = imaplib.IMAP4_SSL(host); M.login(addr, pw)
    except Exception as e:
        hint = ""
        if "office365" in host or "outlook" in host:
            hint = " — Microsoft/Outlook & university (e.g. Penn) accounts usually DISABLE basic-auth IMAP for security, so an app password won't work here without OAuth. Use a Gmail/Google-Workspace account, or forward relevant mail to one."
        return {"error": f"IMAP login to {host} failed ({e}).{hint}"}
    added = 0
    try:
        M.select("INBOX")
        state = {}
        try:
            with open(EMAIL_STATE) as f: state = json.load(f)
        except Exception: pass
        last_uid = int(state.get("last_uid", 0))
        crit = f"UID {last_uid+1}:*" if last_uid else "UNSEEN"
        typ, sd = M.uid("search", None, crit)
        uids = [int(u) for u in sd[0].split()] if sd and sd[0] else []
        uids = [u for u in uids if u > last_uid][-15:]
        with open(DATA) as f: proj = json.load(f)
        senders = [s.strip().lower() for s in (cfg.get("email_senders") or []) if s.strip()]
        pending = load_pending(); seen = {p.get("key") for p in pending}
        for uid in uids:
            typ, md = M.uid("fetch", str(uid), "(RFC822)")
            state["last_uid"] = uid
            if not md or not md[0]: continue
            msg = email.message_from_bytes(md[0][1])
            frm, subj = _hdr(msg.get("From", "")), _hdr(msg.get("Subject", ""))
            if senders and not any(s in frm.lower() for s in senders): continue
            key = f"email:{uid}"
            if key in seen: continue
            update_text = f"From: {frm}\nSubject: {subj}\n\n{_body(msg)[:6000]}"
            try:
                result = extract_json(call_claude(get_api_key(cfg), cfg.get("model", "claude-sonnet-5"),
                                                  build_llm_prompt(update_text, proj)))
            except Exception:
                result = {"matches": []}
            if result.get("matches"):
                pending.append({"id": f"em{uid}", "key": key, "source": "email", "from": frm,
                                "subject": subj, "date": msg.get("Date", ""), "matches": result["matches"],
                                "ts": datetime.datetime.now().isoformat()})
                added += 1
        save_pending(pending)
        with open(EMAIL_STATE, "w") as f: json.dump(state, f)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    finally:
        try: M.logout()
        except Exception: pass
    return {"ok": True, "added": added, "pending": len(load_pending())}

# ---------- Slack auto-ingest (Slack Web API) ----------
SLACK_STATE = os.path.join(ROOT, "data", "slack_state.json")

def slack_get(token, method, params):
    q = urlencode(params)
    req = urllib.request.Request(f"https://slack.com/api/{method}" + (f"?{q}" if q else ""),
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def check_slack_once(cfg):
    token = cfg.get("slack_token")
    if not token: return {"error": "Slack not configured"}
    if not get_api_key(cfg): return {"error": "no_key"}
    try:
        auth = slack_get(token, "auth.test", {})
    except Exception as e:
        return {"error": f"Slack request failed: {e}"}
    if not auth.get("ok"): return {"error": f"Slack auth failed: {auth.get('error','')}"}
    me = auth.get("user_id")
    try:
        with open(SLACK_STATE) as f: state = json.load(f)
    except Exception: state = {}
    names, cur = {}, ""
    try:
        for _ in range(4):
            ul = slack_get(token, "users.list", {"limit": 200, **({"cursor": cur} if cur else {})})
            for u in ul.get("members", []): names[u["id"]] = u.get("real_name") or u.get("name") or u["id"]
            cur = ul.get("response_metadata", {}).get("next_cursor", "")
            if not cur: break
    except Exception: pass
    watch = [w.strip().lstrip("#").lower() for w in (cfg.get("slack_channels") or []) if w.strip()]
    try:
        convs = slack_get(token, "conversations.list",
                          {"types": "public_channel,private_channel,im,mpim", "limit": 200}).get("channels", [])
    except Exception as e:
        return {"error": f"Slack list failed: {e}"}
    with open(DATA) as f: proj = json.load(f)
    pending = load_pending(); seen = {p.get("key") for p in pending}; added = 0
    for c in convs:
        cid = c["id"]
        cname = c.get("name") or (names.get(c.get("user"), "DM") if c.get("is_im") else cid)
        if watch and str(cname).lower() not in watch and cid.lower() not in watch: continue
        try:
            hist = slack_get(token, "conversations.history", {"channel": cid, "oldest": state.get(cid, "0"), "limit": 30})
        except Exception: continue
        if hist.get("messages"): state[cid] = hist["messages"][0]["ts"]
        msgs = [m for m in reversed(hist.get("messages", []))
                if m.get("type") == "message" and m.get("text") and m.get("user") != me and not m.get("subtype")]
        if not msgs: continue
        label = ("#" + cname) if not c.get("is_im") else ("DM · " + str(cname))
        blob = f"Slack {label}:\n" + "\n".join(f"- {names.get(m.get('user'), m.get('user',''))}: {m['text']}" for m in msgs[-15:])
        key = f"slack:{cid}:{state.get(cid)}"
        if key in seen: continue
        try:
            result = extract_json(call_claude(get_api_key(cfg), cfg.get("model", "claude-sonnet-5"),
                                              build_llm_prompt(blob, proj)))
        except Exception:
            result = {"matches": []}
        if result.get("matches"):
            pending.append({"id": f"sl{cid}{str(state.get(cid,'')).replace('.','')}", "key": key, "source": "slack",
                            "from": label, "subject": "Slack " + label, "date": "",
                            "matches": result["matches"], "ts": datetime.datetime.now().isoformat()})
            added += 1
    save_pending(pending)
    with open(SLACK_STATE, "w") as f: json.dump(state, f)
    return {"ok": True, "added": added, "pending": len(load_pending())}

def poll_loop():
    while True:
        try:
            cfg = load_config()
            if get_api_key(cfg):
                if cfg.get("email_poll") and cfg.get("gmail_address"): check_email_once(cfg)
                if cfg.get("slack_poll") and cfg.get("slack_token"): check_slack_once(cfg)
        except Exception:
            pass
        time.sleep(600)   # every 10 minutes

class H(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, str(v))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(INDEX, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "index.html missing", "text/plain")
        elif self.path == "/api/data":
            try:
                with open(DATA, "rb") as f:
                    body = f.read()
                mt = os.path.getmtime(DATA)
                self._send(200, body, extra={"X-Data-Mtime": f"{mt:.3f}"})
            except FileNotFoundError:
                self._send(404, json.dumps({"error": "no data"}))
        elif self.path == "/api/config":
            cfg = load_config()
            self._send(200, json.dumps({"hasKey": bool(get_api_key(cfg)),
                "model": cfg.get("model", "claude-sonnet-5"),
                "hasEmail": bool(cfg.get("gmail_address") and cfg.get("gmail_app_password")),
                "gmail_address": cfg.get("gmail_address", ""),
                "imap_server": cfg.get("imap_server", ""),
                "imap_guess": guess_imap(cfg.get("gmail_address", "")),
                "email_poll": bool(cfg.get("email_poll")),
                "email_senders": cfg.get("email_senders", []),
                "hasSlack": bool(cfg.get("slack_token")),
                "slack_poll": bool(cfg.get("slack_poll")),
                "slack_channels": cfg.get("slack_channels", [])}))
        elif self.path == "/api/pending":
            self._send(200, json.dumps(load_pending()))
        elif urlparse(self.path).path == "/report":
            lab = (parse_qs(urlparse(self.path).query).get("lab", ["ELab"]))[0]
            try:
                with open(DATA) as f:
                    data = json.load(f)
                if lab not in data["labs"]:
                    lab = data["labs"][0]
                html = report_mod.build_html(data, lab)
                self._send(200, html, "text/html; charset=utf-8")
            except Exception as e:
                self._send(500, f"report error: {e}", "text/plain")
        else:
            self._send(404, "not found", "text/plain")

    def _read_json(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n))

    def do_POST(self):
        if self.path == "/api/config":
            try:
                payload = self._read_json(); cfg = load_config()
                for k in ("anthropic_api_key", "model", "gmail_address", "gmail_app_password", "imap_server", "slack_token"):
                    if k in payload: cfg[k] = (payload[k] or "").strip()
                if "email_poll" in payload: cfg["email_poll"] = bool(payload["email_poll"])
                if "slack_poll" in payload: cfg["slack_poll"] = bool(payload["slack_poll"])
                for lk in ("email_senders", "slack_channels"):
                    if lk in payload:
                        cfg[lk] = [s.strip() for s in payload[lk] if s.strip()] \
                            if isinstance(payload[lk], list) else \
                            [s.strip() for s in str(payload[lk]).split(",") if s.strip()]
                os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
                with open(CONFIG, "w") as f: json.dump(cfg, f, indent=2)
                try: os.chmod(CONFIG, 0o600)
                except Exception: pass
                self._send(200, json.dumps({"ok": True, "hasKey": bool(get_api_key(cfg)),
                    "hasEmail": bool(cfg.get("gmail_address") and cfg.get("gmail_app_password"))}))
            except Exception as e:
                self._send(400, json.dumps({"error": f"{e}"}))
            return
        if self.path == "/api/email/check":
            self._send(200, json.dumps(check_email_once(load_config())))
            return
        if self.path == "/api/slack/check":
            self._send(200, json.dumps(check_slack_once(load_config())))
            return
        if self.path == "/api/pending/resolve":
            try:
                rid = self._read_json().get("id")
                save_pending([p for p in load_pending() if p.get("id") != rid])
                self._send(200, json.dumps({"ok": True, "pending": len(load_pending())}))
            except Exception as e:
                self._send(400, json.dumps({"error": f"{e}"}))
            return
        if self.path == "/api/llm":
            try:
                payload = self._read_json()
                update = (payload.get("update") or "").strip()
                if not update:
                    self._send(400, json.dumps({"error": "empty update"})); return
                cfg = load_config(); key = get_api_key(cfg)
                if not key:
                    self._send(400, json.dumps({"error": "no_key"})); return
                with open(DATA) as f: data = json.load(f)
                text = call_claude(key, cfg.get("model", "claude-sonnet-5"),
                                   build_llm_prompt(update, data))
                result = extract_json(text)
                self._send(200, json.dumps(result))
            except urllib.error.HTTPError as e:
                self._send(502, json.dumps({"error": f"Anthropic API error {e.code}: {e.read().decode('utf-8','ignore')[:300]}"}))
            except Exception as e:
                self._send(500, json.dumps({"error": f"{type(e).__name__}: {e}"}))
            return
        if self.path != "/api/save":
            self._send(404, "not found", "text/plain")
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n)
            data = json.loads(raw)              # validate JSON
            assert isinstance(data, dict) and "projects" in data, "bad shape"
        except Exception as e:
            self._send(400, json.dumps({"error": f"invalid payload: {e}"}))
            return
        # optimistic concurrency: reject a save from a browser whose data is stale
        base = self.headers.get("X-Base-Mtime")
        if base and os.path.exists(DATA):
            try:
                if os.path.getmtime(DATA) - float(base) > 0.5:
                    self._send(409, json.dumps({"error": "stale",
                        "mtime": f"{os.path.getmtime(DATA):.3f}"}))
                    return
            except ValueError:
                pass
        # timestamped backup of previous state, then atomic write
        os.makedirs(BACKUPS, exist_ok=True)
        if os.path.exists(DATA):
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy2(DATA, os.path.join(BACKUPS, f"projects-{stamp}.json"))
            # keep only the 40 most recent backups
            bks = sorted(os.listdir(BACKUPS))
            for old in bks[:-40]:
                os.remove(os.path.join(BACKUPS, old))
        data["updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        tmp = DATA + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, DATA)
        self._send(200, json.dumps({"ok": True, "updated": data["updated"],
                                    "mtime": f"{os.path.getmtime(DATA):.3f}"}))

    def log_message(self, *a):
        pass  # quiet

class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    os.chdir(ROOT)
    threading.Thread(target=poll_loop, daemon=True).start()   # background email poller (opt-in via config)
    with Server(("127.0.0.1", PORT), H) as httpd:
        print(f"ResearchOps running → http://127.0.0.1:{PORT}")
        print("Ctrl-C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")
