"""Camada de acesso ao Trello.

Toda a conversa com a API fica concentrada aqui. As ferramentas do agente
(em `agent.py`) só traduzem o resultado para texto amigável.

Vantagens de separar assim:
- a conexão é criada uma única vez (antes era repetida em cada função);
- as regras de status e de data ficam em um só lugar;
- os testes podem usar um cliente falso, sem chamar o Trello de verdade.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from trello import TrelloClient

from .config import VARIAVEIS_TRELLO, fuso_horario, quadro_padrao
from .utils import formatar_data_hora, normalizar, parse_due_date

# Grupos de nomes aceitos para cada status. As chaves e os valores já estão
# normalizados (sem acento, minúsculos), então "Concluído" e "CONCLUIDO"
# caem no mesmo grupo.
STATUS_ALIASES: dict[str, set[str]] = {
    "a fazer": {
        "a fazer",
        "todo",
        "to do",
        "backlog",
        "pendente",
        "a iniciar",
        "nao iniciado",
        "nao comecado",
    },
    "em andamento": {
        "em andamento",
        "andamento",
        "doing",
        "em progresso",
        "fazendo",
        "in progress",
    },
    "concluido": {
        "concluido",
        "concluida",
        "done",
        "feito",
        "feita",
        "finalizado",
        "finalizada",
        "completo",
        "completa",
    },
}

STATUS_VALIDOS = "'a fazer', 'em andamento' ou 'concluido'"


class TrelloError(Exception):
    """Erro esperado, com uma mensagem pronta para mostrar ao usuário."""


@lru_cache(maxsize=1)
def get_client() -> TrelloClient:
    """Cria (uma vez) e devolve o cliente do Trello.

    A conexão era repetida em cada ferramenta do código original. Agora
    todas usam esta função, que também valida as credenciais.
    """
    faltando = [nome for nome in VARIAVEIS_TRELLO if not os.getenv(nome)]
    if faltando:
        raise TrelloError(
            "Credenciais do Trello ausentes: "
            + ", ".join(faltando)
            + ". Preencha o arquivo .env (use o .env.exemplo como modelo)."
        )

    return TrelloClient(
        api_key=os.environ["TRELLO_API_KEY"],
        api_secret=os.environ["TRELLO_API_SECRET"],
        token=os.environ["TRELLO_TOKEN"],
    )


def listar_quadros() -> list[str]:
    """Retorna o nome de todos os quadros visíveis para o token."""
    return [quadro.name for quadro in get_client().list_boards()]


def obter_quadro(nome_do_quadro: str | None = None) -> Any:
    """Encontra um quadro pelo nome (sem diferenciar maiúsculas/acentos)."""
    nome = (nome_do_quadro or quadro_padrao()).strip()
    quadros = get_client().list_boards()

    for quadro in quadros:
        if normalizar(quadro.name) == normalizar(nome):
            return quadro

    disponiveis = ", ".join(quadro.name for quadro in quadros) or "nenhum"
    raise TrelloError(
        f"Quadro '{nome}' não encontrado. Quadros disponíveis: {disponiveis}. "
        "Ajuste TRELLO_BOARD_NAME no .env ou informe o nome do quadro."
    )


def obter_lista(listas: list[Any], status: str) -> Any | None:
    """Encontra a lista correspondente a um status.

    Devolve None quando o status é "todas" (usado pela listagem).
    Aceita o nome exato da lista ou apelidos como "done", "concluída" etc.
    """
    alvo = normalizar(status)

    if not alvo or alvo in {"todas", "todos", "all"}:
        return None

    # 1) Nome exato da lista (ignorando acentos e maiúsculas).
    for lista in listas:
        if normalizar(lista.name) == alvo:
            return lista

    # 2) Apelidos do status.
    for aliases in STATUS_ALIASES.values():
        if alvo in aliases:
            for lista in listas:
                if normalizar(lista.name) in aliases:
                    return lista

            nomes = ", ".join(lista.name for lista in listas) or "nenhuma"
            raise TrelloError(
                f"O status '{status}' foi reconhecido, mas não há uma lista "
                f"correspondente no quadro. Listas encontradas: {nomes}."
            )

    raise TrelloError(
        f"Status '{status}' não reconhecido. Use {STATUS_VALIDOS}."
    )


def _localizar_card(quadro: Any, nome_ou_id: str) -> tuple[Any, Any]:
    """Procura um card em todas as listas do quadro, por id ou nome exato."""
    alvo = (nome_ou_id or "").strip()
    if not alvo:
        raise TrelloError("Informe o nome da tarefa.")

    alvo_normalizado = normalizar(alvo)

    for lista in quadro.list_lists():
        for card in lista.list_cards():
            if card.id == alvo or normalizar(card.name) == alvo_normalizado:
                return lista, card

    raise TrelloError(f"Tarefa '{alvo}' não encontrada no quadro '{quadro.name}'.")


def _card_para_dict(card: Any, lista: Any, quadro: Any) -> dict[str, str]:
    return {
        "id": card.id,
        "nome": card.name,
        "descricao": card.desc or "",
        "vencimento": formatar_data_hora(getattr(card, "due", None), fuso_horario()),
        "status": lista.name,
        "quadro": quadro.name,
    }


def criar_tarefa(
    nome: str,
    descricao: str = "",
    due_date: str | None = None,
    quadro: str | None = None,
) -> dict[str, str]:
    """Cria um card na lista "A fazer" do quadro."""
    nome = (nome or "").strip()
    if not nome:
        raise TrelloError("O nome da tarefa é obrigatório.")

    board = obter_quadro(quadro)
    listas = board.list_lists()
    lista_destino = obter_lista(listas, "a fazer")

    if lista_destino is None:  # proteção extra: "a fazer" nunca é "todas"
        raise TrelloError("A lista 'A fazer' não foi encontrada no quadro.")

    try:
        vencimento = parse_due_date(due_date, fuso_horario())
    except ValueError as erro:
        raise TrelloError(str(erro)) from erro

    card = lista_destino.add_card(
        name=nome,
        desc=descricao or "",
        due=vencimento,
    )
    return _card_para_dict(card, lista_destino, board)


def listar_tarefas(
    status: str = "todas",
    quadro: str | None = None,
) -> list[dict[str, str]]:
    """Lista os cards de todas as listas ou de um status específico."""
    board = obter_quadro(quadro)
    listas = board.list_lists()
    lista_filtrada = obter_lista(listas, status)
    listas_para_ler = [lista_filtrada] if lista_filtrada else listas

    tarefas: list[dict[str, str]] = []
    for lista in listas_para_ler:
        for card in lista.list_cards():
            tarefas.append(_card_para_dict(card, lista, board))

    return tarefas


def mover_tarefa(
    nome: str,
    novo_status: str,
    quadro: str | None = None,
) -> dict[str, Any]:
    """Move um card para a lista do novo status."""
    board = obter_quadro(quadro)
    listas = board.list_lists()
    lista_destino = obter_lista(listas, novo_status)

    if lista_destino is None:
        raise TrelloError(
            f"Informe o status de destino: {STATUS_VALIDOS}."
        )

    lista_origem, card = _localizar_card(board, nome)
    if lista_origem.id == lista_destino.id:
        return {
            "nome": card.name,
            "origem": lista_origem.name,
            "destino": lista_destino.name,
            "movido": False,
        }

    card.change_list(lista_destino.id)
    return {
        "nome": card.name,
        "origem": lista_origem.name,
        "destino": lista_destino.name,
        "movido": True,
    }


def remover_tarefa(nome: str, quadro: str | None = None) -> dict[str, str]:
    """Remove um card do quadro."""
    board = obter_quadro(quadro)
    lista, card = _localizar_card(board, nome)
    dados = {"nome": card.name, "status": lista.name, "quadro": board.name}
    card.delete()
    return dados
