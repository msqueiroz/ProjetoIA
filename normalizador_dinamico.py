import pandas as pd


def aplicar_mapeamento_dinamico(
    dados,
    mapa_dinamico
):

    dados_normalizados = dados.copy()

    dados_normalizados = dados_normalizados.rename(
        columns=mapa_dinamico
    )


    return dados_normalizados

def normalizar_unidades_dinamicas(
    dados,
    unidade_tensao="V",
    unidade_temperatura="°C",
    unidade_nivel="%"
):

    dados_normalizados = dados.copy()

    if (
        "tensao_v" in dados_normalizados.columns
        and unidade_tensao == "kV"
    ):

        dados_normalizados["tensao_v"] = (
            pd.to_numeric(
                dados_normalizados["tensao_v"],
                errors="coerce"
            ) * 1000
        )

    if (
        "temp_mancal_c" in dados_normalizados.columns
        and unidade_temperatura == "°F"
    ):

        temperatura_f = pd.to_numeric(
            dados_normalizados["temp_mancal_c"],
            errors="coerce"
        )

        dados_normalizados["temp_mancal_c"] = (
            (temperatura_f - 32) * 5 / 9
        ).round(1)

    if (
        "nivel_pct" in dados_normalizados.columns
        and unidade_nivel == "Fração 0-1"
    ):

        dados_normalizados["nivel_pct"] = (
            pd.to_numeric(
                dados_normalizados["nivel_pct"],
                errors="coerce"
            ) * 100
        )

    return dados_normalizados