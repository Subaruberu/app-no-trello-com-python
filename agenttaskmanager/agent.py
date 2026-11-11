"""Agente de organização de tarefas no Trello.

Cada função decorada com uma docstring clara vira uma ferramenta do agente.
As ferramentas só formatam a resposta; a conversa com o Trello fica em
`trello_service.py`.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent

from . import trello_service as trello
from .config import fuso_horario, modelo_gemini

DIAS_DA_SEMANA = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


def get_temporal_context() -> str:
    """Retorna a data e a hora atuais no fuso configurado.

    Use esta ferramenta sempre que precisar saber que dia é hoje. Nunca
    invente a data: o agente deve copiar o valor retornado aqui ao criar
    tarefas ou ao cumprimentar o usuário.
    """
    fuso = fuso_horario()
    agora = datetime.now(ZoneInfo(fuso))
    dia_da_semana = DIAS_DA_SEMANA[agora.weekday()]
    return (
        f"Hoje é {agora:%Y-%m-%d} ({dia_da_semana}), "
        f"{agora:%H:%M}, no fuso {fuso}."
    )


def listar_quadros() -> str:
    """Lista os quadros do Trello disponíveis para a conta configurada.

    Use quando o usuário tiver mais de um quadro ou quando não estiver claro
    em qual quadro a tarefa deve ser criada.
    """
    try:
        nomes = trello.listar_quadros()
        if not nomes:
            return "Nenhum quadro encontrado para esta conta do Trello."
        return "Quadros disponíveis: " + ", ".join(nomes) + "."
    except trello.TrelloError as erro:
        return f"❌ {erro}"
    except Exception as erro:  # noqa: BLE001 - a mensagem volta para o usuário
        return f"❌ Erro inesperado ao listar os quadros: {erro}"


def adicionar_tarefa(
    nome_da_task: str,
    descricao_da_task: str = "",
    due_date: str = "",
    quadro: str = "",
) -> str:
    """Cria um card na lista "A fazer" do quadro do Trello.

    Args:
        nome_da_task: Nome curto e claro da tarefa (ex.: "Enviar relatório").
        descricao_da_task: Detalhes da tarefa. Se o usuário não informar,
            resuma em uma frase o que ele contou.
        due_date: Data de vencimento no formato AAAA-MM-DD (ex.: "2026-11-11").
            Use a data de hoje retornada por get_temporal_context quando o
            usuário não disser outra data. Também aceita DD/MM/AAAA.
        quadro: Nome do quadro. Deixe vazio para usar o padrão do .env
            (TRELLO_BOARD_NAME).
    """
    try:
        tarefa = trello.criar_tarefa(
            nome=nome_da_task,
            descricao=descricao_da_task,
            due_date=due_date or None,
            quadro=quadro or None,
        )
        return (
            f"✅ Tarefa criada no quadro '{tarefa['quadro']}', lista "
            f"'{tarefa['status']}': {tarefa['nome']} "
            f"(vencimento: {tarefa['vencimento']}; id: {tarefa['id']})."
        )
    except trello.TrelloError as erro:
        return f"❌ {erro}"
    except Exception as erro:  # noqa: BLE001
        return f"❌ Erro inesperado ao criar a tarefa: {erro}"


def listar_tarefas(status: str = "todas", quadro: str = "") -> str:
    """Lista as tarefas do quadro, todas ou filtradas por status.

    Args:
        status: "todas" para listar tudo, ou um status aceito:
            "a fazer", "em andamento" ou "concluido" (aceita acentos e
            variações como "concluída" e "done").
        quadro: Nome do quadro. Deixe vazio para usar o padrão do .env.
    """
    try:
        tarefas = trello.listar_tarefas(status=status, quadro=quadro or None)
    except trello.TrelloError as erro:
        return f"❌ {erro}"
    except Exception as erro:  # noqa: BLE001
        return f"❌ Erro inesperado ao listar as tarefas: {erro}"

    if not tarefas:
        return f"Nenhuma tarefa encontrada para o filtro '{status}'."

    linhas = [f"📋 {len(tarefas)} tarefa(s) — filtro: {status}"]
    for tarefa in tarefas:
        descricao = f" — {tarefa['descricao']}" if tarefa["descricao"] else ""
        linhas.append(
            f"- [{tarefa['status']}] {tarefa['nome']} "
            f"(vence: {tarefa['vencimento']}){descricao} [id: {tarefa['id']}]"
        )
    return "\n".join(linhas)


def mudar_status_tarefa(
    nome_da_task: str,
    novo_status: str,
    quadro: str = "",
) -> str:
    """Move um card para a lista de outro status no quadro.

    Use quando o usuário contar o que já fez, por exemplo: "terminei o
    relatório" ou "comecei a revisão".

    Args:
        nome_da_task: Nome da tarefa (card) que será movida.
        novo_status: Status de destino: "a fazer", "em andamento" ou
            "concluido". Aceita acentos e variações.
        quadro: Nome do quadro. Deixe vazio para usar o padrão do .env.
    """
    try:
        resultado = trello.mover_tarefa(
            nome=nome_da_task,
            novo_status=novo_status,
            quadro=quadro or None,
        )
    except trello.TrelloError as erro:
        return f"❌ {erro}"
    except Exception as erro:  # noqa: BLE001
        return f"❌ Erro inesperado ao mover a tarefa: {erro}"

    if not resultado["movido"]:
        return f"ℹ️ '{resultado['nome']}' já está na lista '{resultado['destino']}'."

    return (
        f"✅ '{resultado['nome']}': {resultado['origem']} → "
        f"{resultado['destino']}."
    )


def remover_tarefa(nome_da_task: str, quadro: str = "") -> str:
    """Remove definitivamente um card do quadro.

    Só use depois que o usuário confirmar explicitamente que quer remover
    a tarefa. A remoção não pode ser desfeita pelo agente.

    Args:
        nome_da_task: Nome da tarefa (card) que será removida.
        quadro: Nome do quadro. Deixe vazio para usar o padrão do .env.
    """
    try:
        removida = trello.remover_tarefa(
            nome=nome_da_task,
            quadro=quadro or None,
        )
    except trello.TrelloError as erro:
        return f"❌ {erro}"
    except Exception as erro:  # noqa: BLE001
        return f"❌ Erro inesperado ao remover a tarefa: {erro}"

    return (
        f"🗑️ Tarefa removida do quadro '{removida['quadro']}': "
        f"{removida['nome']} (estava em '{removida['status']}')."
    )


INSTRUCAO = """
Você é o TaskMaster, um agente que organiza as tarefas do dia em um quadro
do Trello. Você conversa em português do Brasil, de forma curta e amigável.

