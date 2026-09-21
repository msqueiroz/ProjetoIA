"""Canal autenticado do Microsoft Teams para a MAR.IA."""

from __future__ import annotations

import asyncio
import os
import re

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from microsoft_teams.apps import App, FastAPIAdapter

from ui_chat_maria import responder_chat_maria


load_dotenv("teams.env")


def _validar_configuracao() -> None:
    obrigatorias = ("CLIENT_ID", "CLIENT_SECRET", "TENANT_ID")
    ausentes = [nome for nome in obrigatorias if not os.getenv(nome, "").strip()]
    if ausentes:
        raise RuntimeError(
            "Configuração do Teams incompleta: " + ", ".join(ausentes)
        )


api = FastAPI(title="MAR.IA para Microsoft Teams")
adapter = FastAPIAdapter(app=api)
teams_app = App(http_server_adapter=adapter)


def _limpar_pergunta(texto: str | None) -> str:
    sem_mencao = re.sub(r"<at>.*?</at>", "", str(texto or ""), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", sem_mencao).strip()


def _formatar_para_teams(resposta: dict) -> str:
    partes = [str(resposta.get("content", "")).strip()]
    contexto = list(resposta.get("contexto_operacional") or [])
    if contexto:
        partes.append("\n**Contexto operacional**")
        for item in contexto[:8]:
            partes.append(
                f"- **{item.get('Indicador', 'Indicador')}:** "
                f"{item.get('Valor atual', '')} — {item.get('Sinal', '')}"
            )
    if resposta.get("grafico") or resposta.get("relacao"):
        partes.append(
            "\nOs gráficos detalhados permanecem disponíveis na aplicação de engenharia."
        )
    return "\n".join(parte for parte in partes if parte)


@api.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "modo_pi": "somente leitura"}


@teams_app.on_message
async def receber_mensagem(ctx):
    pergunta = _limpar_pergunta(ctx.activity.text)
    if not pergunta:
        await ctx.send("Escreva uma pergunta sobre o PI, o processo ou os manuais.")
        return

    servidor = os.getenv("PI_AF_SERVER", "CE-SRV11").strip()
    database = os.getenv("PI_AF_DATABASE", "ETE").strip()
    try:
        resposta = await asyncio.to_thread(
            responder_chat_maria, servidor, database, pergunta
        )
        await ctx.send(_formatar_para_teams(resposta))
    except Exception as erro:
        await ctx.send(
            "Não foi possível concluir a consulta. "
            f"Detalhe técnico: `{str(erro).splitlines()[0]}`"
        )


async def main() -> None:
    _validar_configuracao()
    await teams_app.initialize()
    porta = int(os.getenv("PORT", "3978"))
    # O acesso externo deve ser feito por proxy/túnel autenticado aprovado pela TI.
    servidor = uvicorn.Server(
        uvicorn.Config(api, host="127.0.0.1", port=porta)
    )
    await servidor.serve()


if __name__ == "__main__":
    asyncio.run(main())
