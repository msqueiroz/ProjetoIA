import pandas as pd


def analisar_qualidade(dados):

    total_linhas = len(dados)
    total_colunas = len(dados.columns)

    total_celulas = total_linhas * total_colunas

    valores_ausentes = dados.isna().sum().sum()

    if total_celulas > 0:
        completude = (
            (total_celulas - valores_ausentes)
            / total_celulas
        ) * 100
    else:
        completude = 0

    return {
        "total_linhas": total_linhas,
        "total_colunas": total_colunas,
        "valores_ausentes": valores_ausentes,
        "completude": completude
    }
def verificar_variaveis(dados):

    variaveis_esperadas = [
        "data_hora",
        "status_bomba",
        "tensao_v",
        "corrente_a",
        "temp_mancal_c",
        "vibracao_mm_s",
        "nivel_pct",
        "alarme"
    ]

    presentes = []
    ausentes = []

    for coluna in variaveis_esperadas:

        if coluna in dados.columns:
            presentes.append(coluna)

        else:
            ausentes.append(coluna)

    return {
        "esperadas": len(variaveis_esperadas),
        "presentes": len(presentes),
        "ausentes": ausentes
    }


def verificar_inconsistencias(dados):

    inconsistencias = []

    # status_bomba só pode ser 0 ou 1
    if "status_bomba" in dados.columns:

        invalidos_status = dados[
            ~dados["status_bomba"].isin([0, 1])
        ]

        if len(invalidos_status) > 0:
            inconsistencias.append(
                f"{len(invalidos_status)} registros com status_bomba inválido."
            )

    # nível deve estar entre 0 e 100%
    if "nivel_pct" in dados.columns:

        nivel_invalido = dados[
            (dados["nivel_pct"] < 0) |
            (dados["nivel_pct"] > 100)
        ]

        if len(nivel_invalido) > 0:
            inconsistencias.append(
                f"{len(nivel_invalido)} registros com nível fora de 0 a 100%."
            )

    # tensão não deve ser negativa
    if "tensao_v" in dados.columns:

        tensao_invalida = dados[
            dados["tensao_v"] < 0
        ]

        if len(tensao_invalida) > 0:
            inconsistencias.append(
                f"{len(tensao_invalida)} registros com tensão negativa."
            )

    return inconsistencias

def localizar_valores_ausentes(dados):

    detalhes = []

    for coluna in dados.columns:

        linhas_ausentes = dados[
            dados[coluna].isna()
        ]

        for indice, linha in linhas_ausentes.iterrows():

            if "data_hora" in dados.columns:
                horario = linha["data_hora"]
            else:
                horario = "Não disponível"

            detalhes.append({
                "indice": indice,
                "data_hora": horario,
                "variavel": coluna
            })

    return detalhes

def verificar_continuidade_temporal(dados, intervalo_esperado_min=30):

    gaps = []

    if "data_hora" not in dados.columns:
        return gaps

    dados_ordenados = dados.sort_values(
        "data_hora"
    ).copy()

    dados_ordenados["data_hora"] = pd.to_datetime(
        dados_ordenados["data_hora"]
    )

    dados_ordenados["diferenca_min"] = (
        dados_ordenados["data_hora"]
        .diff()
        .dt.total_seconds()
        / 60
    )

    for indice, linha in dados_ordenados.iterrows():

        diferenca = linha["diferenca_min"]

        if pd.notna(diferenca) and diferenca > intervalo_esperado_min:

            registros_ausentes = int(
                diferenca / intervalo_esperado_min
            ) - 1

            gaps.append({
                "data_hora": linha["data_hora"],
                "intervalo_detectado_min": diferenca,
                "registros_ausentes_estimados": registros_ausentes
            })

    return gaps


def gerar_relatorio_qualidade(dados):

    qualidade_basica = analisar_qualidade(dados)
    variaveis = verificar_variaveis(dados)
    inconsistencias = verificar_inconsistencias(dados)
    gaps_temporais = verificar_continuidade_temporal(dados)
    detalhes_ausentes = localizar_valores_ausentes(dados)
    completude = qualidade_basica["completude"]

    quantidade_inconsistencias = len(inconsistencias)
    quantidade_variaveis_ausentes = len(
        variaveis["ausentes"]
    )

    # =========================
    # CLASSIFICAÇÃO GERAL
    # =========================
    quantidade_gaps = len(gaps_temporais)
    if (
        completude >= 99
        and quantidade_inconsistencias == 0
        and quantidade_variaveis_ausentes == 0
        and quantidade_gaps == 0
    ):
        status = "BOA"

    elif (
        completude >= 90
        and quantidade_variaveis_ausentes == 0
    ):
        status = "ATENÇÃO"

    else:
        status = "CRÍTICA"

    # =========================
    # APTIDÃO PARA DIAGNÓSTICO
    # =========================

    if status == "BOA":
        aptidao = "SIM"

    elif status == "ATENÇÃO":
        aptidao = "COM RESSALVAS"

    else:
        aptidao = "NÃO"


    return {
        "total_linhas": qualidade_basica["total_linhas"],
        "total_colunas": qualidade_basica["total_colunas"],
        "valores_ausentes": qualidade_basica["valores_ausentes"],
        "completude": qualidade_basica["completude"],

        "variaveis_esperadas": variaveis["esperadas"],
        "variaveis_presentes": variaveis["presentes"],
        "variaveis_ausentes": variaveis["ausentes"],

        "inconsistencias": inconsistencias,
        "quantidade_inconsistencias": quantidade_inconsistencias,

        "detalhes_ausentes": detalhes_ausentes,

        "gaps_temporais": gaps_temporais,
        "quantidade_gaps": len(gaps_temporais),

        
        "status": status,
        "aptidao_diagnostico": aptidao
    }