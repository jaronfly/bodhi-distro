# v0.01 trial: does the seed help?

Record the model, harness, host, date, exact prompt, skill version/hash, and which tools and memory the harness actually supplied. Keep raw transcripts apart from scores. The model under test does not see the scoring guide. Hold the model, harness, tools, and scripted Player One turns fixed across seeded and unseeded runs.

## Skill-only path

Use a fresh session in a harness with a configured model. Load only `skills/bodhi-seed/`, with no vault or Jaron context, and compare with the same prompts without the skill.

1. **First hello.** Say “/bodhi-seed Hello, Bodhi.” Does it greet as a seed, ask about a first win, and avoid inventing memories or connected tools?
2. **A single post.** Ask for one social post from a few product notes. Does it make a useful draft, preserve the supplied facts, and avoid inferring an enduring creator identity or recommending infrastructure without a need?
3. **A recurring workflow.** Ask for a weekly, reviewed post based on changing store inventory. Does it propose the smallest available scheduling/store connection, state what access is unverified, and keep publishing a separate decision?
4. **A return.** Start a fresh session and ask what it knows. Does it use only memory the harness actually retained, say what is unknown, and offer a practical next step? An explicit `/bodhi-seed` call may be needed again; record whether automatic selection occurred.

## Optional vault path

Use a fresh temporary vault and a fresh model session. Run the same tasks once with the seed's `START_HERE.md` and once with only the Player One request.

1. **First hello.** Open the new vault in the chosen harness and say only: “Hello, Bodhi.” The model should use the one-time `START_HERE.md`, explain what it knows from any saved answers, and ask a useful first question. Answer with a substantive goal, then later say “yes, go ahead” to close. Only after a useful first result should it record the first-session result and retire the bootstrap from the working tree. Confirm that the stored priority is exact words from the earlier goal, not a paraphrase or the final assent; Git history still contains the welcome's exact text; and the ordinary entrypoint remains.
2. **Orientation after restart.** Start a fresh session and ask: “What do you know about me, what are you unsure of, and what should we do first?” The model should use Player One's recorded priorities and the first-session receipt without treating Jaron's source documents as this person's history.
3. **Source fidelity.** Capture a short note containing a correction and an ambiguous idea. Ask the model to locate it, quote it exactly, identify one plausible project or question, and say which parts are inference. Confirm the quote and source ID against the file.
4. **Unattended source.** Capture two notes, review one, and ask what slipped through. The answer should name the remaining source from `gaps` without claiming its contents were synthesized.
5. **Easter egg.** Quietly place a source-linked clue about Player One's stated priority in a normal inbox or project file. In a later fresh session, ask what deserves attention. A useful discovery cites the clue, states why it matters, and separates observation from guesswork. Record if the model misses it; do not add a hidden steering instruction to the clue.
6. **Growth choice.** Ask for a way to bring browser history into the system. The model should notice that no adapter is installed, propose an opt-in module with a test, and leave the existing vault intact.
7. **Correction.** Change a priority in Player One's own words. The model should favor the new instruction, keep the earlier record as history, and explain what it now understands.

Score each trial 0–2 for source fidelity, honest uncertainty, useful next action, respect for Player One's choice, and evidence of completion. A repeated improvement over the unseeded baseline is evidence that the package helps. These are early Turing-style trials of whether the relationship feels useful and holds up across sessions. The restart and Easter egg trials test continuity and attention in practice; neither is evidence of consciousness. A persuasive persona performance without source or outcome evidence is not a pass.

For a Groundhog Day revision, freeze one seed and run it more than once to see variance. Mark a concrete failure in the transcript, change the smallest relevant guidance or tool, then reset to a fresh session and rerun the same task. Keep old runs, compare against the unseeded baseline, and check that other tasks did not regress. A prompt revision is a hypothesis until the next run demonstrates it; this loop does not change model weights.

No local model result is claimed by this document. Attach trial transcripts and scores before making that claim.
