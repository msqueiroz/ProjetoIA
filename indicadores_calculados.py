"""Indicadores derivados, calculados com rastreabilidade e validações físicas."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

import pandas as pd

from conhecimento_ete import ESTRUTURA_PROCESSO_ETE
from unidades_engenharia import formatar_unidade_engenharia


CATALOGO_CALCULOS: dict[str, dict[str, Any]] = {
    "tdh": {
        "nome": "Tempo de detenção hidráulica (TDH)",
        "formula": "TDH = volume útil / vazão média",
        "resultado_unidade": "h",
        "entradas": ("volume útil (m³)", "vazão do efluente que entra no tanque (m³/h)", "vazão de reciclo de lodo (m³/h)"),
        "status": "OPERACIONAL",
        "observacao": "No tanque de aeração, soma a vazão do efluente e a vazão do lodo de reciclo.",
    },
    "balanco_hidraulico": {
        "nome": "Balanço hidráulico",
        "formula": "desvio = |Qentrada - Qsaída| / média(Qentrada, Qsaída)",
        "resultado_unidade": "%",
        "entradas": ("vazão de entrada (m³/h)", "vazão de saída (m³/h)"),
        "status": "OPERACIONAL",
        "observacao": "Qualifica a confiança do TDH e evidencia possíveis mudanças de nível ou fronteira incorreta.",
    },
    "carga": {
        "nome": "Carga de massa",
        "formula": "carga = concentração × vazão / 1000",
        "resultado_unidade": "kg/h",
        "entradas": ("concentração (mg/L)", "vazão (m³/h)"),
        "status": "NÚCLEO PRONTO",
        "observacao": "A associação dos sinais do PI deve ser confirmada antes do cálculo.",
    },
    "eficiencia_remocao": {
        "nome": "Eficiência de remoção",
        "formula": "eficiência = (entrada - saída) / entrada × 100",
        "resultado_unidade": "%",
        "entradas": ("valor ou carga de entrada", "valor ou carga de saída"),
        "status": "NÚCLEO PRONTO",
        "observacao": "Entrada e saída precisam representar o mesmo indicador e período.",
    },
}


def listar_catalogo_calculos() -> list[dict[str, Any]]:
    return [{"codigo": codigo, **configuracao} for codigo, configuracao in CATALOGO_CALCULOS.items()]


def identificar_calculos(pergunta: Any) -> list[str]:
    texto = unicodedata.normalize("NFKD", str(pergunta or "")).encode("ascii", "ignore").decode().lower()
    encontrados: list[str] = []
    if "tdh" in texto or (("detencao" in texto or "retencao" in texto) and "hidraul" in texto):
        encontrados.extend(["tdh", "balanco_hidraulico"])
    if "balanco hidraul" in texto:
        encontrados.append("balanco_hidraulico")
    if re.search(r"\bcarga\b", texto):
        encontrados.append("carga")
    if "eficiencia" in texto and ("remocao" in texto or "remover" in texto):
        encontrados.append("eficiencia_remocao")
    return list(dict.fromkeys(encontrados))


def calcular_carga_kg_h(concentracao_mg_l: float, vazao_m3_h: float) -> float:
    if concentracao_mg_l < 0 or vazao_m3_h < 0:
        raise ValueError("Concentração e vazão não podem ser negativas.")
    return float(concentracao_mg_l) * float(vazao_m3_h) / 1000.0


def calcular_eficiencia_remocao_pct(entrada: float, saida: float) -> float:
    if entrada <= 0:
        raise ValueError("O valor de entrada deve ser maior que zero.")
    return (float(entrada) - float(saida)) / float(entrada) * 100.0


def identificar_pedido_tdh(pergunta: Any) -> bool:
    texto = str(pergunta or "").lower()
    texto_sem_acentos = (
        texto.replace("á", "a").replace("â", "a").replace("ã", "a")
        .replace("ç", "c").replace("é", "e").replace("í", "i")
    )
    return bool(
        re.search(r"\btdh\b", texto)
        or (
            any(termo in texto for termo in ("detenção", "detencao", "retenção", "retencao"))
            and "hidraul" in texto_sem_acentos
        )
    )


def extrair_tanque(pergunta: Any) -> str | None:
    texto = str(pergunta or "").upper()
    encontrado = re.search(r"\bTA\s*[- ]?\s*0*(\d+)\b", texto)
    return f"TA-{int(encontrado.group(1))}" if encontrado else None


def extrair_data(pergunta: Any) -> date | None:
    encontrado = re.search(
        r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2}|\d{4})\b",
        str(pergunta or ""),
    )
    if not encontrado:
        return None
    dia, mes, ano = (int(valor) for valor in encontrado.groups())
    if ano < 100:
        ano += 2000
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def obter_dados_tanque(codigo: str) -> dict[str, Any] | None:
    for etapa in ESTRUTURA_PROCESSO_ETE.get("etapas_principais", []):
        if str(etapa.get("codigo", "")).upper() == str(codigo).upper():
            return etapa
    return None


def converter_vazao_m3_h(
    serie: pd.Series,
    unidade: Any,
    nome_atributo: Any = "",
) -> tuple[pd.Series | None, str]:
    unidade_formatada = formatar_unidade_engenharia(unidade)
    nome = str(nome_atributo or "").lower().replace("³", "3")

    if unidade_formatada in ("m³/h", "m3/h") or "m3/h" in nome:
        return serie, "m³/h"
    if unidade_formatada in ("m³/s", "m3/s") or "m3/s" in nome:
        return serie * 3600.0, "m³/h"
    if unidade_formatada == "L/s" or "l/s" in nome:
        return serie * 3.6, "m³/h"
    if unidade_formatada == "L/h" or "l/h" in nome:
        return serie / 1000.0, "m³/h"
    return None, unidade_formatada or "não informada"


def resumir_vazao_ponderada(
    historico_vazao: pd.DataFrame,
) -> dict[str, Any]:
    """Resume eventos comprimidos do PI ponderando cada intervalo pelo tempo."""

    dados = historico_vazao.copy()
    dados["data_hora"] = pd.to_datetime(dados["data_hora"], errors="coerce")
    dados["valor"] = pd.to_numeric(dados["valor"], errors="coerce")
    dados = dados.dropna(subset=["data_hora", "valor"])
    dados = dados[dados["valor"] > 0].sort_values("data_hora")
    dados = dados.drop_duplicates(subset=["data_hora"], keep="last")
    if len(dados) < 2:
        raise ValueError("São necessários ao menos dois registros positivos no período.")

    proximo_tempo = dados["data_hora"].shift(-1)
    proximo_valor = dados["valor"].shift(-1)
    duracao_h = (proximo_tempo - dados["data_hora"]).dt.total_seconds() / 3600.0
    intervalos_validos = duracao_h.notna() & (duracao_h > 0)
    duracao_h = duracao_h[intervalos_validos]
    vazao_media_intervalo = (
        (dados.loc[intervalos_validos, "valor"] + proximo_valor[intervalos_validos]) / 2.0
    )
    volume_observado = float((vazao_media_intervalo * duracao_h).sum())
    cobertura_h = float(duracao_h.sum())
    if cobertura_h <= 0:
        raise ValueError("O histórico não possui duração temporal válida.")

    return {
        "vazao_media_m3_h": volume_observado / cobertura_h,
        "volume_observado_m3": volume_observado,
        "registros_validos": int(len(dados)),
        "cobertura_observada_h": cobertura_h,
        "vazao_min_m3_h": float(dados["valor"].min()),
        "vazao_max_m3_h": float(dados["valor"].max()),
    }


def calcular_tdh_balanco(
    historico_entrada: pd.DataFrame,
    historico_saida: pd.DataFrame,
    volume_util_m3: float,
) -> dict[str, Any]:
    """Calcula TDH por entrada e saída e qualifica o balanço hidráulico."""

    entrada = resumir_vazao_ponderada(historico_entrada)
    saida = resumir_vazao_ponderada(historico_saida)
    q_entrada = entrada["vazao_media_m3_h"]
    q_saida = saida["vazao_media_m3_h"]
    q_media = (q_entrada + q_saida) / 2.0
    divergencia_pct = abs(q_entrada - q_saida) / q_media * 100.0
    cobertura_minima = min(
        entrada["cobertura_observada_h"], saida["cobertura_observada_h"]
    )

    if divergencia_pct <= 5 and cobertura_minima >= 20:
        confianca = "ALTA"
    elif divergencia_pct <= 10 and cobertura_minima >= 18:
        confianca = "MODERADA"
    else:
        confianca = "BAIXA"

    tdh_consolidado = float(volume_util_m3) / q_media if divergencia_pct <= 10 else None
    return {
        "entrada": entrada,
        "saida": saida,
        "tdh_entrada_h": float(volume_util_m3) / q_entrada,
        "tdh_saida_h": float(volume_util_m3) / q_saida,
        "tdh_consolidado_h": tdh_consolidado,
        "divergencia_balanco_pct": divergencia_pct,
        "confianca": confianca,
        "cobertura_comum_aproximada_h": cobertura_minima,
    }


def calcular_tdh_diario(
    historico_vazao: pd.DataFrame,
    volume_util_m3: float,
) -> dict[str, Any]:
    """Compatibilidade com a estimativa por uma corrente, agora ponderada no tempo."""

    resumo = resumir_vazao_ponderada(historico_vazao)
    dados = historico_vazao.copy()
    dados["valor"] = pd.to_numeric(dados["valor"], errors="coerce")
    dados = dados[dados["valor"] > 0]
    dados["tdh_h"] = float(volume_util_m3) / dados["valor"]

    return {
        "tdh_medio_h": float(volume_util_m3) / resumo["vazao_media_m3_h"],
        "tdh_mediano_h": float(dados["tdh_h"].median()),
        "tdh_min_h": float(dados["tdh_h"].min()),
        "tdh_max_h": float(dados["tdh_h"].max()),
        **resumo,
    }