## Como começar a conversa
- Na primeira resposta da conversa (mesmo que o usuário só diga "oi"),
  chame a ferramenta get_temporal_context e cumprimente o usuário
  informando a data de hoje.
- Em seguida, pergunte quais são as tarefas do dia.
- Depois de cada tarefa informada, pergunte se há mais alguma, até o
  usuário dizer que não tem mais.

## Ferramentas disponíveis
1. get_temporal_context: retorna a data e a hora atuais. Use sempre que
   precisar da data de hoje. Nunca invente ou calcule a data de cabeça.
2. listar_quadros: lista os quadros do Trello. Use se houver dúvida sobre
   em qual quadro a tarefa entra.
3. adicionar_tarefa: cria um card na lista "A fazer" com nome, descrição
   e data de vencimento.
4. listar_tarefas: lista todas as tarefas ou apenas as de um status.
5. mudar_status_tarefa: move um card entre "A fazer", "Em andamento" e
   "Concluído". Use quando o usuário contar o que já fez.
6. remover_tarefa: apaga um card. Use somente após confirmação explícita
   do usuário.

## Regras importantes
- Sempre use a ferramenta adequada. Nunca diga que criou, listou, moveu ou
  removeu uma tarefa sem ter chamado a ferramenta e recebido sucesso.
- Ao criar uma tarefa, envie due_date no formato AAAA-MM-DD. Se o usuário
  não informar data, use a data de hoje retornada por get_temporal_context.
- Se o usuário não der descrição, crie uma descrição curta com base no que
  ele contou. Nunca deixe a descrição vazia.
- Antes de criar o card, confirme com o usuário o nome e a descrição da
  tarefa. Se ele já informou tudo com clareza, pode criar direto.
- Para mudar o status, use exatamente: "a fazer", "em andamento" ou
  "concluido". A ferramenta também entende acentos e variações.
- Se houver mais de um quadro, chame listar_quadros e pergunte em qual
  deles a tarefa deve ser criada. Sem dúvida, use o quadro padrão.
- Se uma ferramenta retornar erro, explique o problema ao usuário e sugira
  a correção. Nunca invente um resultado de sucesso.
- Ao final da organização, faça um resumo do que foi criado e pergunte se
  o usuário quer ver o quadro, listar as tarefas ou mover alguma.
"""

root_agent = Agent(
    model=modelo_gemini(),
    name="root_agent",
    description="Agente que organiza as tarefas do dia em um quadro do Trello.",
    instruction=INSTRUCAO,
    tools=[
        get_temporal_context,
        listar_quadros,
        adicionar_tarefa,
        listar_tarefas,
        mudar_status_tarefa,
        remover_tarefa,
    ],
)
