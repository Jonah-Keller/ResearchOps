# ResearchOps — working notes for Claude Code

A local, zero-dependency web app for tracking research projects and generating an
academic CV from them. `serve.py` (stdlib only) serves `app/index.html` and reads
and writes one JSON file. There is no build step, no framework, and no test suite.

## Layout

```
serve.py             HTTP server + Anthropic/IMAP/Slack integrations. Stdlib only.
app/index.html       The entire client — ~2,300 lines of vanilla JS in one file.
seed/projects.json   Empty workspace template, copied on first run. Never edit
                     to add real content.
tools/report.py      Weekly per-lab HTML report, served at /report?lab=<lab>.
data/projects.json   THE workspace. Not in git. This is what you edit.
data/backups/        Timestamped copies. Not in git.
data/config.json     API key, email app password. Not in git. Never read, print,
                     echo, or commit this file.
start.sh             Seeds data on first run, picks a free port, opens browser.
```

Everything except the files listed in `.gitignore`'s allowlist is untracked. The
ignore file is deny-by-default (`*` then `!path` un-ignores), because this repo
sits on top of private research data. Do not weaken it. Do not un-ignore `data/`.

## The data model

`data/projects.json` is a single object:

| Key | Shape | What it is |
|---|---|---|
| `profile` | object | CV header: `name`, `credentials`, `email`, `phone`, `location`, `scholar`, `orcid`, `linkedin`, `links[]`, `cvHidden` |
| `labs` | string[] | Sidebar labs, followed by the five CV section names |
| `projects` | object[] | The research board. See below. |
| `groups` | object[] | Programs/themes that projects nest under (`id`, `name`, `lab`) |
| `entries` | object[] | CV items that aren't projects. See below. |
| `grants` | object[] | Funding pipeline (`name`, `sponsor`, `amount`, `deadline`, `status`, `owner`) |
| `clerical` | object[] | Admin to-dos per lab (`text`, `status`, `date`) |
| `tracks` | string[] | Fixed: `funding, data, analysis, poster, paper` |
| `specimens` | object[] | Wet-lab tissue tracker. Hidden from the sidebar unless non-empty or `flags.specimens` is true. |
| `omics` | object | Optional multi-omics planning board (arms → steps → tasks). Shown only for the lab named in `flags.omicsLab`; empty and hidden otherwise. |
| `flags` | object | Feature toggles: `specimens` (force-show the tracker), `omicsLab` (which lab, if any, shows the omics board). |
| `updated` | string | Stamped by the server on save. Don't set it by hand. |

### `entries[]` — direct CV items

```json
{ "id": "e123", "section": "Education", "title": "…", "org": "…",
  "date": "Aug 2025 – Present", "city": "Philadelphia, PA", "amount": "",
  "note": "", "gpa": "", "awards": "", "activities": "" }
```

`section` must be exactly one of:
`Education` · `Experience` · `Activities` · `Funding / Scholarship` · `Peer Review Activity`

Those render as Education · Experience · **Leadership & Service** · **Honors &
Awards** · Peer Review. The stored value and the display label differ — always
write the stored value.

Field meaning shifts by section: for `Education`, `title` is the institution and
`org` is the degree; for `Experience`, `title` is the position and `org` is the
organization; for `Funding / Scholarship`, `org` is the sponsor and `amount` is
the award. `gpa`/`awards`/`activities` are Education-only.

### `projects[]` — publications, posters, and everything in flight

```json
{ "id": "slug", "name": "…", "lab": "ELab", "group": "", "priority": 0,
  "pi": ["…"], "dirs": [], "tags": [], "stage": "analysis", "dataset": "",
  "archived": false, "authorship": {…}, "posters": [],
  "tracks": { "funding": {"status":"","items":[]}, "data": {…},
              "analysis": {…}, "poster": {…}, "paper": {…} } }
```

`stage` drives which CV section a project lands in, in this order:
`idea → data-collection → analysis → manuscript-prep → ready-for-feedback →
responding-to-feedback → prepared-for-submission → in-submission → in-review →
in-revision → rejected → accepted`.

Track items are `{id, text, done, owner, date, due, priority, notes, links[], subtasks[]}`.

**Publications and posters are never entered as `entries`.** They come from
projects. If asked to add a paper or a poster to the CV, add or update a project.

## Ingesting someone's activity list

The common task: they paste a résumé, a list of activities, or an application
draft, and want it turned into the workspace.

1. Read `data/projects.json` first. Never assume it's empty.
2. Back up before writing: `cp data/projects.json "data/backups/projects.pre-<slug>-$(date +%Y%m%d-%H%M%S).json"`
3. Sort each item: is it a paper/poster/project in flight (→ `projects`), or a
   static CV line (→ `entries`)? Grants and awards with a sponsor and a dollar
   amount can go in `grants`, on the CV as `Funding / Scholarship`, or both —
   ask which they want rather than duplicating silently.
4. Add any new lab or research group to `labs` before referencing it from a project.
5. `id` must be unique. Entries use `e<digits>`, projects use a slug, grants `g<digits>`.
6. Preserve their wording. Don't invent dates, titles, PIs, or metrics — leave a
   field blank and flag it rather than guessing.
7. Validate before you finish: `python3 -c "import json;json.load(open('data/projects.json'))"`

## Editing the file while the app is open

The browser holds the whole workspace in memory and PUTs it back on every edit.
The server compares mtimes and returns 409 if the file changed underneath, which
makes the page reload from disk — so an unsaved browser edit can be lost.

After you write to `data/projects.json`, tell them to **reload the browser tab**.
If they were mid-edit in the app, have them let it save first, then write.

## Conventions in `app/index.html`

- Vanilla DOM via the `el(tag, class, text)` helper. No framework, no bundler.
- `render()` = `renderSide()` + `renderMain()`; almost every mutation ends with
  `queueSave(); renderMain();`.
- Nothing personal is hardcoded. Owner name comes from `myName()` (reads
  `profile.name`), and `boldMe()` bolds that person in author lists in both
  "First Last" and "Last F.M." forms. Keep it that way — this repo is shared.
- Escape user text with `esc()` before putting it in `innerHTML`.
- Match the existing dense one-line style rather than reformatting.

## Don't

- Commit anything under `data/`, `legacy/`, `reports/`, or any `.eml`.
- Print, log, or paste the contents of `data/config.json`.
- Rewrite `README.md`'s history or `git add -A` outside this repo's allowlist.
- Add a dependency. The whole point is that `./start.sh` works on a stock Mac.
