import pandas as pd
from perfis_normalizacao import PERFIS_NORMALIZACAO


def normalizar_data_hora(dados):

    dados = dados.copy()

    if "data_hora" in dados.columns:

        dados["data_hora"] = pd.to_datetime(
            dados["data_hora"],
            errors="coerce"
        )

    return dados


def normalizar_status_bomba(dados):

    dados = dados.copy()

    if "status_bomba" in dados.columns:

        mapa_status = {
            "RUNNING": 1,
            "RUN": 1,
            "ON": 1,
            "LIGADA": 1,
            "LIGADO": 1,

            "STOPPED": 0,
            "STOP": 0,
            "OFF": 0,
            "PARADA": 0,
            "PARADO": 0
        }

        dados["status_bomba"] = (
            dados["status_bomba"]
            .replace(mapa_status)
        )

        dados["status_bomba"] = pd.to_numeric(
            dados["status_bomba"],
            errors="coerce"
        )

    return dados

def converter_tensao_kv_para_v(dados):

    dados = dados.copy()

    if "tensao_v" in dados.columns:
        dados["tensao_v"] = (
            pd.to_numeric(
                dados["tensao_v"],
                errors="coerce"
            ) * 1000
        )

    return dados


def converter_temperatura_f_para_c(dados):

    dados = dados.copy()

    if "temp_mancal_c" in dados.columns:

        temperatura_f = pd.to_numeric(
            dados["temp_mancal_c"],
            errors="coerce"
        )

        dados["temp_mancal_c"] = (
            (temperatura_f - 32) * 5 / 9
        ).round(1)

    return dados


def converter_nivel_fracao_para_pct(dados):

    dados = dados.copy()

    if "nivel_pct" in dados.columns:

        dados["nivel_pct"] = (
            pd.to_numeric(
                dados["nivel_pct"],
                errors="coerce"
            ) * 100
        )

    return dados


def normalizar_dados(dados, perfil="padrao"):

    dados_normalizados = dados.copy()

    configuracao = PERFIS_NORMALIZACAO.get(
        perfil
    )

    if configuracao is None:
        raise ValueError(
            f"Perfil de normalização '{perfil}' não encontrado."
        )

    dados_normalizados = normalizar_data_hora(
        dados_normalizados
    )

    dados_normalizados = normalizar_status_bomba(
        dados_normalizados
    )

    conversoes = configuracao[
        "conversoes"
    ]

    if conversoes["tensao"] == "kv_para_v":

        dados_normalizados = converter_tensao_kv_para_v(
            dados_normalizados
        )

    if conversoes["temperatura"] == "f_para_c":

        dados_normalizados = converter_temperatura_f_para_c(
            dados_normalizados
        )

    if conversoes["nivel"] == "fracao_para_pct":

        dados_normalizados = converter_nivel_fracao_para_pct(
            dados_normalizados
        )

    return dados_normalizados