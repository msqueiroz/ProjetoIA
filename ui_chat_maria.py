# A API do PI AF expõe objetos .NET dinâmicos sem tipagem Python completa.
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false
"""Chat de consulta atual ao PI/AF, estritamente somente leitura."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from adaptador_pi_af import (
    buscar_pi_points_por_nome,
    carregar_historico_pi_point,
    conectar_af,
    carregar_historico_atributo,
    listar_databases,
    obter_valor_atual_atributo,
    obter_valor_atual_pi_point,
)
from motor_estudo_processo import alinhar_series, calcular_correlacao
from adaptador_ia import (
    concluir_login_maria,
    consultar_ia,
    iniciar_login_maria,
    obter_token_maria_silencioso,
    verificar_maria,
    verificar_ollama,
)
from gerenciador_conhecimento import (
    buscar_base_documental,
    carregar_base_documental,
)
from unidades_engenharia import formatar_unidade_engenharia


PALAVRAS_COMUNS = {
    "a", "ao", "aos", "como", "da", "das", "de", "do", "dos",
    "e", "em", "esta", "estao", "me", "mostre", "na", "nas", "no",
    "nos", "o", "os", "pi", "qual", "quanto", "agora", "atual", "valor",
    "valores", "tag", "plote", "plotar", "grafico", "historico", "ultimas",
    "ultimos", "dia", "dias", "hora", "horas",
}

TERMOS_DOCUMENTAIS = {
    "manual", "manuais", "documentacao", "documentacoes", "documento",
    "documentos", "procedimento", "procedimentos", "processo",
    "funciona", "funcionamento", "operacao", "operar", "recomendacao",
    "recomendacoes", "melhoria", "melhorar", "criterio", "limite",
    "especificacao", "projeto", "equipamento", "porque", "causa",
}

TERMOS_CONTEXTO_OPERACIONAL = {
    "aerador", "aeradores", "contexto", "resumo", "situacao", "panorama",
    "visao", "geral",
}

CAMPOS_CONTEXTO_RAPIDO = (
    ("Aeradores", ("aerador",)),
    ("Vazão", ("vazao",)),
    ("Oxigênio dissolvido", ("oxigenio", "od ")),
    ("Recirculação", ("reciclo", "recirculacao")),
    ("Descarte", ("descarte",)),
    ("Idade do lodo", ("idade", "lodo")),
    ("Sólidos", ("sst", "solidos")),
)


def _normalizar(texto: Any) -> str:
    bruto = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acentos = "".join(letra for letra in bruto if not unicodedata.combining(letra))
    return re.sub(r"[^a-z0-9]+", " ", sem_acentos.lower()).strip()


@st.cache_data(ttl=300, show_spinner=False)
def _listar_databases_chat(servidor: str) -> list[str]:
    return list(listar_databases(servidor))


@st.cache_data(ttl=300, show_spinner=False)
def _carregar_documentos_chat(database: str) -> dict[str, Any]:
    """Carrega somente documentos identificáveis com a base selecionada."""

    base = carregar_base_documental("Documentos")
    if not base.get("trechos") and Path("Manual_Oper_EEF.pdf").exists():
        base = carregar_base_documental(".")
    identificador = _normalizar(database).replace(" ", "")
    trechos = [
        item for item in base.get("trechos", [])
        if identificador
        and (
            identificador in _normalizar(
                item.get("documento") or item.get("nome_arquivo") or ""
            ).replace(" ", "")
            or identificador in set(_normalizar(item.get("texto", "")).split())
        )
    ]
    documentos_incluidos = {
        str(item.get("documento") or item.get("nome_arquivo") or "")
        for item in trechos
    }
    documentos = [
        item for item in base.get("documentos_processados", [])
        if str(item.get("documento", "")) in documentos_incluidos
    ]
    return {
        **base,
        "trechos": trechos,
        "documentos_processados": documentos,
        "total_documentos": len(documentos),
        "total_trechos": len(trechos),
    }


def _buscar_documentacao_chat(database: str, pergunta: str) -> list[dict[str, Any]]:
    base = _carregar_documentos_chat(database)
    return list(buscar_base_documental(base, pergunta, limite=5))


def _solicitou_conhecimento(pergunta: str) -> bool:
    termos = set(_normalizar(pergunta).split())
    return bool(termos & TERMOS_DOCUMENTAIS)


def _solicitou_lista_documentos(pergunta: str) -> bool:
    termos = set(_normalizar(pergunta).split())
    return bool(
        termos & {"manual", "manuais", "documento", "documentos"}
        and termos & {
            "carregado", "carregados", "disponivel", "disponiveis", "quais"
        }
    )


def _responder_lista_documentos(database: str) -> dict[str, Any]:
    base = _carregar_documentos_chat(database)
    documentos = list(base.get("documentos_processados", []))
    if not documentos:
        return {
            "content": f"Nenhum manual associado à base **{database}** foi localizado."
        }
    linhas = []
    for item in documentos:
        nome = str(item.get("documento", "Documento sem nome"))
        trechos = item.get("total_trechos", 0)
        linhas.append(f"- **{nome}** — {trechos} trecho(s) pesquisáveis")
    return {
        "content": (
            f"### 📚 Documentos associados à base {database}\n\n"
            + "\n".join(linhas)
            + "\n\nEsses documentos são consultados em modo somente leitura."
        )
    }


def _referencias_documentais(trechos: list[dict[str, Any]]) -> str:
    referencias = []
    vistas = set()
    for trecho in trechos:
        documento = str(
            trecho.get("documento") or trecho.get("nome_arquivo") or "Documento técnico"
        )
        pagina = trecho.get("pagina")
        chave = (documento, pagina)
        if chave in vistas:
            continue
        vistas.add(chave)
        pagina_texto = f", pág. {pagina}" if pagina is not None else ""
        referencias.append(f"- **{documento}**{pagina_texto}")
    return "\n".join(referencias)


def _responder_documentacao(
    database: str,
    pergunta: str,
    provedor: str | None,
    modelo: str | None,
    token: str | None,
) -> dict[str, Any]:
    trechos = _buscar_documentacao_chat(database, pergunta)
    if not trechos:
        return {
            "content": (
                f"Não encontrei, nos manuais associados à base **{database}**, "
                "trechos suficientes para responder a essa pergunta. Isso pode "
                "representar uma lacuna documental ou exigir outros termos de busca."
            )
        }

    referencias = _referencias_documentais(trechos)
    if not provedor:
        return {
            "content": (
                "Encontrei referências relacionadas, mas nenhum provedor de IA está "
                "disponível para consolidar a resposta.\n\n"
                "### Referências encontradas\n" + referencias
            )
        }

    resultado = consultar_ia(
        contexto_ia={
            "modo_consulta_documental": True,
            "pergunta": pergunta,
            "base_operacional": database,
            "conhecimento_documental": trechos,
        },
        provedor=provedor,
        modelo=modelo,
        token=token,
    )
    if not resultado.get("ok"):
        return {
            "content": (
                "Não foi possível consolidar a resposta com IA: "
                f"{resultado.get('erro') or 'erro não informado'}.\n\n"
                "### Referências encontradas\n" + referencias
            )
        }
    return {
        "content": (
            str(resultado.get("resposta", "")).strip()
            + "\n\n### Referências consultadas\n"
            + referencias
        )
    }


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
                    "origem": "AF",
                    "pi_point": "",
                })
                if len(catalogo) >= limite_atributos:
                    return
            visitar(elemento.Elements, novo_caminho, profundidade + 1)

    visitar(banco.Elements, [], 1)
    return catalogo


@st.cache_data(ttl=300, show_spinner=False)
def _buscar_pi_points_chat(servidor: str, termo: str) -> list[dict[str, Any]]:
    return list(buscar_pi_points_por_nome(servidor, termo, limite=100))


def _catalogar_smt(servidor: str, pergunta: str) -> list[dict[str, Any]]:
    """Descobre no SMT/Data Archive tags mencionadas na pergunta."""

    # Identificadores como TUT-DS2, AI-ETF1-1 e OD-TA3-1 devem ser
    # pesquisados antes das palavras naturais da pergunta.
    identificadores = re.findall(
        r"(?<![A-Z0-9])(?:[A-Z0-9]+-)+[A-Z0-9]+(?![A-Z0-9])",
        str(pergunta or "").upper(),
    )
    termos_naturais = [
        termo for termo in _normalizar(pergunta).split()
        if termo not in PALAVRAS_COMUNS and len(termo) >= 2
    ]
    termos = []
    for termo in [*identificadores, *termos_naturais]:
        if termo not in termos:
            termos.append(termo)
        if len(termos) >= 6:
            break
    catalogo: list[dict[str, Any]] = []
    incluidas: set[str] = set()
    for termo in termos:
        for ponto in _buscar_pi_points_chat(servidor, termo):
            tag = str(ponto.get("pi_point", "")).strip()
            chave = tag.upper()
            if not tag or chave in incluidas:
                continue
            incluidas.add(chave)
            catalogo.append({
                "caminho": ["SMT / Data Archive"],
                "elemento": "SMT",
                "atributo": tag,
                "unidade": "",
                "origem": "SMT",
                "pi_point": tag,
            })
    return catalogo


def _catalogo_completo(
    servidor: str,
    database: str,
    pergunta: str,
) -> list[dict[str, Any]]:
    """Combina contexto AF e pontos SMT, preferindo o AF nas duplicidades."""

    catalogo_af = _catalogar_atributos(servidor, database)
    catalogo_smt = _catalogar_smt(servidor, pergunta)
    chaves_af = {
        _normalizar(item.get("atributo", "")) for item in catalogo_af
    }
    return catalogo_af + [
        item for item in catalogo_smt
        if _normalizar(item.get("atributo", "")) not in chaves_af
    ]


def _localizar(pergunta: str, catalogo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pergunta_normalizada = _normalizar(pergunta)
    termos_ordenados = [
        termo for termo in pergunta_normalizada.split()
        if termo not in PALAVRAS_COMUNS and len(termo) >= 1
    ]
    termos = set(termos_ordenados)
    pergunta_sem_palavras_comuns = " ".join(termos_ordenados)
    candidatos: list[dict[str, Any]] = []

    for item in catalogo:
        atributo = _normalizar(item["atributo"])
        pi_point = _normalizar(item.get("pi_point", ""))
        caminho = _normalizar(" ".join(item["caminho"]))
        termos_atributo = set(atributo.split()) | set(pi_point.split())
        termos_caminho = set(caminho.split())
        acertos_atributo = termos & termos_atributo
        acertos_caminho = termos & termos_caminho

        if not acertos_atributo:
            continue

        pontuacao = 6 * len(acertos_atributo) + 3 * len(acertos_caminho)
        termos_especificos_atributo = {
            termo for termo in atributo.split()
            if termo not in PALAVRAS_COMUNS
        }
        # Atributos que cobrem todos os qualificadores citados devem superar
        # nomes genéricos. Ex.: "Vazão Outorga" vence "Vazão" na pergunta
        # "qual a vazão de outorga", mesmo com a preposição entre os termos.
        if termos_especificos_atributo and termos_especificos_atributo <= termos:
            pontuacao += 8 + 2 * len(termos_especificos_atributo)
        if atributo and atributo in pergunta_sem_palavras_comuns:
            pontuacao += 2 * len(termos_especificos_atributo)
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


def _descricao_horario_leitura(timestamp: Any) -> str:
    """Evita apresentar o marco Unix de atributo estático como horário real."""

    texto = str(timestamp or "").strip()
    if not texto:
        return "Horário não informado pelo PI/AF"
    if texto.startswith(("01/01/1970", "1970-01-01", "01/01/0001", "0001-01-01")):
        return "Valor configurado no AF (atributo estático, sem horário de medição)"
    return texto


def _solicitou_contexto_operacional(pergunta: str) -> bool:
    texto = _normalizar(pergunta)
    termos = set(texto.split())
    possui_equipamento = bool(
        re.search(r"\b(?:ta|ds|etf|eic|beq)\s*\d+\b", texto)
    )
    return possui_equipamento and bool(termos & TERMOS_CONTEXTO_OPERACIONAL)


def _informou_apenas_equipamento(pergunta: str) -> bool:
    """Detecta perguntas sem grandeza, ação ou intenção suficientemente definida."""

    texto = _normalizar(pergunta)
    equipamentos = re.findall(
        r"\b(?:ta|ds|etf|eic|beq)\s*\d*\b",
        texto,
    )
    if not equipamentos:
        return False
    restante = texto
    for equipamento in equipamentos:
        restante = restante.replace(equipamento, " ")
    termos_restantes = {
        termo for termo in restante.split()
        if termo not in PALAVRAS_COMUNS and len(termo) >= 2
    }
    return not termos_restantes


def _responder_pedido_ambiguo(pergunta: str) -> dict[str, Any]:
    texto = _normalizar(pergunta)
    match = re.search(r"\b(?:ta|ds|etf|eic|beq)\s*\d*\b", texto)
    equipamento = (
        match.group(0).upper().replace(" ", "-")
        if match
        else "equipamento"
    )
    return {
        "content": (
            f"Você informou **{equipamento}**, mas ainda não indicou o que deseja "
            "consultar. Posso ajudar de algumas formas:\n\n"
            f"- **Contexto geral:** “Mostre o contexto do {equipamento}.”\n"
            f"- **Aeradores:** “Quantos aeradores estão ligados no {equipamento}?”\n"
            f"- **Variável:** “Como está o oxigênio dissolvido do {equipamento}?”\n"
            f"- **Manual:** “O que o manual informa sobre o {equipamento}?”\n\n"
            "Informe uma dessas opções ou escreva o nome da variável desejada."
        )
    }


def _ler_valor_candidato(
    servidor: str,
    database: str,
    candidato: dict[str, Any],
) -> dict[str, Any]:
    if candidato.get("origem") == "SMT":
        return obter_valor_atual_pi_point(
            servidor_pi=servidor,
            nome_pi_point=candidato["pi_point"],
        )
    return obter_valor_atual_atributo(
        servidor=servidor,
        database=database,
        caminho_elementos=candidato["caminho"],
        nome_atributo=candidato["atributo"],
    )


def _responder_contexto_operacional(
    servidor: str,
    database: str,
    pergunta: str,
) -> dict[str, Any]:
    """Responde ao sinal perguntado e monta uma visão curta do equipamento."""

    catalogo = _catalogo_completo(servidor, database, pergunta)
    candidatos = _localizar(pergunta, catalogo)
    if not candidatos:
        return {"content": "Não encontrei o sinal solicitado nesse equipamento."}

    principal = candidatos[0]
    leitura_principal = _ler_valor_candidato(servidor, database, principal)
    unidade_principal = formatar_unidade_engenharia(principal.get("unidade"))
    valor_principal = str(leitura_principal.get("valor", ""))
    if unidade_principal:
        valor_principal += f" {unidade_principal}"

    texto = _normalizar(pergunta)
    match = re.search(r"\b(?:ta|ds|etf|eic|beq)\s*\d+\b", texto)
    equipamento = match.group(0).upper().replace(" ", "-") if match else "equipamento"
    caminho_principal = list(principal.get("caminho") or [])
    atributos_af = [
        item for item in catalogo
        if item.get("origem") == "AF"
        and (
            item.get("caminho") == caminho_principal
            or _normalizar(equipamento)
            in _normalizar(" ".join(item.get("caminho", [])))
        )
    ]

    contexto = []
    usados = {str(principal.get("atributo", "")).upper()}
    for categoria, palavras in CAMPOS_CONTEXTO_RAPIDO:
        correspondente = next(
            (
                item for item in atributos_af
                if str(item.get("atributo", "")).upper() not in usados
                and any(
                    palavra in (_normalizar(item.get("atributo", "")) + " ")
                    for palavra in palavras
                )
            ),
            None,
        )
        if not correspondente:
            continue
        try:
            leitura = _ler_valor_candidato(servidor, database, correspondente)
        except Exception:
            continue
        usados.add(str(correspondente.get("atributo", "")).upper())
        valor = str(leitura.get("valor", ""))
        unidade = formatar_unidade_engenharia(correspondente.get("unidade"))
        contexto.append({
            "Indicador": categoria,
            "Sinal": str(correspondente.get("atributo", "")),
            "Valor atual": valor + (f" {unidade}" if unidade else ""),
        })
        if len(contexto) >= 6:
            break

    return {
        "content": (
            f"No **{equipamento}**, o sinal **{principal['atributo']}** está em "
            f"**{valor_principal}**.\n\n"
            "Abaixo está uma visão rápida dos demais indicadores encontrados "
            "no mesmo contexto. Os valores são leituras atuais e não constituem diagnóstico."
        ),
        "contexto_operacional": contexto,
        "titulo_contexto": f"Contexto rápido — {equipamento}",
    }


def _responder_pergunta(servidor: str, database: str, pergunta: str) -> str:
    if _informou_apenas_equipamento(pergunta):
        return _responder_pedido_ambiguo(pergunta)["content"]
    catalogo = _catalogo_completo(servidor, database, pergunta)
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

    if melhor.get("origem") == "SMT":
        leitura = obter_valor_atual_pi_point(
            servidor_pi=servidor,
            nome_pi_point=melhor["pi_point"],
        )
    else:
        leitura = obter_valor_atual_atributo(
            servidor=servidor,
            database=database,
            caminho_elementos=melhor["caminho"],
            nome_atributo=melhor["atributo"],
        )
    unidade_formatada = formatar_unidade_engenharia(melhor.get("unidade"))
    unidade = f" {unidade_formatada}" if unidade_formatada else ""
    caminho_texto = " / ".join(melhor["caminho"])
    horario = _descricao_horario_leitura(leitura.get("timestamp"))
    atributo_estatico = horario.startswith("Valor configurado no AF")
    tipo_valor = "valor configurado" if atributo_estatico else "valor atual"

    return (
        f"O {tipo_valor} de **{melhor['atributo']}** em **{caminho_texto}** é "
        f"**{leitura['valor']}{unidade}**.\n\n"
        f"**Referência do dado:** {horario}  \n"
        f"**Fonte:** PI System `{servidor}` — "
        + ("SMT/Data Archive" if melhor.get("origem") == "SMT" else f"AF `{database}`")
        + "  \n"
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
    if candidato.get("origem") == "SMT":
        dados = carregar_historico_pi_point(
            servidor_pi=servidor,
            nome_pi_point=candidato["pi_point"],
            inicio=f"*-{horas}h",
            fim="*",
        ).copy()
    else:
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

    catalogo = _catalogo_completo(servidor, database, pergunta)
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

    unidade_a = formatar_unidade_engenharia(primeiro.get("unidade"))
    unidade_b = formatar_unidade_engenharia(segundo.get("unidade"))
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

    catalogo = _catalogo_completo(servidor, database, pergunta)
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

    unidade = formatar_unidade_engenharia(melhor.get("unidade"))
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

    provedor_chat: str | None = None
    modelo_chat: str | None = None
    token_chat: str | None = None

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

    with st.expander("IA e biblioteca técnica", expanded=False):
        status_maria = verificar_maria()
        status_ollama = verificar_ollama()
        provedores = []
        if status_maria.get("disponivel"):
            provedores.append("MAR.IA (corporativa)")
        if status_ollama.get("disponivel") and status_ollama.get("modelos"):
            provedores.append("Ollama (local)")

        if provedores:
            provedor_tela = st.radio(
                "Provedor para perguntas documentais",
                options=provedores,
                horizontal=True,
                key="provedor_ia_chat_maria",
            )
            if provedor_tela.startswith("MAR.IA"):
                provedor_chat = "MAR.IA"
                cache = st.session_state.get("maria_cache_autenticacao", "")
                silencioso = obter_token_maria_silencioso(cache)
                if silencioso.get("cache"):
                    st.session_state["maria_cache_autenticacao"] = silencioso["cache"]
                token_chat = silencioso.get("token") or None

                if token_chat:
                    st.success("MAR.IA conectada com sua conta Microsoft.")
                else:
                    fluxo = st.session_state.get("maria_fluxo_login_chat")
                    if not fluxo and st.button(
                        "🔐 Entrar com a Microsoft",
                        key="entrar_microsoft_chat",
                    ):
                        inicio = iniciar_login_maria(cache)
                        if inicio.get("ok"):
                            st.session_state["maria_fluxo_login_chat"] = inicio["fluxo"]
                            st.session_state["maria_cache_autenticacao"] = inicio["cache"]
                            st.rerun()
                        else:
                            st.error(f"Não foi possível iniciar o login: {inicio.get('erro')}")
                    fluxo = st.session_state.get("maria_fluxo_login_chat")
                    if fluxo:
                        st.info("Abra o endereço, informe o código e conclua o login.")
                        st.link_button(
                            "Abrir login da Microsoft",
                            fluxo.get("verification_uri", "https://microsoft.com/devicelogin"),
                        )
                        st.code(fluxo.get("user_code", ""), language=None)
                        if st.button("✅ Já concluí o login", key="concluir_login_chat"):
                            conclusao = concluir_login_maria(
                                fluxo,
                                st.session_state.get("maria_cache_autenticacao", ""),
                            )
                            if conclusao.get("ok"):
                                st.session_state["maria_cache_autenticacao"] = conclusao["cache"]
                                st.session_state.pop("maria_fluxo_login_chat", None)
                                st.rerun()
                            else:
                                st.error(f"Login não concluído: {conclusao.get('erro')}")
            else:
                provedor_chat = "OLLAMA"
                modelos = list(status_ollama.get("modelos", []))
                modelo_chat = str(st.selectbox(
                    "Modelo local",
                    options=modelos,
                    key="modelo_ia_chat_maria",
                ))
        else:
            st.warning("Nenhum provedor de IA está disponível para perguntas documentais.")

        if database:
            base_documental = _carregar_documentos_chat(str(database))
            total_documentos = int(base_documental.get("total_documentos", 0))
            total_trechos = int(base_documental.get("total_trechos", 0))
            if total_documentos:
                st.caption(
                    f"Biblioteca da base {database}: {total_documentos} documento(s), "
                    f"{total_trechos} trecho(s) pesquisáveis."
                )
                for documento in base_documental.get("documentos_processados", []):
                    st.markdown(
                        f"- `{documento.get('documento', 'Documento sem nome')}` "
                        f"— {documento.get('total_trechos', 0)} trecho(s)"
                    )
            else:
                st.caption(f"Nenhum manual associado à base {database} foi localizado.")

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
            if mensagem.get("contexto_operacional"):
                st.markdown(
                    f"##### {mensagem.get('titulo_contexto', 'Contexto operacional')}"
                )
                st.dataframe(
                    pd.DataFrame(mensagem["contexto_operacional"]),
                    width="stretch",
                    hide_index=True,
                )
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
            with st.spinner("Consultando dados e conhecimento disponíveis..."):
                if _informou_apenas_equipamento(pergunta):
                    resposta = _responder_pedido_ambiguo(pergunta)
                elif _solicitou_lista_documentos(pergunta):
                    resposta = _responder_lista_documentos(str(database))
                elif _solicitou_conhecimento(pergunta):
                    resposta = _responder_documentacao(
                        str(database),
                        pergunta,
                        provedor_chat,
                        modelo_chat,
                        token_chat,
                    )
                elif _solicitou_contexto_operacional(pergunta):
                    resposta = _responder_contexto_operacional(
                        servidor,
                        database,
                        pergunta,
                    )
                elif _solicitou_relacao(pergunta):
                    resposta = _responder_relacao(servidor, database, pergunta)
                elif _solicitou_grafico(pergunta):
                    resposta = _responder_grafico(servidor, database, pergunta)
                else:
                    resposta = {"content": _responder_pergunta(servidor, database, pergunta)}
        except Exception as erro:
            resposta = {"content": f"Não foi possível concluir a consulta ao PI: `{erro}`"}
        historico.append({"role": "assistant", **resposta})
        st.rerun()
