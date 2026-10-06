"""SCX-MCP-19: generic AGENTS.md template distributed to external SoluCortex clients.

Single parametrized spec (task budget: max 1 pytest test). Traces to the task fields:
  - Output operativo esperado: templates/AGENTS.md (generic, self-contained, client-conventions
    placeholder, commented hook recipe) + README linking it.
  - Restricciones: ZERO internal-SoluAI references (word-bounded absence), "SoluCortex" present,
    English audience, honest about the file reinforcing (the hook guarantees).
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "AGENTS.md"
README = ROOT / "README.md"

I = re.IGNORECASE
S = re.DOTALL

# (case id, kind, pattern, flags, source) ; source: "template" or "readme"
CASES = [
    # --- exists / non-empty / audience --------------------------------------------------
    ("non_empty", "present", r"\S{3,}", 0, "template"),
    ("is_english", "absent", r"\b(para|los|las|nunca|debe|tarea|proyecto|memoria)\b", I, "template"),
    ("mentions_solucortex", "present", r"\bSoluCortex\b", 0, "template"),
    # --- methodology markers (what the file must teach) ---------------------------------
    ("recall_at_task_start", "present", r"solucortex_recall", 0, "template"),
    ("search_during", "present", r"solucortex_search", 0, "template"),
    ("remember_at_close", "present", r"solucortex_remember", 0, "template"),
    ("recall_partial_cut_targeted_query", "present", r"targeted", I, "template"),
    ("recall_partial_cut_declare_n_of_m", "present", r"\bN/M\b", 0, "template"),
    *[
        (f"type_{t}", "present", rf"\b{t}\b", 0, "template")
        for t in (
            "architecture",
            "decision",
            "convention",
            "risk",
            "bug_history",
            "tech_debt",
            "sensitive_module",
            "learning",
            "external_integration",
        )
    ],
    ("importance_scale_1_10", "present", r"1\s*[-–]\s*10", 0, "template"),
    ("importance_8_plus_structural_only", "present", r"8\+", 0, "template"),
    ("update_tool", "present", r"solucortex_update_memory", 0, "template"),
    ("flag_tool", "present", r"solucortex_flag_memory", 0, "template"),
    ("tell_user_to_approve_in_panel", "present", r"approv\w+.{0,120}panel|panel.{0,120}approv\w+", I | S, "template"),
    ("action_required_mentioned", "present", r"action_required", 0, "template"),
    ("never_secrets", "present", r"never.{0,60}secrets", I | S, "template"),
    ("delete_is_human", "present", r"delet\w+.{0,100}human|human.{0,100}delet\w+", I | S, "template"),
    ("honest_pending_moderation", "present", r"pending", I, "template"),
    ("works_as_agents_or_claude_md", "present", r"AGENTS\.md or CLAUDE\.md", 0, "template"),
    ("client_conventions_placeholder_section", "present", r"^#+ .*conventions", I | re.MULTILINE, "template"),
    ("hook_recipe_sessionstart_commented", "present", r"<!--(?:(?!-->).)*SessionStart(?:(?!-->).)*-->", S, "template"),
    ("hook_recipe_userpromptsubmit_commented", "present", r"<!--(?:(?!-->).)*UserPromptSubmit(?:(?!-->).)*-->", S, "template"),
    # --- Restricciones: no internal SoluAI references (word-bounded) --------------------
    ("no_SoluAI", "absent", r"\bSoluAI\b", 0, "template"),
    ("no_CORE_case_sensitive", "absent", r"\bCORE\b", 0, "template"),  # IGNORECASE would hit "core"
    ("no_Notion", "absent", r"\bNotion\b", 0, "template"),
    ("no_soluaicore", "absent", r"\bsoluaicore\b", I, "template"),
    ("no_pipeline_v3", "absent", r"\bpipeline v3\b", I, "template"),
    # --- Output: README links the template ----------------------------------------------
    ("readme_links_template", "present", r"templates/AGENTS\.md", 0, "readme"),
]


@pytest.mark.parametrize(
    "kind,pattern,flags,source",
    [pytest.param(k, p, f, s, id=cid) for cid, k, p, f, s in CASES],
)
def test_agents_template_ships_the_generic_client_methodology(kind, pattern, flags, source):
    assert TEMPLATE.is_file(), f"missing {TEMPLATE.relative_to(ROOT)}"
    text = (TEMPLATE if source == "template" else README).read_text(encoding="utf-8")
    assert text.strip(), f"{source} is empty"
    found = re.search(pattern, text, flags) is not None
    if kind == "present":
        assert found, f"{source}: missing /{pattern}/"
    else:
        assert not found, f"{source}: forbidden /{pattern}/ found"
