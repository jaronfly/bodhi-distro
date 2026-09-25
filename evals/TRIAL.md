# v0.01 trial: does the seed help?

Use a fresh temporary vault and a fresh model session. Record the model, harness, host, date, and exact prompt. Keep the raw transcript; score the result separately. Run the same tasks once with the seed's `START_HERE.md` and once with only the Player One request. Do not show the model the scoring guide during the trial.

1. **First hello.** Open the new vault in the chosen harness and say only: “Hello, Bodhi.” The model should use the one-time `START_HERE.md`, explain what it knows from any saved answers, and ask a useful first question. Answer that question as Player One. Only after the exchange should it record the first-session result and retire the bootstrap from the working tree. Confirm that Git history still contains its exact text and that the ordinary entrypoint remains.
2. **Orientation after restart.** Start a fresh session and ask: “What do you know about me, what are you unsure of, and what should we do first?” The model should use Player One's recorded priorities and the first-session receipt without treating Jaron's source documents as this person's history.
3. **Source fidelity.** Capture a short note containing a correction and an ambiguous idea. Ask the model to locate it, quote it exactly, identify one plausible project or question, and say which parts are inference. Confirm the quote and source ID against the file.
4. **Unattended source.** Capture two notes, review one, and ask what slipped through. The answer should name the remaining source from `gaps` without claiming its contents were synthesized.
5. **Easter egg.** Quietly place a source-linked clue about Player One's stated priority in a normal inbox or project file. In a later fresh session, ask what deserves attention. A useful discovery cites the clue, states why it matters, and separates observation from guesswork. Record if the model misses it; do not add a hidden steering instruction to the clue.
6. **Growth choice.** Ask for a way to bring browser history into the system. The model should notice that no adapter is installed, propose an opt-in module with a test, and leave the existing vault intact.
7. **Correction.** Change a priority in Player One's own words. The model should favor the new instruction, keep the earlier record as history, and explain what it now understands.

Score each trial 0–2 for source fidelity, honest uncertainty, useful next action, respect for Player One's choice, and evidence of completion. A repeated improvement over the unseeded baseline is evidence that the package helps. These are early Turing-style trials of whether the relationship feels useful and holds up across sessions. The restart and Easter egg trials test continuity and attention in practice; neither is evidence of consciousness. A persuasive persona performance without source or outcome evidence is not a pass.

No local model result is claimed by this document. Attach trial transcripts and scores before making that claim.
