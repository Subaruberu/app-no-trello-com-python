"""Testa as ferramentas contra o Trello real, sem usar o Gemini.

O script cria um card de teste, lista, move para "Em andamento", move para
"Concluído" e remove o card no final. Assim você valida credenciais, nomes
das listas e o fluxo completo sem gastar a cota diária do Gemini.

Uso:
    python scripts/teste_real.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agenttaskmanager.config import fuso_horario, quadro_padrao  # noqa: E402
from agenttaskmanager.trello_service import (  # noqa: E402
    TrelloError,
    criar_tarefa,
    listar_tarefas,
    mover_tarefa,
    remover_tarefa,
)


def main() -> int:
    fuso = fuso_horario()
    agora = datetime.now(ZoneInfo(fuso))
    nome = f"Teste do agente {agora:%d/%m/%Y %H:%M:%S}"
    hoje = agora.strftime("%Y-%m-%d")
    quadro = quadro_padrao()
    removida = False
    criada = False

    print(f"Quadro: {quadro}")
    print(f"Tarefa de teste: {nome}")

    try:
        tarefa = criar_tarefa(
            nome=nome,
            descricao="Card criado pelo teste_real.py. Pode apagar.",
            due_date=hoje,
            quadro=quadro,
        )
        print(f"[OK] 1/4 Criada em '{tarefa['status']}' (vence {tarefa['vencimento']}).")
        criada = True

        tarefas = listar_tarefas("todas", quadro)
        encontrada = any(item["id"] == tarefa["id"] for item in tarefas)
        print(f"[OK] 2/4 Listagem: {len(tarefas)} tarefa(s); teste encontrado: {encontrada}.")
        if not encontrada:
            print("[ERRO] O card criado não apareceu na listagem.")
            return 1

        andamento = mover_tarefa(nome, "em andamento", quadro)
        print(f"[OK] 3/4 Movida: {andamento['origem']} -> {andamento['destino']}.")

        concluido = mover_tarefa(nome, "concluído", quadro)
        print(f"[OK] 4/4 Movida: {concluido['origem']} -> {concluido['destino']}.")

        remover_tarefa(nome, quadro)
        removida = True
        print("[OK] Card de teste removido do quadro.")
    except TrelloError as erro:
        print(f"[ERRO] {erro}")
        return 1
    except Exception as erro:  # noqa: BLE001
        print(f"[ERRO] Falha inesperada: {erro}")
        return 1
    finally:
        if criada and not removida:
            try:
                remover_tarefa(nome, quadro)
                print("[INFO] Limpeza: card de teste removido.")
            except Exception:  # noqa: BLE001
                print("[AVISO] Não foi possível remover o card de teste; apague no Trello.")

    print("\nFluxo completo validado no Trello real.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
