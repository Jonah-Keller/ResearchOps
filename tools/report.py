#!/usr/bin/env python3
"""
Weekly per-lab report, formatted like a PI update email:

  Weekly Report (MM/DD) — Lab
  HIGH PRIORITY SUMMARY
    Research Items          (open + done[√] tasks from starred projects)
    Clerical / Logistical / Infrastructure Items
  OVERALL REVIEW
    1) Project — Authorship · Journal · Stage
         - task (owner)
         - Poster: …
    2) …
  COMPLETED / ACCEPTED

Emits a self-contained HTML page with a 'Copy as plain text' button.
CLI:  python3 tools/report.py <LabName>
"""
import os, sys, json, html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "projects.json")

AUTH_LBL = {"first":"1st","co-first":"Co-1st","second":"2nd","third":"3rd","middle":"Middle","":""}
STAGE_LBL = {"idea":"Idea","data-collection":"Data Collection","analysis":"Analysis",
             "manuscript-prep":"Manuscript Preparation","ready-for-feedback":"Ready for Feedback",
             "responding-to-feedback":"Responding to Feedback","prepared-for-submission":"Prepared for Submission",
             "in-submission":"In Submission","in-review":"In Review","in-revision":"In Revision",
             "rejected":"Rejected","accepted":"Accepted","":"Idea"}
CLERICAL = {"infra","clerical","logistics","admin","it"}
WORK_ORDER = ["paper","analysis","data","funding"]

def load():
    with open(DATA) as f: return json.load(f)

def stage(p): return p.get("stage") or "idea"
def in_lab(data, lab): return [p for p in data["projects"] if p["lab"] == lab]
def groups_in(data, lab): return [g for g in data.get("groups", []) if g["lab"] == lab]

def journal_of(p):
    return (p.get("tracks", {}).get("paper", {}) or {}).get("journal", "")

def header(p):
    auth = AUTH_LBL.get(p.get("authorship", ""), "")
    bits = [b for b in [auth + " author" if auth else "", journal_of(p), STAGE_LBL[stage(p)]] if b]
    return f"{p['name']} — " + " · ".join(bits) if bits else p["name"]

def fmt(it):
    owner = (it.get("owner") or "").strip()
    txt = (it.get("text") or "").strip()
    line = f"{txt}"
    if owner:
        line = f"{txt}  ({owner})"
    return line

def node_lines(nodes, depth=1):
    out = []
    for n in nodes:
        out.append("   " + "  " * depth + "· [" + ("x" if n.get("done") else " ") + "] " + n.get("text", ""))
        out += node_lines(n.get("children", []), depth + 1)
    return out

def task_lines(p):
    """Nested lines for one project's Overall Review entry."""
    out = []
    j = journal_of(p)
    # journal/authorship handled in header; here list open work + notes + posters
    for t in WORK_ORDER:
        tr = p.get("tracks", {}).get(t)
        if not tr: continue
        for it in tr.get("items", []):
            if it.get("done") or it.get("hp"): continue  # hp shown in High Priority, not repeated here
            out.append(fmt(it))
            out += node_lines(it.get("subtasks", []))
    for ps in p.get("posters", []):
        pres = ps.get("presentations", [])
        venues = " + ".join(
            (pr.get("conference","") + (f" [{pr['status']}]" if pr.get("status") else "")).strip()
            for pr in pres if pr.get("conference")) or ps.get("note") or "poster"
        auth = AUTH_LBL.get(ps.get("authorship",""), "")
        tail = " · ".join([b for b in [ps.get("type",""), (auth + " author") if auth else ""] if b])
        note = f" — {ps['note']}" if ps.get("note") else ""
        out.append(f"Poster: {venues}{note}" + (f"  ({tail})" if tail else ""))
    return out

def all_tasks(data, lab):
    for c in in_lab(data, lab) + groups_in(data, lab):
        for t, tr in c.get("tracks", {}).items():
            for it in tr.get("items", []):
                yield it

def research_items(data, lab):
    # preserve authoring order; keep [√] inline (mirrors the email)
    return [(it.get("text","").strip(), (it.get("owner") or "").strip(), bool(it.get("done")),
             it.get("subtasks", []))
            for it in all_tasks(data, lab) if it.get("hp")]

