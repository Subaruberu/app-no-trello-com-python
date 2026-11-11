"""Testes das ferramentas do agente (camada de conversa)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from agenttaskmanager import agent, trello_service


def test_get_temporal_context_informa_data_de_hoje():
    fuso = agent.fuso_horario()
    hoje = datetime.now(ZoneInfo(fuso)).strftime("%Y-%m-%d")
    texto = agent.get_temporal_context()
    assert hoje in texto
    assert "Hoje é" in texto


def test_adicionar_tarefa_formata_sucesso(monkeypatch):
    monkeypatch.setattr(
        agent.trello,
        "criar_tarefa",
        lambda **kwargs: {
            "id": "abc",
            "nome": kwargs["nome"],
            "descricao": kwargs["descricao"],
            "vencimento": "11/11/2026",
            "status": "A Fazer",
            "quadro": "DIO",
        },
    )

    resposta = agent.adicionar_tarefa("Enviar relatório", "Mensal", "2026-11-11")

    assert resposta.startswith("✅")
    assert "Enviar relatório" in resposta
    assert "A Fazer" in resposta


def test_adicionar_tarefa_mostra_erro_de_negocio(monkeypatch):
    def falha(**kwargs):
        raise trello_service.TrelloError("Credenciais ausentes")

    monkeypatch.setattr(agent.trello, "criar_tarefa", falha)

    resposta = agent.adicionar_tarefa("Qualquer")

    assert resposta == "❌ Credenciais ausentes"


def test_adicionar_tarefa_nao_quebra_com_erro_inesperado(monkeypatch):
    def falha(**kwargs):
        raise RuntimeError("rede caiu")

    monkeypatch.setattr(agent.trello, "criar_tarefa", falha)

    resposta = agent.adicionar_tarefa("Qualquer")

    assert resposta.startswith("❌ Erro inesperado")
    assert "rede caiu" in resposta


def test_listar_tarefas_formata_itens(monkeypatch):
    monkeypatch.setattr(
        agent.trello,
        "listar_tarefas",
        lambda **kwargs: [
            {
                "id": "1",
                "nome": "Comprar café",
                "descricao": "Pacote de 500g",
                "vencimento": "11/11/2026",
                "status": "A Fazer",
                "quadro": "DIO",
            }
        ],
    )

    resposta = agent.listar_tarefas("a fazer")

    assert "1 tarefa(s)" in resposta
    assert "[A Fazer] Comprar café" in resposta
    assert "Pacote de 500g" in resposta


def test_listar_tarefas_vazio(monkeypatch):
    monkeypatch.setattr(agent.trello, "listar_tarefas", lambda **kwargs: [])

    resposta = agent.listar_tarefas("concluido")

    assert "Nenhuma tarefa encontrada" in resposta


def test_mudar_status_formata_movimentacao(monkeypatch):
    monkeypatch.setattr(
        agent.trello,
        "mover_tarefa",
        lambda **kwargs: {
            "nome": "Revisar contrato",
            "origem": "Em andamento",
            "destino": "Concluído",
            "movido": True,
        },
    )

    resposta = agent.mudar_status_tarefa("Revisar contrato", "concluido")

    assert resposta.startswith("✅")
    assert "Em andamento → Concluído" in resposta


def test_mudar_status_quando_ja_esta_na_lista(monkeypatch):
    monkeypatch.setattr(
        agent.trello,
        "mover_tarefa",
        lambda **kwargs: {
            "nome": "Revisar contrato",
            "origem": "Concluído",
            "destino": "Concluído",
            "movido": False,
        },
    )

    resposta = agent.mudar_status_tarefa("Revisar contrato", "concluido")

    assert "já está" in resposta


def test_remover_tarefa_formata_sucesso(monkeypatch):
    monkeypatch.setattr(
        agent.trello,
        "remover_tarefa",
        lambda **kwargs: {"nome": "Tarefa velha", "status": "A Fazer", "quadro": "DIO"},
    )

    resposta = agent.remover_tarefa("Tarefa velha")

    assert resposta.startswith("🗑️")
    assert "Tarefa velha" in resposta


def test_listar_quadros_formata_nomes(monkeypatch):
    monkeypatch.setattr(agent.trello, "listar_quadros", lambda: ["DIO", "Pessoal"])
    resposta = agent.listar_quadros()
    assert "DIO" in resposta and "Pessoal" in resposta
