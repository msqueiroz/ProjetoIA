# A API do PI AF expõe objetos .NET dinâmicos sem tipagem Python completa.
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false
"""Chat de consulta atual ao PI/AF, estritamente somente leitura."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd
import streamlit as st

from adaptador_pi_af import (
    conectar_af,
    carregar_historico_atributo,
    listar_databases,
    obter_valor_atual_atributo,
)
from motor_estudo_processo import alinhar_series, calcular_correlacao


PALAVRAS_COMUNS = {
    "a", "ao", "aos", "como", "da", "das", "de", "do", "dos",
    "e", "em", "esta", "estao", "me", "mostre", "na", "nas", "no",
    "nos", "o", "os", "pi", "qual", "quanto", "agora", "atual", "valor",
}


def _normalizar(texto: Any) -> str:
    bruto = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acentos = "".join(letra for letra in bruto if not unicodedata.combining(letra))
    return re.sub(r"[^a-z0-9]+", " ", sem_acentos.lower()).strip()


@st.cache_data(ttl=300, show_spinner=False)
def _listar_databases_chat(servidor: str) -> list[str]:
    return list(listar_databases(servidor))


@st.cache_data(ttl=300, show_spinner=False)
def _catalogar_atributos(
    servidor: str,
    database: str,
    profundidade_maxima: int = 7,
    limite_atributos: int = 10000,
) -> list[dict[str, Any]]:
    """Cria um catálogo leve de nomes; não lê valores do processo."""

    sistema = conectar_af(servidor)
    banco = sistema.Databases[database]
    if banco is None:
        raise ValueError(f"Database '{database}' não encontrada.")

    catalogo: list[dict[str, Any]] = []

    def visitar(elementos: Any, caminho: list[str], profundidade: int) -> None:
        if profundidade > profundidade_maxima or len(catalogo) >= limite_atributos:
            return
        for elemento in elementos:
            novo_caminho = [*caminho, str(elemento.Name)]
            for atributo in elemento.Attributes:
                try:
                    unidade = str(atributo.DefaultUOM or "").strip()
                except Exception:
                    unidade = ""
                catalogo.append({
                    "caminho": novo_caminho,
                    "elemento": str(elemento.Name),
                    "atributo": str(atributo.Name),
                    "unidade": unidade,
                })
                if len(catalogo) >= limite_atributos:
                    return
            visitar(elemento.Elements, novo_caminho, profundidade + 1)

    visitar(banco.Elements, [], 1)
    return catalogo


def _localizar(pergunta: str, catalogo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pergunta_normalizada = _normalizar(pergunta)
    termos = {
        termo for termo in pergunta_normalizada.split()
        if termo not in PALAVRAS_COMUNS and len(termo) >= 1
    }
    candidatos: list[dict[str, Any]] = []

    for item in catalogo:
        atributo = _normalizar(item["atributo"])
        caminho = _normalizar(" ".join(item["caminho"]))
        termos_atributo = set(atributo.split())
        termos_caminho = set(caminho.split())
        acertos_atributo = termos & termos_atributo
        acertos_caminho = termos & termos_caminho

        if not acertos_atributo:
            continue

        pontuacao = 6 * len(acertos_atributo) + 3 * len(acertos_caminho)
        if atributo and atributo in pergunta_normalizada:
            pontuacao += 8
        if _normalizar(item["elemento"]) in pergunta_normalizada:
            pontuacao += 6

        candidato = dict(item)
        candidato["pontuacao"] = pontuacao
        candidatos.append(candidato)

    return sorted(
        candidatos,
        key=lambda item: (
            -int(item["pontuacao"]),
            len(item["caminho"]),
            str(item["atributo"]),
        ),
    )


def _responder_pergunta(servidor: str, database: str, pergunta: str) -> str:
    catalogo = _catalogar_atributos(servidor, database)
    candidatos = _localizar(pergunta, catalogo)

    if not candidatos:
        return (
            "Não encontrei com segurança o atributo citado. Informe o nome do "
            "equipamento/local e a grandeza, por exemplo: **Como está a vazão do TA-2?**"
        )

    melhor = candidatos[0]
    empatados = [
        item for item in candidatos
        if item["pontuacao"] == melhor["pontuacao"]
    ]
    caminhos_distintos = {" / ".join(item["caminho"]) for item in empatados}
    if len(caminhos_distintos) > 1:
        opcoes = "\n".join(
            f"- {' / '.join(item['caminho'])} — {item['atributo']}"
            for item in empatados[:5]
        )
        return (
            "Encontrei mais de um ponto compatível. Inclua o local completo na pergunta:\n\n"
            + opcoes
        )

    leitura = obter_valor_atual_atributo(
        servidor=servidor,
        database=database,
        caminho_elementos=melhor["caminho"],
        nome_atributo=melhor["atributo"],
    )
    unidade = f" {melhor['unidade']}" if melhor.get("unidade") else ""
    caminho_texto = " / ".join(melhor["caminho"])

    return (
        f"O valor atual de **{melhor['atributo']}** em **{caminho_texto}** é "
        f"**{leitura['valor']}{unidade}**.\n\n"
        f"**Horário do dado:** {leitura['timestamp']}  \n"
        f"**Fonte:** PI System `{servidor}` — database `{database}`  \n"
        "**Modo:** consulta direta, somente leitura."
    )


def _periodo_historico_horas(pergunta: str) -> int:
    """Extrai um período simples da pergunta; usa 24 horas como padrão."""

    texto = _normalizar(pergunta)
    correspondencia = re.search(r"(\d+)\s*(hora|horas|h)\b", texto)
    if correspondencia:
        return max(1, min(int(correspondencia.group(1)), 24 * 31))

    correspondencia = re.search(r"(\d+)\s*(dia|dias|d)\b", texto)
    if correspondencia:
        return max(1, min(int(correspondencia.group(1)) * 24, 24 * 31))

    return 24


def _solicitou_grafico(pergunta: str) -> bool:
    texto = _normalizar(pergunta)
    return any(termo in texto.split() for termo in ("grafico", "plote", "plotar", "tendencia", "historico"))


def _solicitou_relacao(pergunta: str) -> bool:
    """Identifica pedidos explícitos de comparação entre duas variáveis."""

    texto = _normalizar(pergunta)
    termos = set(texto.split())
    return bool(
        termos & {"compare", "comparar", "correlacao", "relacao", "versus", "vs"}
        or re.search(r"\b[a-z0-9]+\s+x\s+[a-z0-9]+\b", texto)
    )


def _historico_numerico(
    servidor: str,
    database: str,
    candidato: dict[str, Any],
    horas: int,
) -> pd.DataFrame:
    dados = carregar_historico_atributo(
        servidor=servidor,
        database=database,
        caminho_elementos=candidato["caminho"],
        nome_atributo=candidato["atributo"],
        inicio=f"*-{horas}h",
        fim="*",
    ).copy()
    if not dados.empty:
        dados["valor"] = pd.to_numeric(
            dados["valor"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )
        dados = dados.dropna(subset=["data_hora", "valor"]).sort_values("data_hora")
    return dados


def _responder_relacao(servidor: str, database: str, pergunta: str) -> dict[str, Any]:
    """Compara duas séries alinhadas no tempo e prepara os três gráficos."""

    catalogo = _catalogar_atributos(servidor, database)
    candidatos = _localizar(pergunta, catalogo)
    if len(candidatos) < 2:
        return {
            "content": (
                "Não consegui identificar duas variáveis. Use, por exemplo: "
                "**Compare vazão x corrente do TA-2 nas últimas 24 horas.**"
            )
        }

    primeiro = candidatos[0]
    nome_primeiro = _normalizar(primeiro["atributo"])
    restantes = [item for item in candidatos if _normalizar(item["atributo"]) != nome_primeiro]
    if not restantes:
        return {"content": "Encontrei somente uma variável distinta para a comparação."}

    mesmo_caminho = [item for item in restantes if item["caminho"] == primeiro["caminho"]]
    segundo = mesmo_caminho[0] if mesmo_caminho else restantes[0]
    horas = _periodo_historico_horas(pergunta)
    serie_a = _historico_numerico(servidor, database, primeiro, horas)
    serie_b = _historico_numerico(servidor, database, segundo, horas)
    if serie_a.empty or serie_b.empty:
        return {"content": "Uma das duas variáveis não possui registros numéricos no período solicitado."}

    nome_a = str(primeiro["atributo"])
    nome_b = str(segundo["atributo"])
    alinhado = alinhar_series(
        serie_a,
        serie_b,
        nome_a=nome_a,
        nome_b=nome_b,
        tolerancia="30min",
    )
    resultado = calcular_correlacao(alinhado, nome_a=nome_a, nome_b=nome_b)
    if alinhado.empty:
        return {"content": "As séries existem, mas não produziram pares alinhados dentro da tolerância de 30 minutos."}

    unidade_a = str(primeiro.get("unidade") or "").strip()
    unidade_b = str(segundo.get("unidade") or "").strip()
    rotulo_a = nome_a + (f" ({unidade_a})" if unidade_a else "")
    rotulo_b = nome_b + (f" ({unidade_b})" if unidade_b else "")
    correlacao = resultado.get("correlacao")
    texto_correlacao = "não calculável" if correlacao is None else f"{float(correlacao):.3f}"
    periodo_texto = f"{horas // 24} dia(s)" if horas % 24 == 0 and horas >= 24 else f"{horas} hora(s)"

    return {
        "content": (
            f"Comparação entre **{nome_a}** e **{nome_b}** nas últimas **{periodo_texto}**. "
            f"O alinhamento temporal produziu **{resultado.get('pontos_validos', len(alinhado))} pares válidos**.\n\n"
            f"**Correlação:** {texto_correlacao} — {resultado.get('classificacao', 'não classificada')} — "
            f"direção {str(resultado.get('direcao', '-')).lower()}.  \n"
            "A correlação representa associação estatística e **não comprova causalidade**.  \n"
            f"**Fonte:** PI System `{servidor}` — database `{database}` — somente leitura."
        ),
        "relacao": {
            "serie_a": serie_a[["data_hora", "valor"]].to_dict(orient="records"),
            "serie_b": serie_b[["data_hora", "valor"]].to_dict(orient="records"),
            "dispersao": alinhado[[nome_a, nome_b]].to_dict(orient="records"),
            "nome_a": nome_a,
            "nome_b": nome_b,
            "rotulo_a": rotulo_a,
            "rotulo_b": rotulo_b,
        },
    }


def _responder_grafico(servidor: str, database: str, pergunta: str) -> dict[str, Any]:
    """Consulta o histórico do melhor atributo e prepara o gráfico."""

    catalogo = _catalogar_atributos(servidor, database)
    candidatos = _localizar(pergunta, catalogo)
    if not candidatos:
        return {
            "content": (
                "Não encontrei o atributo para o gráfico. Informe também o local, "
                "por exemplo: **Plote a vazão do TA-2 nas últimas 24 horas.**"
            )
        }

    melhor = candidatos[0]
    empatados = [item for item in candidatos if item["pontuacao"] == melhor["pontuacao"]]
    caminhos_distintos = {" / ".join(item["caminho"]) for item in empatados}
    if len(caminhos_distintos) > 1:
        opcoes = "\n".join(
            f"- {' / '.join(item['caminho'])} — {item['atributo']}"
            for item in empatados[:5]
        )
        return {"content": "Encontrei mais de um ponto. Especifique o local:\n\n" + opcoes}

    horas = _periodo_historico_horas(pergunta)
    historico = _historico_numerico(servidor, database, melhor, horas)
    if historico.empty:
        return {"content": "O PI não retornou registros para o período solicitado."}

    dados = historico.copy()
    if dados.empty:
        return {"content": "Os registros encontrados não possuem valores numéricos válidos para o gráfico."}

    unidade = str(melhor.get("unidade") or "").strip()
    rotulo = melhor["atributo"] + (f" ({unidade})" if unidade else "")
    caminho_texto = " / ".join(melhor["caminho"])
    periodo_texto = f"{horas // 24} dia(s)" if horas % 24 == 0 and horas >= 24 else f"{horas} hora(s)"

    return {
        "content": (
            f"Acompanhamento de **{melhor['atributo']}** em **{caminho_texto}**, "
            f"considerando as últimas **{periodo_texto}**. Foram recuperados "
            f"**{len(dados)} registros válidos** do PI.\n\n"
            f"**Fonte:** PI System `{servidor}` — database `{database}`  \n"
            "**Modo:** histórico, somente leitura."
        ),
        "grafico": dados[["data_hora", "valor"]].to_dict(orient="records"),
        "rotulo_y": rotulo,
    }


def renderizar_chat_maria() -> None:
    """Renderiza uma experiência curta de pergunta e resposta sobre o PI."""

    st.subheader("💬 Pergunte à MAR.IA")
    st.caption(
        "Consulte valores atuais do PI em linguagem natural. A MAR.IA apenas lê; "
        "nenhum comando ou ajuste é enviado ao processo."
    )

    with st.expander("Fonte da consulta", expanded=False):
        servidor = st.text_input("Servidor PI/AF", value="CE-SRV11", key="chat_maria_servidor")
        try:
            databases = _listar_databases_chat(servidor) if servidor.strip() else []
        except Exception as erro:
            databases = []
            st.error(f"Não foi possível acessar o servidor PI/AF: {erro}")
        database = st.selectbox(
            "Database AF",
            options=databases,
            key="chat_maria_database",
            disabled=not databases,
        ) if databases else ""

    historico = st.session_state.setdefault("chat_maria_historico", [])
    if not historico:
        historico.append({
            "role": "assistant",
            "content": (
                "Olá! Pergunte sobre um valor atual do PI. Exemplo: "
                "**Como está a vazão do TA-2?**"
            ),
        })

    for mensagem in historico:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])
            if mensagem.get("grafico"):
                dados_grafico = pd.DataFrame(mensagem["grafico"])
                dados_grafico["data_hora"] = pd.to_datetime(
                    dados_grafico["data_hora"], errors="coerce"
                )
                st.line_chart(
                    dados_grafico,
                    x="data_hora",
                    y="valor",
                    y_label=mensagem.get("rotulo_y", "Valor"),
                    x_label="Data e hora",
                    width="stretch",
                )
            if mensagem.get("relacao"):
                relacao = mensagem["relacao"]
                st.markdown(f"##### Tendência — {relacao['nome_a']}")
                serie_a = pd.DataFrame(relacao["serie_a"])
                serie_a["data_hora"] = pd.to_datetime(serie_a["data_hora"], errors="coerce")
                st.line_chart(
                    serie_a, x="data_hora", y="valor",
                    x_label="Data e hora", y_label=relacao["rotulo_a"], width="stretch",
                )
                st.markdown(f"##### Tendência — {relacao['nome_b']}")
                serie_b = pd.DataFrame(relacao["serie_b"])
                serie_b["data_hora"] = pd.to_datetime(serie_b["data_hora"], errors="coerce")
                st.line_chart(
                    serie_b, x="data_hora", y="valor",
                    x_label="Data e hora", y_label=relacao["rotulo_b"], width="stretch",
                )
                st.markdown(f"##### Dispersão — {relacao['nome_a']} × {relacao['nome_b']}")
                dispersao = pd.DataFrame(relacao["dispersao"])
                st.scatter_chart(
                    dispersao,
                    x=relacao["nome_a"],
                    y=relacao["nome_b"],
                    x_label=relacao["rotulo_a"],
                    y_label=relacao["rotulo_b"],
                    width="stretch",
                )

    pergunta = st.chat_input(
        "Pergunte algo sobre o PI...",
        disabled=not bool(database),
        key="chat_maria_pergunta",
    )
    if pergunta:
        historico.append({"role": "user", "content": pergunta})
        try:
            with st.spinner("Consultando o PI System..."):
                if _solicitou_relacao(pergunta):
                    resposta = _responder_relacao(servidor, database, pergunta)
                elif _solicitou_grafico(pergunta):
                    resposta = _responder_grafico(servidor, database, pergunta)
                else:
                    resposta = {"content": _responder_pergunta(servidor, database, pergunta)}
        except Exception as erro:
            resposta = {"content": f"Não foi possível concluir a consulta ao PI: `{erro}`"}
        historico.append({"role": "assistant", **resposta})
        st.rerun()
