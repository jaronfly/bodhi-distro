# A deeper memory: notes, a graph, or nothing yet?

Read this when Player One asks for "better memory," "a second brain," or "a graph," or when you catch yourself about to suggest one. It is a set of questions, not a recommendation. Ask yourself first, then ask Player One, and let their answers choose. Do not assume the seed's own examples, including the tools the first fleet used, fit this person.

## First, ask yourself

1. **What is actually being lost today?** Name one real case from this installation. There are three different losses:
   - **text**: the exact words are gone, or only a summary survives;
   - **relations**: the pieces exist, but no one can see how they connect;
   - **history**: what was true before a change, or who changed it and why.
   If you cannot name a case, that is the answer for now.
2. **Who would read the structure?** Player One browsing and writing it, or agents querying it? These lead to different tools.
3. **What already covers it?** The harness's own memory and search, the project's files and Git history, and, if Player One uses it, the Bodhi vault. Its captures keep exact text; its relay keeps handoffs and decisions. A new layer has to beat these on the real case, not in principle.
4. **What would it cost?** Setup time, a running service, money, and the attention to keep it accurate. A graph that nobody rebuilds or checks drifts from its sources.

## Then ask Player One why

Put these in plain words, one at a time, and keep the answers verbatim:

- "Do you already keep notes somewhere? Where, and do you like it?"
- "When you look for something from last month, what do you do, and what goes wrong?"
- "Would you rather browse and write the notes yourself, or mostly have the AI find things for you?"
- "Is your work mostly code, or mostly writing, research, and projects?"
- "Is there anything you would not want indexed or kept?"

If their answers and your case disagree, show the disagreement and ask. Their "why" outranks your guess.

## The three honest answers

**No graph yet.** This is a legitimate choice, and the default until relations are actually being lost. Plain files, the harness's own search and memory, and the optional vault cover a lot. *Acceptance:* in a fresh session, last week's source is found with the tools already present, and its exact words are quoted.

**A notes vault the person reads and writes.** [Obsidian](https://obsidian.md) is one example; [Logseq](https://logseq.com) is another. Obsidian keeps local Markdown files, with backlinks, a graph view, and plugins. It fits a Player One who writes notes and wants to see the links. Agents can read and write the same files, because they are just Markdown. MCP servers such as [Basic Memory](https://github.com/basicmachines-co/basic-memory) work over such a folder. *Acceptance:* Player One opens a note an agent wrote and follows its link to the source. In a fresh session, an agent finds a note Player One wrote, by its title.

**A graph the agents query.** [Memtrace](https://github.com/syncable-dev/memtrace-public) is what the first fleet ran. It parses a codebase into symbols, calls, and history and serves them over MCP. It fits code-heavy work. At the time of writing it is a proprietary beta, so check its current terms. General-purpose alternatives include the [Knowledge Graph Memory Server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) and [Graphiti](https://github.com/getzep/graphiti). *Acceptance:* an agent answers one structural question, such as "what calls this?" or "what changed here since the 1st?", and the answer checks out against the files. One relation traces back to its source, and the graph can be rebuilt from the sources. That is the "Optional graph" row in the seed repository's `MODULES.md`.

Both at once is possible: people-facing notes plus an agent-facing index. Start with one, and add the second only when the first shows a gap.

## Record the choice

Write the decision where the next session will find it, with Player One's own words for the why and a date to revisit. That can be the harness's memory, or `python3 bin/bodhi.py relay decide "Memory: no graph yet" "<their words>"` in a vault. Then run the acceptance test in a fresh session and record what happened, including if it failed. The first fleet's tools and their results are in [tools from the first fleet](FLEET_TOOLS.md).
