"""SCX-MCP-13: the server ships usage methodology as MCP `instructions` on initialize."""

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from solucortex_mcp.server import INSTRUCTIONS, mcp, solucortex_recall


def test_instructions_cover_the_workflow_and_rules():
    assert mcp.instructions == INSTRUCTIONS
    for required in (
        "solucortex_recall",
        "solucortex_search",
        "solucortex_remember",
        "architecture",
        "external_integration",
        "never store secrets",
        "pending",
    ):
        assert required in INSTRUCTIONS, f"missing: {required}"


@pytest.mark.anyio
async def test_initialize_exposes_instructions_to_clients(http_server):
    async with streamablehttp_client(
        f"{http_server}/mcp", headers={"Authorization": "Bearer scx_test"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            result = await session.initialize()
    assert result.instructions is not None
    assert "solucortex_recall" in result.instructions


def test_instructions_declare_the_agent_rule_for_an_arbitrary_recall_cutoff():
    """CORE-OPS-07 — Criterio de cierre (3): `recall` puede devolver una selección
    parcial (top-N por relevancia) sin que el agente lo note. La regla de qué debe
    hacer el agente ante ese corte arbitrario tiene que estar escrita en algún lugar
    que el agente realmente lea antes de actuar: las `instructions` globales del
    servidor (INSTRUCTIONS) y/o el docstring de la tool `solucortex_recall`
    (lo que el cliente MCP muestra al modelo por cada tool).

    La regla debe cubrir, como mínimo, ambas mitades del criterio de cierre:
    (a) que recall puede NO estar devolviendo todo lo elegible (menciona el corte
        por tipo / total disponible), y
    (b) qué hacer al respecto: una segunda consulta dirigida al tipo que falta, o
        declarar explícitamente cuánto se leyó del total disponible.

    LÍMITE DE ALCANCE (Criterio de cierre, punto 4 — literal, no resumido):
    "Este test verifica que la regla está declarada en las instrucciones. NO
    verifica que los agentes la apliquen. La aplicación no está cubierta."
    Este test es sintáctico/documental: pasa si el texto existe, no si un agente
    real actúa según él (eso, hoy, no es verificable sin un harness de agentes
    reales y no está en el alcance de esta tarea — ver también el precedente del
    harness/§09-F citado en el Aprendizaje esperado de la tarea).
    """
    combined = (INSTRUCTIONS + "\n" + (solucortex_recall.__doc__ or "")).lower()

    assert any(
        marker in combined
        for marker in ("total_available", "por tipo", "per type", "partial selection", "selección parcial")
    ), (
        "las instrucciones deben advertir que recall puede ser una selección "
        "parcial (no 'ya leí todo'), no solo describir el flujo feliz"
    )

    assert any(
        phrase in combined
        for phrase in (
            "second, targeted query",
            "segunda consulta",
            "consulta dirigida",
            "targeted follow-up query",
            "puede faltar contexto",
            "may be missing",
            "declare how many",
            "declarar cuántas",
            "declarar cuantas",
        )
    ), (
        "las instrucciones deben decir qué hacer ante un corte arbitrario: "
        "una segunda consulta dirigida al tipo, o declarar N/M leídas explícitamente"
    )
