"""Testes das ferramentas sem chamar o Trello de verdade.

Um cliente falso imita as partes da py-trello que o agente usa. Assim é
possível validar criação, listagem, movimentação e remoção de cards sem
gastar a cota da API nem mexer no quadro real.
"""

from __future__ import annotations

import pytest

from agenttaskmanager import trello_service
from agenttaskmanager.utils import formatar_data_hora, normalizar, parse_due_date


class FakeCard:
    def __init__(self, card_id: str, name: str, desc: str = "", due=None):
        self.id = card_id
        self.name = name
        self.desc = desc
        self.due = due
        self.list_id = ""
        self.deleted = False

    def change_list(self, list_id: str) -> None:
        self.list_id = list_id

    def delete(self) -> None:
        self.deleted = True


class FakeList:
    def __init__(self, list_id: str, name: str):
        self.id = list_id
        self.name = name
        self.cards: list[FakeCard] = []

    def list_cards(self):
        return list(self.cards)

    def add_card(self, name, desc=None, due=None):
        card = FakeCard(f"card-{len(self.cards) + 1}", name, desc or "", due)
        card.list_id = self.id
        self.cards.append(card)
        return card


class FakeBoard:
    def __init__(self, name: str, lists: list[FakeList]):
        self.name = name
        self.lists = lists

    def list_lists(self):
        return list(self.lists)


class FakeClient:
    def __init__(self, boards: list[FakeBoard]):
        self.boards = boards

    def list_boards(self):
        return list(self.boards)


@pytest.fixture
def quadro() -> FakeBoard:
    return FakeBoard(
        "DIO",
        [
            FakeList("lista-a-fazer", "A Fazer"),
            FakeList("lista-andamento", "Em andamento"),
            FakeList("lista-concluido", "Concluído"),
        ],
    )


@pytest.fixture
def trello_falso(monkeypatch, quadro):
    cliente = FakeClient([quadro])
    monkeypatch.setattr(trello_service, "get_client", lambda: cliente)
    return cliente


# ---------------------------------------------------------------------------
# Funções puras
# ---------------------------------------------------------------------------

def test_normalizar_remove_acento_e_espacos():
    assert normalizar("  Concluído  ") == "concluido"
    assert normalizar("EM   ANDAMENTO") == "em andamento"
    assert normalizar("A Fazer") == "a fazer"


def test_parse_due_date_usa_fim_do_dia_com_fuso():
    assert parse_due_date("2026-11-11") == "2026-11-11T23:59:00-03:00"
    assert parse_due_date("11/11/2026") == "2026-11-11T23:59:00-03:00"


def test_parse_due_date_preserva_horario_informado():
    assert parse_due_date("2026-11-11T09:30:00-03:00") == "2026-11-11T09:30:00-03:00"


def test_parse_due_date_invalida():
    with pytest.raises(ValueError, match="Data inválida"):
        parse_due_date("11 de novembro")


def test_formatar_data_utc_volta_para_fuso_local():
    # 23:59 de 11/11 em Brasília = 02:59 de 12/11 em UTC.
    assert formatar_data_hora("2026-11-12T02:59:00.000Z") == "11/11/2026"


def test_formatar_data_vazia():
    assert formatar_data_hora(None) == "sem data"


# ---------------------------------------------------------------------------
# Criação
# ---------------------------------------------------------------------------

def test_criar_tarefa_na_lista_a_fazer(trello_falso, quadro):
    tarefa = trello_service.criar_tarefa(
        "Enviar relatório",
        "Relatório mensal de vendas",
        "2026-11-11",
        "DIO",
    )

    assert tarefa["status"] == "A Fazer"
    assert tarefa["vencimento"] == "11/11/2026"
    assert tarefa["quadro"] == "DIO"
    assert len(quadro.lists[0].cards) == 1
    assert quadro.lists[0].cards[0].due == "2026-11-11T23:59:00-03:00"


