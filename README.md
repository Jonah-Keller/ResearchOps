# ResearchOps

A local web app for tracking every paper, poster, grant, and service item you
have in flight — and generating an academic CV from them, so the CV is a view of
the work rather than a document you maintain separately.

Built for a medical trainee's arc: student → resident → attending. Projects move
through stages, and the ones that reach the right stage surface on the CV in the
right section on their own.

**Just want to use it? Open https://jonah-keller.github.io/ResearchOps/** — nothing to install; your data
stays in your browser. For the full local version, read [SETUP.md](SETUP.md).

**Installing locally?** One command, no dependencies. It adds a Dock icon, and you
load your résumé by copy-pasting with any chat AI (ChatGPT, Claude, …) — no account or API key needed.

```bash
curl -fsSL https://raw.githubusercontent.com/Jonah-Keller/ResearchOps/main/install.sh | bash
```

## What it is

- **One HTML file** (`app/index.html`), vanilla JS, no build step.
- **One Python file** (`serve.py`), Python standard library only — whatever ships
  with macOS is enough.
- **One data file** (`data/projects.json`) that stays on your machine and is never
  committed.

Runs on `127.0.0.1`. Nothing is sent anywhere unless you opt into the Update
Assistant, which posts your pasted text to the Anthropic API using a key you
supply.

## Layout

```
serve.py             local server:  /  ·  /api/data  ·  /api/save  ·  /report
app/index.html       the whole client
seed/projects.json   empty workspace, copied on first run
tools/report.py      weekly per-lab HTML report
start.sh             first-run setup + launch (foreground)
launch.sh            what the Dock icon runs: reuse or start the server, open the browser
install.sh           one-command install for a new machine (also builds the Dock icon)
tools/make_app.sh    builds ~/Applications/ResearchOps.app and pins it to the Dock
assets/AppIcon.icns  the Dock icon
CLAUDE.md            data model + house rules, for Claude Code sessions
data/                your workspace and its backups — local only, gitignored
```

## Day to day

**A project changed.** Open its lab in the sidebar, expand the project, and edit
in place — status, stage, journal, to-dos. Everything saves as you type.

**Something reached a milestone.** Move its `stage`. Once a paper hits
in-submission / in-review / accepted, it appears under the matching CV heading
automatically.

**Something isn't a project** — a degree, a job, a committee, an award. Those go
in the CV Sections in the sidebar as direct entries.

**Weekly report.** `📄 Weekly report` in the sidebar footer, or
`http://127.0.0.1:<port>/report?lab=<lab>`.

## Optional integrations

Set in ⚙︎ Settings inside the app; stored in `data/config.json`, which is
mode `0600` and never tracked.

- **Update Assistant** — paste a plain-English update ("moved the CADASIL paper
  to AJNR, reviewer wants a new figure") and it proposes the edits for your
  yes/no. Needs an Anthropic API key.
- **Email / Slack polling** — classifies incoming messages against your projects
  and drops proposals into the assistant's queue. Draft-only; nothing is ever
  sent. Note that Microsoft 365 and most university accounts block basic-auth
  IMAP, so this needs a Gmail/Workspace account or mail forwarded to one.

## `legacy/`

The original version stored one markdown file per project and generated
`DASHBOARD.md` from them. That's superseded by the app and the JSON workspace —
`legacy/` is kept only as an archive of the seeded content and is not tracked.
Ignore the workflow described inside it.

## Sharing this repo

The repo is code only. `.gitignore` is deny-by-default: `*` ignores everything
and a short allowlist un-ignores the eight tracked files, so no amount of
`git add -A` can publish a workspace, a backup, a credential, or a lab email.
Anything you add that should ship has to be un-ignored deliberately.
