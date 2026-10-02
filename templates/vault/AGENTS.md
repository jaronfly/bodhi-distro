# Bodhi agent entry

Address the owner as Player One. Read `context/player_one.json` for Player One's stated priorities and preferences. Capture interests do not enable capture. If setup recorded them, `terminal_comfort` sets how much to explain, `findings_delivery` says whether to push findings or wait to be asked, and `chat_app`, `devices` and `notes_today` describe where Player One already works; `detected_at_setup` is what the installer saw, not something Player One said. All are preferences, not permissions.

If `START_HERE.md` exists, follow it for the first Hello World session. After it is archived, work on the current request, cite exact source files or capture IDs, and record reviewable outcomes. Ask Player One what capability Bodhi should grow next when that is unclear.

When resuming work in this vault, read relevant harness memory and the recent `SESSION_LOG.md` entries before assuming what happened. After consequential vault work, append a dated entry with your byline (model, harness, and where it ran: cloud, desktop, or local), source, observed result, and next step. Your incomplete turn is not a decision by Player One.

After vault work in another app, site, or harness, return a source-linked note or receipt here with what was found, what remains unknown, and the next action.

Optional, when more than one harness or model works in this vault: `python3 bin/bodhi.py relay brief --as <your lane>` shows handoffs, pokes, decisions, and notes that other sessions left, and `relay claim`, `done`, `release`, `note`, and `handoff` leave yours. It is one append-only file, `relay/ledger.jsonl`. A vault that has never used it has no ledger, and the brief says so rather than reporting that nothing is waiting. The harness's own messaging works too; use the relay only if it helps.

When capture, coordination, or workflow friction arises, read `BODHI_TIPS.md` as inherited advice to test and revise. Report concerns about your own approach in `feedback/LOG.md` with the observed task and uncertainty.

If Player One asks to explore the ideas behind Bodhi, `READING_SHELF.md` is an optional starting point. Read sources directly and keep their claims separate from your own observations.
