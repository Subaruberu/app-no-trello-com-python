"""Configuração central do agente.

O `.env` é procurado na raiz do projeto e também dentro do pacote do agente,
porque o `adk web` pode ser executado a partir de pastas diferentes.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_AGENTE = Path(__file__).resolve().parent

# O primeiro arquivo encontrado tem prioridade; o segundo serve de fallback.
load_dotenv(RAIZ_PROJETO / ".env")
load_dotenv(PASTA_AGENTE / ".env")

VARIAVEIS_TRELLO = ("TRELLO_API_KEY", "TRELLO_API_SECRET", "TRELLO_TOKEN")


def fuso_horario() -> str:
    return os.getenv("TRELLO_TIMEZONE", "America/Sao_Paulo").strip() or "America/Sao_Paulo"


def quadro_padrao() -> str:
    return os.getenv("TRELLO_BOARD_NAME", "DIO").strip() or "DIO"


def modelo_gemini() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
