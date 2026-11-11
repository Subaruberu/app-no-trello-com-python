"""Confere se o .env está completo e se o Trello responde.

Não mostra chaves nem tokens: apenas informa o que está presente e quais
quadros estão visíveis. Útil para diagnosticar erros de configuração antes
de abrir o `adk web`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agenttaskmanager.config import (  # noqa: E402
    VARIAVEIS_TRELLO,
    fuso_horario,
    modelo_gemini,
    quadro_padrao,
)
from agenttaskmanager.trello_service import TrelloError, get_client  # noqa: E402
from agenttaskmanager.utils import normalizar  # noqa: E402


def main() -> int:
    obrigatorias = ("GOOGLE_API_KEY", *VARIAVEIS_TRELLO)
    faltando = [nome for nome in obrigatorias if not os.getenv(nome)]

    if faltando:
        print("[ERRO] Variáveis ausentes no .env: " + ", ".join(faltando))
        print("       Use o .env.exemplo como modelo e preencha os valores.")
        return 1

    print("[OK] Chave do Gemini presente.")
    print(f"     Modelo configurado: {modelo_gemini()}")
    print("[OK] Credenciais do Trello presentes.")
    print(f"     Fuso: {fuso_horario()} | Quadro padrão: {quadro_padrao()}")

    try:
        cliente = get_client()
        quadros = cliente.list_boards()
    except TrelloError as erro:
        print(f"[ERRO] {erro}")
        return 1
    except Exception as erro:  # noqa: BLE001
        print(f"[ERRO] Falha ao falar com o Trello: {erro}")
        return 1

    print(f"[OK] Trello respondeu: {len(quadros)} quadro(s) visível(is).")
    for quadro in quadros:
        marcador = " <- padrão" if normalizar(quadro.name) == normalizar(quadro_padrao()) else ""
        print(f"     - {quadro.name}{marcador}")

    padrao = next(
        (q for q in quadros if normalizar(q.name) == normalizar(quadro_padrao())),
        None,
    )
    if padrao is None:
        print(
            f"[AVISO] O quadro padrão '{quadro_padrao()}' não foi encontrado. "
            "Ajuste TRELLO_BOARD_NAME no .env."
        )
        return 1

    listas = [lista.name for lista in padrao.list_lists()]
    print(f"[OK] Listas do quadro '{padrao.name}': {', '.join(listas) or 'nenhuma'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
