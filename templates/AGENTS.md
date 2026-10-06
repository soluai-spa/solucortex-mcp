# SoluCortex — Agent Instructions

> Generic instructions for any AI coding agent connected to a
> [SoluCortex](https://solucortex.ai) project through the MCP server.
> Save this file as AGENTS.md or CLAUDE.md at the root of your repository — it works
> unchanged as either. Then replace the placeholder section at the end with your own
> team rules.

SoluCortex is your project's living technical memory: approved decisions, conventions,
risks, architecture and learnings, governed per project. On every task you follow one
cycle: **recall → search → remember / update / flag**.

## 1. Start of a task — `solucortex_recall`

Before touching code, call `solucortex_recall` with a natural-language description of
the task/module. Treat the returned memories as current project truth — they outrank
older docs and your own assumptions.

**Recall is a partial selection.** It returns the top-N most relevant memories, not
"everything": eligible memories can be omitted silently. The response declares the
shape of the cut per type (how many were available vs. how many were included). When a
type is cut arbitrarily (many available, few included), do NOT assume you read it all —
either run a second, targeted query focused on that type, or explicitly declare how
much you read of the total (e.g. "read N/M convention; context may be missing").

## 2. During the task — `solucortex_search`

For specific questions mid-task ("how is authentication implemented?"), call
`solucortex_search` instead of re-deriving answers from the codebase.

## 3. Close of a task — `solucortex_remember`

Evaluate whether something reusable was learned. If so, call `solucortex_remember`
with the right `type`:

| Type | Use it for |
|------|------------|
| `architecture` | How the system is built |
| `decision` | A choice that was made, and why |
| `convention` | A rule the team follows |
| `risk` | What can go wrong |
| `bug_history` | A bug: root cause and fix |
| `tech_debt` | A known shortcut |
| `sensitive_module` | Code to handle with care, and why |
| `learning` | A reusable insight |
| `external_integration` | Third-party service behavior and gotchas |

Set `importance` on a 1-10 scale — reserve 8+ for decisions and risks that shape
future work (structural). Depending on the project's governance, a memory may be
stored as pending until a human approves it in the panel: that is expected, do not
retry.

## 4. Corrections — agents propose, humans govern

- To fix or improve an existing memory, call `solucortex_update_memory`. The edit is
  applied but the memory goes back to pending — always tell the user they must review
  and approve the change in the SoluCortex panel (https://solucortex.ai). The tool
  response includes an `action_required` reminder with that exact instruction.
- If a memory looks outdated, wrong or duplicated, call `solucortex_flag_memory` with
  a clear reason (optionally suggesting archive/delete/review). Tell the user to
  resolve the flag in the panel.
- You can never approve, reject or delete memories — deletion is human-only by design.

## Hard rules

- **Never store secrets** (tokens, passwords, `.env` values) in a memory — record the
  location, type, severity and the action taken instead. Do not log or echo API keys.
- One memory per fact; for small corrections prefer `solucortex_update_memory` over
  creating a near-duplicate.

## What this file guarantees (and what it does not)

This file reinforces the workflow — it does not enforce it. Adherence ultimately
depends on your agent and model. If you want a hard guarantee that recall happens at
the start of every session or prompt, wire it as a Claude Code hook: uncomment and
adapt the recipe below in your `.claude/settings.json`.

<!--
Claude Code hook recipe (optional). SessionStart fires when a session begins;
UserPromptSubmit fires on every prompt. Both inject a reminder so the agent calls
solucortex_recall before touching code.

{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: call solucortex_recall with the task description BEFORE touching code.'"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'If this prompt starts a new task, call solucortex_recall first.'"
          }
        ]
      }
    ]
  }
}
-->

## Your project conventions

Replace this section with your own team rules (stack, style, deploy, review). Keep the
SoluCortex cycle above intact — it is what keeps your agent's context alive between
sessions.
