"""Regras deterministicas de elegibilidade fisica do processo.

A topologia limita quais variaveis podem disputar uma hipotese de
contribuicao direta. Ela nao cria nem comprova causalidade.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Mapping


ROTAS_PROCESSO = {
    "ROTA_ETF1": {
        "origens": ("TA-1", "TA-2"),
        "decantadores": tuple(f"DS-{numero}" for numero in range(1, 7)),
        "destinos": ("ETF-1",),
        "tags_alvo_conhecidas": ("TUT-DS1",),
    },
    "ROTA_ETF2": {
        "origens": ("TA-3", "TA-4"),
        "decantadores": tuple(f"DS-{numero}" for numero in range(7, 13)),
        "destinos": ("ETF-2",),
        "tags_alvo_conhecidas": ("TUT-DS2",),
    },
}

# Elementos comuns ou consolidados não recebem uma rota exclusiva.
# A tela do PI Vision confirma EIC como entrada comum e ETF como visão final.
ELEMENTOS_COMPARTILHADOS = ("EIC", "ETF")


# Catálogo semântico declarativo. Novos indicadores podem ser acrescentados aos
# dados de configuração sem criar um novo fluxo de tela ou uma nova regra de
# execução. A topologia continua sendo a autoridade sobre a rota física.
CATALOGO_INDICADORES = {
    "TURBIDEZ": {
        "nome": "Turbidez",
        "sinonimos": ("TURBIDEZ", "TUT"),
        "tags_por_rota": {
            "ROTA_ETF1": "TUT-DS1",
            "ROTA_ETF2": "TUT-DS2",
        },
        "estrategia_analitica": "SERIE_CONTINUA",
        "pi_point_confirmado": True,
    },
    "AMONIA": {
        "nome": "Amônia",
        "sinonimos": (
            "AMONIA",
            "NITROGENIO AMONIACAL",
            "N-NH3",
            "NNH3",
            "NH3",
        ),
        "tags_por_rota": {
            "ROTA_ETF1": "NNH3 ETF-1",
            "ROTA_ETF2": "NNH3 ETF-2",
        },
        "estrategia_analitica": "SERIE_CONTINUA",
        # "NNH3 ETF-x" é o nome funcional visto na estrutura, não há garantia
        # de que seja o nome do PI Point no Data Archive.
        "pi_point_confirmado": False,
    },
}

PALAVRAS_IGNORADAS_OBJETIVO = {
    "A", "AS", "DA", "DAS", "DE", "DO", "DOS", "E", "EM", "EXISTE",
    "HOUVE", "NA", "NAS", "NO", "NOS", "O", "OS", "PARA", "PIORA",
    "POR", "PORQUE", "QUE", "QUAL", "SAIDA", "ENTRADA", "AUMENTO",
    "REDUCAO", "INVESTIGAR", "ENTENDER", "AUMENTAR", "AUMENTOU",
    "DIMINUIR", "DIMINUIU", "ALTERACAO", "ALTERACOES", "VARIACAO",
    "VARIACOES", "OCORREU", "OCORRER", "UM", "UMA",
}


def resolver_objetivo_estudo(objetivo: Any) -> dict[str, Any] | None:
    """Interpreta indicador e destino usando um catálogo semântico auditável.

    A função não escolhe variáveis causais. Ela somente resolve a identidade do
    alvo e entrega a rota para a validação física realizada nas etapas seguintes.
    """

    texto_original = str(objetivo or "")
    texto = _normalizar(texto_original)
    rota = None
    if "TUTDS1" in texto or "ETF1" in texto:
        rota = "ROTA_ETF1"
    elif "TUTDS2" in texto or "ETF2" in texto:
        rota = "ROTA_ETF2"

    indicador = None
    for configuracao_indicador in CATALOGO_INDICADORES.values():
        if any(
            _normalizar(sinonimo) in texto
            for sinonimo in configuracao_indicador["sinonimos"]
        ):
            indicador = configuracao_indicador
            break

    if not indicador or not rota:
        return None

    configuracao = ROTAS_PROCESSO[rota]
    tag = indicador["tags_por_rota"].get(rota)
    if not tag:
        return None

    tag_explicita = next(
        (
            tag_catalogada
            for tag_catalogada in indicador["tags_por_rota"].values()
            if _normalizar(tag_catalogada) in texto
        ),
        None,
    )
    return {
        "indicador": indicador["nome"],
        "tag_principal": tag_explicita or tag,
        "rota": rota,
        "origens_elegiveis": list(configuracao["origens"]),
        "decantadores_elegiveis": list(configuracao["decantadores"]),
        "destino": configuracao["destinos"][0],
        "estrategia_analitica": indicador["estrategia_analitica"],
        "confianca": "ALTA",
        "origem_contexto": "CATALOGO_SEMANTICO_E_TOPOLOGIA",
        "requer_confirmacao": not indicador.get("pi_point_confirmado", False),
    }


def sugerir_termos_busca_objetivo(objetivo: Any, limite: int = 3) -> list[str]:
    """Extrai termos úteis para descobrir tags reais sem conhecer o indicador."""

    valor = unicodedata.normalize("NFKD", str(objetivo or ""))
    valor = "".join(letra for letra in valor if not unicodedata.combining(letra))
    tokens = re.findall(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", valor.upper())
    termos: list[str] = []
    for token in tokens:
        compacto = _normalizar(token)
        if (
            compacto in PALAVRAS_IGNORADAS_OBJETIVO
            or re.fullmatch(r"ETF\d*|TA\d+|DS\d+", compacto)
            or len(compacto) < 2
        ):
            continue
        if token not in termos:
            termos.append(token)
        if len(termos) >= limite:
            break
    return termos


def ranquear_tags_para_objetivo(
    objetivo: Any,
    tags: Iterable[Any],
) -> list[dict[str, Any]]:
    """Ordena tags descobertas por aderência textual e compatibilidade de rota."""

    termos = sugerir_termos_busca_objetivo(objetivo, limite=8)
    rota_objetivo = identificar_rota(objetivo)
    ranking = []
    vistas = set()
    for valor in tags:
        tag = str(valor or "").strip()
        chave = tag.upper()
        if not tag or chave in vistas:
            continue
        vistas.add(chave)
        nome = _normalizar(tag)
        correspondencias = sum(
            1 for termo in termos if _normalizar(termo) in nome
        )
        rota_tag = identificar_rota(tag)
        if rota_objetivo and rota_tag and rota_objetivo != rota_tag:
            continue
        bonus_rota = 3 if rota_objetivo and rota_tag == rota_objetivo else 0
        ranking.append({
            "tag_principal": tag,
            "pontuacao": correspondencias * 2 + bonus_rota,
            "correspondencias": correspondencias,
            "rota": rota_tag or rota_objetivo,
        })
    return sorted(
        ranking,
        key=lambda item: (-item["pontuacao"], item["tag_principal"].upper()),
    )


def construir_resolucao_tag(
    objetivo: Any,
    tag_principal: Any,
) -> dict[str, Any] | None:
    """Cria uma resolução auditável após a confirmação de uma tag descoberta."""

    tag = str(tag_principal or "").strip()
    rota = identificar_rota(tag) or identificar_rota(objetivo)
    if not tag or not rota:
        return None
    configuracao = ROTAS_PROCESSO[rota]
    termos = sugerir_termos_busca_objetivo(objetivo, limite=1)
    indicador = termos[0].replace("-", " ").title() if termos else tag
    return {
        "indicador": indicador,
        "tag_principal": tag,
        "rota": rota,
        "origens_elegiveis": list(configuracao["origens"]),
        "decantadores_elegiveis": list(configuracao["decantadores"]),
        "destino": configuracao["destinos"][0],
        "estrategia_analitica": "SERIE_CONTINUA_A_CONFIRMAR",
        "confianca": "CONFIRMADA_PELO_USUARIO",
        "origem_contexto": "DESCOBERTA_DINAMICA_DATA_ARCHIVE",
        "requer_confirmacao": False,
    }


def _normalizar(texto: Any) -> str:
    valor = unicodedata.normalize("NFKD", str(texto or ""))
    valor = "".join(letra for letra in valor if not unicodedata.combining(letra))
    return re.sub(r"[^A-Z0-9]+", "", valor.upper())


def _valor_metadado(metadados: Mapping[str, Any] | None, *nomes: str) -> str:
    if not metadados:
        return ""
    indice = {_normalizar(chave): valor for chave, valor in metadados.items()}
    for nome in nomes:
        valor = indice.get(_normalizar(nome))
        if valor not in (None, ""):
            return str(valor)
    return ""


def identificar_rotas_detectadas(
    nome_variavel: Any,
    metadados: Mapping[str, Any] | None = None,
) -> set[str]:
    """Reúne todas as rotas indicadas pela identidade operacional."""

    rotas: set[str] = set()
    rota_af = _valor_metadado(
        metadados,
        "CTX_Grupo_Rota",
        "CTX_Grupo_Rota_Recebido",
        "CTX_Destino_Processo",
    )
    rota_normalizada = _normalizar(rota_af)
    if "ETF1" in rota_normalizada:
        rotas.add("ROTA_ETF1")
    if "ETF2" in rota_normalizada:
        rotas.add("ROTA_ETF2")

    identidade = " ".join([
        str(nome_variavel or ""),
        _valor_metadado(metadados, "caminho_af"),
        _valor_metadado(metadados, "elemento_af"),
        _valor_metadado(metadados, "atributo_af"),
        _valor_metadado(metadados, "pi_point", "tag_smt"),
    ])
    identidade_maiuscula = identidade.upper()
    ds_linha_1 = bool(re.search(
        r"(?:^|[\s>|])DS[-_ ]?0?[1-6](?!\d)",
        identidade_maiuscula,
    ))
    ds_linha_2 = bool(re.search(
        r"(?:^|[\s>|])DS[-_ ]?0?(?:[7-9]|1[0-2])(?!\d)",
        identidade_maiuscula,
    ))
    nome = _normalizar(identidade)
    if (
        re.search(r"TA0?[12](?!\d)", nome)
        or ds_linha_1
        or "ETF1" in nome
        or "TUTDS1" in nome
    ):
        rotas.add("ROTA_ETF1")
    if (
        re.search(r"TA0?[34](?!\d)", nome)
        or ds_linha_2
        or "ETF2" in nome
        or "TUTDS2" in nome
    ):
        rotas.add("ROTA_ETF2")
    return rotas


def identificar_rota(
    nome_variavel: Any,
    metadados: Mapping[str, Any] | None = None,
) -> str | None:
    """Retorna a rota somente quando a identidade é inequívoca."""

    rotas = identificar_rotas_detectadas(nome_variavel, metadados)
    return next(iter(rotas)) if len(rotas) == 1 else None


def avaliar_contexto_dados(
    nome_variavel: Any,
    metadados: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Avalia identificação e rastreabilidade sem interpretar o processo."""

    metadados = metadados or {}
    caminho_af = _valor_metadado(metadados, "caminho_af")
    pi_point = _valor_metadado(metadados, "pi_point", "tag_smt")
    fonte = _valor_metadado(metadados, "fonte_dados", "estrategia")
    rota = identificar_rota(nome_variavel, metadados)
    rotas_detectadas = identificar_rotas_detectadas(nome_variavel, metadados)
    observacoes = []

    if not pi_point:
        observacoes.append(
            "O identificador do ponto no Data Archive/SMT não foi confirmado."
        )
    if not caminho_af:
        observacoes.append(
            "O caminho contextual no AF não foi informado."
        )
    if len(rotas_detectadas) > 1:
        observacoes.append(
            "Há conflito entre as rotas indicadas pelo tag e pelo contexto AF: "
            + ", ".join(sorted(rotas_detectadas))
            + ". O cadastro deve ser validado antes da análise direta."
        )
    elif not rota:
        observacoes.append(
            "A rota física não pôde ser identificada pelos metadados disponíveis."
        )

    return {
        "variavel": str(nome_variavel),
        "fonte_dados": fonte or "Não identificada",
        "pi_point": pi_point or "Não identificado",
        "caminho_af": caminho_af or "Não identificado",
        "rota_identificada": rota or "NÃO IDENTIFICADA",
        "contexto_confirmado": bool(
            pi_point and caminho_af and rota and len(rotas_detectadas) == 1
        ),
        "rotas_detectadas": sorted(rotas_detectadas),
        "observacoes_dados": observacoes,
    }


