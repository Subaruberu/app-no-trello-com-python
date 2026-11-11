"""Cria o quadro do Trello com as três listas usadas pelo agente.

Uso (com o .env já preenchido):
    python scripts/criar_quadro.py
    python scripts/criar_quadro.py --nome "Meu quadro"

O script é idempotente: se o quadro ou uma lista já existir, ele não
duplica nada.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Permite importar o pacote agenttaskmanager ao rodar de qualquer pasta.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agenttaskmanager.config import quadro_padrao  # noqa: E402
from agenttaskmanager.trello_service import TrelloError, get_client  # noqa: E402
from agenttaskmanager.utils import normalizar  # noqa: E402

LISTAS = ("A fazer", "Em andamento", "Concluído")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria o quadro e as listas do agente.")
    parser.add_argument(
        "--nome",
        default=quadro_padrao(),
        help="Nome do quadro (padrão: TRELLO_BOARD_NAME do .env).",
    )
    args = parser.parse_args()

    try:
        cliente = get_client()
        quadros = cliente.list_boards()
        quadro = next(
            (q for q in quadros if normalizar(q.name) == normalizar(args.nome)),
            None,
        )

        if quadro is None:
            quadro = cliente.add_board(args.nome)
            print(f"[OK] Quadro criado: {quadro.name}")
        else:
            print(f"[INFO] Quadro ja existente: {quadro.name}")

        existentes = {normalizar(lista.name) for lista in quadro.list_lists()}
        for nome_lista in LISTAS:
            if normalizar(nome_lista) in existentes:
                print(f"   - lista ja existe: {nome_lista}")
                continue

            quadro.add_list(nome_lista)
            print(f"   - lista criada: {nome_lista}")

    except TrelloError as erro:
        print(f"[ERRO] {erro}")
        return 1
    except Exception as erro:  # noqa: BLE001
        print(f"[ERRO] Erro inesperado: {erro}")
        return 1

    print("\nTudo pronto! Confira o quadro no Trello e rode: adk web")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