def test_criar_tarefa_sem_data(trello_falso):
    tarefa = trello_service.criar_tarefa("Ler artigo", quadro="DIO")
    assert tarefa["vencimento"] == "sem data"


def test_criar_tarefa_sem_nome_falha(trello_falso):
    with pytest.raises(trello_service.TrelloError, match="nome da tarefa"):
        trello_service.criar_tarefa("   ", quadro="DIO")


# ---------------------------------------------------------------------------
# Listagem e filtros
# ---------------------------------------------------------------------------

def test_listar_tarefas_todas(trello_falso, quadro):
    trello_service.criar_tarefa("Tarefa 1", quadro="DIO")
    trello_service.criar_tarefa("Tarefa 2", quadro="DIO")
    quadro.lists[1].cards.append(FakeCard("c3", "Tarefa 3", due=None))

    tarefas = trello_service.listar_tarefas("todas", "DIO")

    assert len(tarefas) == 3
    assert {tarefa["status"] for tarefa in tarefas} == {"A Fazer", "Em andamento"}


def test_listar_com_status_acentuado(trello_falso, quadro):
    quadro.lists[2].cards.append(FakeCard("c1", "Tarefa concluída"))

    tarefas = trello_service.listar_tarefas("concluída", "DIO")

    assert len(tarefas) == 1
    assert tarefas[0]["status"] == "Concluído"


def test_listar_com_status_invalido(trello_falso):
    with pytest.raises(trello_service.TrelloError, match="não reconhecido"):
        trello_service.listar_tarefas("atrasada", "DIO")


# ---------------------------------------------------------------------------
# Movimentação
# ---------------------------------------------------------------------------

def test_mover_tarefa_aceita_acento(trello_falso, quadro):
    trello_service.criar_tarefa("Revisar contrato", quadro="DIO")

    resultado = trello_service.mover_tarefa("Revisar contrato", "Concluído", "DIO")

    assert resultado["movido"] is True
    assert resultado["origem"] == "A Fazer"
    assert resultado["destino"] == "Concluído"
    assert quadro.lists[0].cards[0].list_id == "lista-concluido"


def test_mover_tarefa_para_o_mesmo_status(trello_falso):
    trello_service.criar_tarefa("Revisar contrato", quadro="DIO")

    resultado = trello_service.mover_tarefa("Revisar contrato", "a fazer", "DIO")

    assert resultado["movido"] is False


def test_mover_tarefa_inexistente(trello_falso):
    with pytest.raises(trello_service.TrelloError, match="não encontrada"):
        trello_service.mover_tarefa("Não existe", "concluido", "DIO")


# ---------------------------------------------------------------------------
# Remoção
# ---------------------------------------------------------------------------

def test_remover_tarefa(trello_falso, quadro):
    trello_service.criar_tarefa("Tarefa descartável", quadro="DIO")

    resultado = trello_service.remover_tarefa("Tarefa descartável", "DIO")

    assert resultado["nome"] == "Tarefa descartável"
    assert quadro.lists[0].cards[0].deleted is True


# ---------------------------------------------------------------------------
# Quadros e nomes de listas em inglês
# ---------------------------------------------------------------------------

def test_quadro_nao_encontrado_lista_disponiveis(trello_falso):
    with pytest.raises(trello_service.TrelloError, match="DIO"):
        trello_service.obter_quadro("Outro quadro")


def test_status_funciona_com_listas_em_ingles(monkeypatch):
    board = FakeBoard(
        "DIO",
        [
            FakeList("l1", "To Do"),
            FakeList("l2", "Doing"),
            FakeList("l3", "Done"),
        ],
    )
    monkeypatch.setattr(
        trello_service,
        "get_client",
        lambda: FakeClient([board]),
    )

    trello_service.criar_tarefa("Tarefa", quadro="DIO")
    resultado = trello_service.mover_tarefa("Tarefa", "concluido", "DIO")

    assert resultado["destino"] == "Done"
    assert board.lists[0].cards[0].list_id == "l3"