def clerical_items(data, lab):
    out = [c.get("text","").strip() + (f"  [{c['status']}]" if c.get("status") else "")
           for c in data.get("clerical", []) if c.get("lab") == lab]
    out += [it.get("text","").strip() for it in all_tasks(data, lab)
            if it.get("clerical") or (it.get("owner") or "").strip().lower() in CLERICAL]
    return out

def overall_projects(data, lab):
    ps = [p for p in in_lab(data, lab) if stage(p) not in ("accepted", "rejected")]
    ps.sort(key=lambda p: (0 if p.get("priority") else 1))
    return ps

def completed(data, lab):
    return [p for p in in_lab(data, lab) if stage(p) == "accepted"]

# ---------------- plain text ----------------
def build_text(data, lab):
    today = data.get("updated","")[:10]
    L = [f"Weekly Report ({today}) — {lab}", ""]
    L.append("HIGH PRIORITY SUMMARY"); L.append("")
    L.append("Research Items")
    ri = research_items(data, lab)
    if ri:
        for i,(text,owner,done,subs) in enumerate(ri,1):
            mark = " [√]" if done else ""
            own = f"  ({owner})" if owner else ""
            L.append(f"  {i}. {text}{mark}{own}")
            for s in subs:
                L.append(f"       * {s.get('text','')}" + (" [√]" if s.get('done') else ""))
    else:
        L.append("  (flag a task 'high priority' to populate this)")
    L.append(""); L.append("Clerical / Logistical / Infrastructure Items")
    ci = clerical_items(data, lab)
    if ci:
        for i,text in enumerate(ci,1): L.append(f"  {i}. {text}")
    else:
        L.append("  (none)")
    gr = [g for g in data.get("grants", []) if g.get("lab") == lab]
    if gr:
        L.append(""); L.append("GRANTS (APPLICATIONS)")
        for g in gr:
            bits = [b for b in [g.get("sponsor"), g.get("amount"),
                    ("deadline " + g["deadline"]) if g.get("deadline") else "",
                    ("hear back " + g["hearback"]) if g.get("hearback") else "",
                    g.get("status")] if b]
            L.append(f"  • {g.get('name','(grant)')}" + (" — " + " · ".join(bits) if bits else ""))
    L.append(""); L.append("OVERALL REVIEW"); L.append("")
    for i,p in enumerate(overall_projects(data, lab), 1):
        L.append(f"{i}) {header(p)}")
        for ln in task_lines(p):
            L.append(f"     - {ln}")
        L.append("")
    dn = completed(data, lab)
    if dn:
        L.append("COMPLETED / ACCEPTED")
        for p in dn:
            L.append(f"  • {p['name']}" + (f" — {journal_of(p)}" if journal_of(p) else ""))
    return "\n".join(L).rstrip() + "\n"

# ---------------- HTML ----------------
def _e(s): return html.escape(s or "")

def build_html(data, lab):
    text = build_text(data, lab)
    today = data.get("updated","")[:10]
    ri = research_items(data, lab); ci = clerical_items(data, lab)
    def li_task(text, owner, done, subs):
        o = f' <span class="who">({_e(owner)})</span>' if owner else ''
        c = ' done' if done else ''
        sub = ''
        if subs:
            sub = '<ul>' + ''.join(f'<li class="{"done" if s.get("done") else ""}">{_e(s.get("text",""))}{" ✓" if s.get("done") else ""}</li>' for s in subs) + '</ul>'
        return f'<li class="{c}">{_e(text)}{o}{" ✓" if done else ""}{sub}</li>'
    parts = []
    parts.append('<h2 class="hp">High Priority Summary</h2>')
    parts.append('<h3>Research Items</h3><ol>')
    parts += [li_task(t,o,d,s) for t,o,d,s in ri] or ['<li class="muted">flag a task high priority</li>']
    parts.append('</ol>')
    parts.append('<h3>Clerical / Logistical / Infrastructure</h3><ol>')
    parts += [f'<li>{_e(t)}</li>' for t in ci] or ['<li class="muted">none</li>']
    parts.append('</ol>')
    parts.append('<h2>Overall Review</h2>')
    for i,p in enumerate(overall_projects(data, lab),1):
        parts.append(f'<div class="proj"><div class="pname">{i}) {_e(p["name"])} '
                     f'<span class="sub">{_e(header(p).split("—",1)[1].strip()) if "—" in header(p) else ""}</span></div>')
        lines = task_lines(p)
        if lines:
            parts.append('<ul>' + ''.join(f'<li>{_e(l)}</li>' for l in lines) + '</ul>')
        else:
            parts.append('<div class="muted">— no open tasks —</div>')
        parts.append('</div>')
    dn = completed(data, lab)
    if dn:
        parts.append('<h2>Completed / Accepted</h2><ul>')
        parts += [f'<li>{_e(p["name"])}' + (f' — <b>{_e(journal_of(p))}</b>' if journal_of(p) else '') + '</li>' for p in dn]
        parts.append('</ul>')
    body = "\n".join(parts)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Weekly Report — {_e(lab)}</title>
