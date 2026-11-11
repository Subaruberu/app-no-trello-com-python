"""Funções auxiliares de texto e de data usadas pelas ferramentas.

Nada aqui conversa com o Trello: são funções puras, fáceis de testar.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, time
from zoneinfo import ZoneInfo

FUSO_PADRAO = "America/Sao_Paulo"
HORA_VENCIMENTO = time(23, 59)


def normalizar(texto: str | None) -> str:
    """Deixa o texto em minúsculas, sem acentos e sem espaços duplicados.

    Exemplos:
        "Concluído"  -> "concluido"
        "  EM   ANDAMENTO " -> "em andamento"
    """
    if not texto:
        return ""

    sem_acento = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", str(texto))
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def formatar_data_hora(
    valor: datetime | str | None,
    fuso: str = FUSO_PADRAO,
) -> str:
    """Formata a data de vencimento do Trello como dd/mm/aaaa.

    O Trello devolve a data em UTC (ex.: 2026-11-12T02:59:00.000Z para um
    vencimento às 23:59 de 11/11 em Brasília). Por isso convertemos para o
    fuso local antes de mostrar — senão a data aparece um dia à frente.
    """
    if not valor:
        return "sem data"

    if isinstance(valor, datetime):
        data_hora = valor
    else:
        texto = str(valor).strip()
        try:
            data_hora = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            return texto

    if data_hora.tzinfo is not None:
        data_hora = data_hora.astimezone(ZoneInfo(fuso))

    return data_hora.strftime("%d/%m/%Y")


def parse_due_date(valor: str | None, fuso: str = FUSO_PADRAO) -> str | None:
    """Converte a data recebida do usuário em ISO 8601 com fuso horário.

    Aceita:
        "2026-11-11"                 -> 2026-11-11T23:59:00-03:00
        "11/11/2026"                 -> 2026-11-11T23:59:00-03:00
        "2026-11-11T09:00:00-03:00"  -> mantém o horário informado

    Quando só a data é informada, usamos 23:59 no fuso local. Esse é o
    ajuste para o bug de "um dia a menos": se enviarmos meia-noite UTC, o
    Trello exibe 21h do dia anterior no horário de Brasília. Enviar o fim
    do dia com o offset correto mantém a data que o usuário escolheu.
    """
    if valor is None:
        return None

    texto = str(valor).strip()
    if not texto:
        return None

    tz = ZoneInfo(fuso)

    # ISO completo, com hora (ex.: 2026-11-11T09:00:00-03:00).
    try:
        data_hora = datetime.fromisoformat(texto)
    except ValueError:
        data_hora = None

    if data_hora is not None and ("T" in texto or data_hora.hour or data_hora.minute):
        if data_hora.tzinfo is None:
            data_hora = data_hora.replace(tzinfo=tz)
        return data_hora.isoformat()

    # Apenas a data, em formatos comuns no Brasil.
    data = None
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            data = datetime.strptime(texto, formato).date()
            break
        except ValueError:
            continue

    if data is None:
        raise ValueError(
            f"Data inválida: '{valor}'. Use o formato AAAA-MM-DD (ex.: 2026-11-11)."
        )

    vencimento = datetime.combine(data, HORA_VENCIMENTO, tzinfo=tz)
    return vencimento.isoformat()