def avaliar_elegibilidade_fisica(
    variavel_alvo: Any,
    variavel_candidata: Any,
    metadados_alvo: Mapping[str, Any] | None = None,
    metadados_candidata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classifica a candidata antes da correlacao e explica a decisao."""

    rota_alvo = identificar_rota(variavel_alvo, metadados_alvo)
    rota_candidata = identificar_rota(variavel_candidata, metadados_candidata)
    rotas_alvo = identificar_rotas_detectadas(variavel_alvo, metadados_alvo)
    rotas_candidata = identificar_rotas_detectadas(
        variavel_candidata,
        metadados_candidata,
    )

    if len(rotas_alvo) > 1 or len(rotas_candidata) > 1:
        return {
            "elegivel": False,
            "classificacao_topologica": "CONTEXTO AMBIGUO",
            "rota_alvo": ", ".join(sorted(rotas_alvo)) or None,
            "rota_candidata": ", ".join(sorted(rotas_candidata)) or None,
            "motivo_topologia": (
                "O tag e o contexto AF indicam rotas conflitantes. "
                "A relação direta foi bloqueada até a validação do cadastro."
            ),
        }

    if rota_alvo and rota_candidata and rota_alvo != rota_candidata:
        return {
            "elegivel": False,
            "classificacao_topologica": "INCOMPATIVEL",
            "rota_alvo": rota_alvo,
            "rota_candidata": rota_candidata,
            "motivo_topologia": (
                f"A candidata pertence a {rota_candidata}, mas o alvo "
                f"pertence a {rota_alvo}; nao existe rota direta conhecida."
            ),
        }

    if rota_alvo and rota_candidata:
        classificacao = "ROTA DIRETA"
        motivo = f"Alvo e candidata pertencem a {rota_alvo}."
    else:
        classificacao = "SEM ROTA CONHECIDA"
        motivo = (
            "A topologia cadastrada nao permite confirmar nem descartar "
            "uma rota direta; a candidata foi mantida com ressalva."
        )

    return {
        "elegivel": True,
        "classificacao_topologica": classificacao,
        "rota_alvo": rota_alvo,
        "rota_candidata": rota_candidata,
        "motivo_topologia": motivo,
    }
