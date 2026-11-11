# Guia rápido: Trello + Python

Este guia resume o que você precisa fazer no Trello para rodar o agente.
Ele foi adaptado do material do desafio da DIO.

## 1. Crie o quadro e as listas

No Trello, crie um quadro (o padrão do projeto chama-se **DIO**) com três
listas, exatamente com estes nomes:

```text
A fazer
Em andamento
Concluído
```

Você também pode deixar o script fazer isso:

```bash
python scripts/criar_quadro.py --nome "DIO"
```

O script é idempotente: se o quadro ou as listas já existirem, nada é
duplicado.

## 2. Registre um aplicativo (Power-Up)

1. Acesse <https://trello.com/power-ups/admin/>.
2. Clique em **New**.
3. Preencha:
   - **Nome do aplicativo:** `AgenteTarefas` (ou outro nome)
   - **Workspace:** o workspace onde o quadro está
   - **E-mail** e **contato de suporte**
   - **Autor:** seu nome
   - **URL do conector iframe:** pode ficar em branco para uso somente da API
4. Clique em **Create**.

## 3. Copie a API Key e o Secret

Na página do aplicativo, abra a aba **API Key**. Você verá:

- **Key** (chave pública do aplicativo)
- **Secret** (segredo)

Guarde os dois. Eles serão `TRELLO_API_KEY` e `TRELLO_API_SECRET`.

## 4. Gere o token do usuário

Monte a URL abaixo trocando `SUA_API_KEY` pela sua Key:

```text
https://trello.com/1/authorize?expiration=never&name=AgenteTarefas&scope=read,write&response_type=token&key=SUA_API_KEY
```

Parâmetros:

| Parâmetro | Valor | Para que serve |
|---|---|---|
| `expiration` | `never` | O token não expira |
| `name` | `AgenteTarefas` | Nome que aparece na autorização |
| `scope` | `read,write` | Ler e escrever nos quadros |
| `response_type` | `token` | Devolve o token na tela |
| `key` | sua API Key | Identifica o aplicativo |

Abra a URL, clique em **Allow** e copie o token exibido. Ele será
`TRELLO_TOKEN`.

> Se você perder o token, gere outro pela mesma URL. O token antigo pode ser
> revogado nas configurações da conta.

## 5. Preencha o `.env`

```powershell
Copy-Item .env.exemplo .env
```

```dotenv
TRELLO_API_KEY=sua-key
TRELLO_API_SECRET=seu-secret
TRELLO_TOKEN=seu-token
TRELLO_BOARD_NAME=DIO
TRELLO_TIMEZONE=America/Sao_Paulo
```

## 6. Teste a conexão

```bash
python scripts/criar_quadro.py
```

Saídas esperadas:

```text
[INFO] Quadro ja existente: DIO
   - lista ja existe: A fazer
   - lista ja existe: Em andamento
   - lista ja existe: Concluído
```

Se aparecer `Credenciais do Trello ausentes`, o `.env` não foi encontrado ou
está incompleto. Confira se o arquivo está na raiz do projeto.

## Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `401 Unauthorized` | Key, secret ou token inválidos | Gere o token de novo e confira o `.env` |
| `Quadro 'DIO' não encontrado` | Nome diferente ou token sem acesso | Rode `listar_quadros` no agente ou ajuste `TRELLO_BOARD_NAME` |
| `O status 'concluido' foi reconhecido, mas não há uma lista correspondente` | A lista tem outro nome | Renomeie a lista para **Concluído** ou use o nome que existe |
| Data um dia antes no Trello | Fuso horário | Confira `TRELLO_TIMEZONE` e mantenha o formato ISO com offset |
| `429 Too Many Requests` | Limite da API do Trello | Aguarde alguns minutos |

## Segurança

- Nunca commite o `.env`.
- Não cole o token em prints, issues ou mensagens.
- Use um quadro separado para testes: o agente cria e apaga cards de verdade.
- Se o token vazar, revogue-o imediatamente e gere outro.