<style>
:root{{--bg:#f6f7f9;--panel:#fff;--ink:#1c2330;--muted:#67728a;--line:#e4e8ef;--accent:#3b6fd4;--star:#e0a91b;}}
@media(prefers-color-scheme:dark){{:root{{--bg:#12151b;--panel:#1a1f28;--ink:#e7ecf3;--muted:#93a0b5;--line:#2a313d;--accent:#5b8def;}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}}
.wrap{{max-width:820px;margin:0 auto;padding:26px 22px 80px}}
.top{{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:6px}} .grow{{flex:1}}
h1{{font-size:22px;margin:0}} .date{{color:var(--muted);font-size:13px}}
.btn{{padding:8px 14px;border:1px solid var(--accent);background:var(--accent);color:#fff;border-radius:9px;cursor:pointer;font:600 13px inherit}}
.btn.ghost{{background:transparent;color:var(--accent)}}
h2{{font-size:15px;letter-spacing:.02em;margin:22px 0 8px;padding-bottom:5px;border-bottom:2px solid var(--line)}}
h2.hp{{color:var(--star);border-color:var(--star)}}
h3{{font-size:13px;margin:12px 0 4px;color:var(--muted)}}
ol,ul{{margin:4px 0 8px;padding-left:22px}} li{{margin:3px 0}}
li.done{{color:var(--muted);text-decoration:line-through}}
.who{{color:var(--accent);font-weight:600}}
.muted{{color:var(--muted);font-style:italic;list-style:none}}
.proj{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:8px 0}}
.pname{{font-weight:700}} .sub{{color:var(--muted);font-weight:400;font-size:13px}}
.txtwrap{{display:none;margin-top:16px}} textarea{{width:100%;height:320px;font:12px/1.5 ui-monospace,Menlo,monospace;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink)}}
</style></head><body><div class="wrap">
<div class="top"><div><h1>Weekly Report — {_e(lab)}</h1><div class="date">as of {_e(today)}</div></div>
<div class="grow"></div><button class="btn" id="copyBtn">📋 Copy as plain text</button>
<button class="btn ghost" id="viewBtn">View plain text</button></div>
{body}
<div class="txtwrap" id="txtwrap"><textarea id="plain" readonly>{_e(text)}</textarea></div>
</div><script>
const plain=document.getElementById('plain');
document.getElementById('copyBtn').onclick=async()=>{{ try{{await navigator.clipboard.writeText(plain.value);document.getElementById('copyBtn').textContent='copied ✓';}}catch(e){{document.getElementById('txtwrap').style.display='block';plain.select();document.execCommand('copy');document.getElementById('copyBtn').textContent='copied ✓';}} }};
document.getElementById('viewBtn').onclick=()=>{{const w=document.getElementById('txtwrap');w.style.display=w.style.display==='block'?'none':'block';}};
</script></body></html>"""

def main():
    data = load()
    lab = sys.argv[1] if len(sys.argv) > 1 else data["labs"][0]
    if lab not in data["labs"]:
        print("labs:", ", ".join(data["labs"])); sys.exit(1)
    out = os.path.join(ROOT, "reports", f"weekly_{lab.replace(' ','_').replace('/','-')}.html")
    with open(out, "w") as f: f.write(build_html(data, lab))
    print("wrote", out, "\n")
    print(build_text(data, lab))

if __name__ == "__main__":
    main()
