# Setup — start here

You need a Mac. It takes about five minutes, and nothing you enter ever leaves your computer.

## 1. Install it (once)

1. Open **Terminal**: press ⌘-Space, type `Terminal`, press Enter.
2. Copy this line, paste it into Terminal, and press Enter:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/Jonah-Keller/ResearchOps/main/install.sh | bash
   ```

3. **If a window pops up asking to install "command line developer tools"**, click
   **Install** and wait for it to finish (5–15 minutes). Then paste the same line
   into Terminal again. This only happens on Macs that have never had it.

ResearchOps opens in your browser, and a blue **RO** icon appears in your Dock.
You can close Terminal now.

## 2. Open it any time

Click the **RO** icon in your Dock. That's it.

## 3. Put your résumé in

The first time you open it, you land on **📥 Import résumé**. You can use any
chat AI you already have — ChatGPT, Claude or Gemini, free plans included:

1. Click **📋 Copy instructions**.
2. Open ChatGPT or Claude in another tab. Paste, then paste your résumé (or just
   type out everything you've done) right after it, and send.
3. Copy the chat's whole answer, paste it into box 2 in ResearchOps, and click
   **Preview**.
4. Check the list, then click **✓ Add these to my CV**.

You can do this again whenever you like. It only adds things that aren't
already there, and never changes what you have.

## 4. Fix anything by clicking it

Click **📄 Curriculum Vitae** in the sidebar. Every piece of text on the CV is
editable: click it, type, and it saves by itself. To print or save a PDF, use
**🖨 Full CV** at the top.

Papers and posters live under the lab in the sidebar ("My Research" to start).
When you move a paper along (in preparation → submitted → under review →
accepted), it moves to the right heading on the CV by itself.

## Your data

Everything is in one file on your Mac: `~/ResearchOps/data/projects.json`. It's
never uploaded, and backups are kept in `~/ResearchOps/data/backups/`.

## Getting updates

Paste the install line from step 1 into Terminal again. It updates the app and
leaves your data alone.

## If something goes wrong

- **The page won't load:** click the Dock icon again. If that doesn't help, restart
  the Mac and click it once more.
- **The import says it can't read the answer:** ask the chat to "reply with only
  the JSON code block", then paste again.
- The app's log is at `~/Library/Logs/ResearchOps.log`, if someone helping you asks.
