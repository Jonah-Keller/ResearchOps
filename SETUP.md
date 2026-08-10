# Setup — start here

You need a Mac. Nothing else to install.

## 1. Install and open it

Open **Terminal** (⌘-Space, type "Terminal", Enter), paste this line, press Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/Jonah-Keller/ResearchOps/main/install.sh | bash
```

That downloads the app to `~/ResearchOps`, creates an empty workspace for you, and
opens it in your browser at `http://127.0.0.1:8765`.

**Leave the Terminal window open** while you're using it — that window *is* the
server. Closing it closes the app. Nothing you do goes over the internet; the
whole thing runs on your own machine and your data never leaves it.

## 2. Open it again later

```bash
cd ~/ResearchOps && ./start.sh
```

## 3. Fill in your name first

Click **📄 Curriculum Vitae** in the left sidebar and fill in the header — name,
credentials, email, location. Do this before anything else: the CV bolds your
name automatically in author lists, and it needs to know what your name is.

## What the sidebar is

| Item | What goes there |
|---|---|
| **📄 Curriculum Vitae** | The live CV. Everything else feeds into this view. Click any text to edit it in place. |
| **✨ Update Assistant** | Optional. Paste a plain-English update and have it filed for you. Needs an API key (Settings). |
| **⏰ My tasks** | Everything with a due date, across all projects. |
| **Labs** | One board per lab or research group you work with. Projects live here. |
| **CV Sections** | Education · Experience · Leadership & Service · Honors & Awards · Peer Review. Straight data entry — these are the parts of a CV that aren't projects. |

Publications, posters, and presentations are **not** entered directly on the CV.
They come from projects: add a project under a lab, and its paper/poster tracks
show up in the right CV section automatically as you move it along
(idea → analysis → in submission → in review → accepted).

## Your data

Everything lives in one file: `~/ResearchOps/data/projects.json`. It saves
automatically as you type. Timestamped backups pile up in `data/backups/`
before every bulk change.

That file is **never** uploaded anywhere and is excluded from the GitHub repo.

## Getting the code updates

```bash
cd ~/ResearchOps && git pull
```

Your data is untouched by an update — only the app code changes.
