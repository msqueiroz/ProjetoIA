import pandas as pd


def preparar_historico(

    df,
    coluna_data="data_hora",
    coluna_valor="valor"
):

    dados = df.copy()

    dados[coluna_data] = pd.to_datetime(
        dados[coluna_data],
        errors="coerce"
    )

    dados["valor_numerico"] = pd.to_numeric(
        dados[coluna_valor],
        errors="coerce"
    )

    dados = dados.dropna(
        subset=[
            coluna_data,
            "valor_numerico"
        ]
    )

    dados = dados.sort_values(
        coluna_data
    )

    dados = dados.drop_duplicates(
        subset=[
            coluna_data
        ]
    )

    dados = dados.reset_index(
        drop=True
    )

    return dados

def alinhar_series(
    df_a,
    df_b,
    nome_a="variavel_a",
    nome_b="variavel_b",
    tolerancia="30min"
):

    serie_a = preparar_historico(
        df_a
    ).rename(
        columns={
            "valor_numerico": nome_a
        }
    )[
        [
            "data_hora",
            nome_a
        ]
    ]

    serie_b = preparar_historico(
        df_b
    ).rename(
        columns={
            "valor_numerico": nome_b
        }
    )[
        [
            "data_hora",
            nome_b
        ]
    ]

    serie_a = serie_a.sort_values(
        "data_hora"
    )

    serie_b = serie_b.sort_values(
        "data_hora"
    )

    alinhado = pd.merge_asof(
        serie_a,
        serie_b,
        on="data_hora",
        direction="nearest",
        tolerance=pd.Timedelta(
            tolerancia
        )
    )

    alinhado = alinhado.dropna(
        subset=[
            nome_a,
            nome_b
        ]
    )

    alinhado = alinhado.reset_index(
        drop=True
    )

    return alinhado

def calcular_correlacao(
    df_alinhado,
    nome_a="variavel_a",
    nome_b="variavel_b",
    minimo_pontos=5
):

    if df_alinhado.empty:
        return {
            "correlacao": None,
            "classificacao": "SEM DADOS",
            "direcao": "-",
            "confiabilidade": "BAIXA",
            "pontos_validos": 0
        }

    dados_validos = df_alinhado[
        [
            nome_a,
            nome_b
        ]
    ].dropna()

    pontos_validos = len(
        dados_validos
    )

    if pontos_validos < minimo_pontos:
        return {
            "correlacao": None,
            "classificacao": "DADOS INSUFICIENTES",
            "direcao": "-",
            "confiabilidade": "BAIXA",
            "pontos_validos": pontos_validos
        }

    correlacao = dados_validos[
        nome_a
    ].corr(
        dados_validos[
            nome_b
        ]
    )

    if pd.isna(correlacao):
        return {
            "correlacao": None,
            "classificacao": "NÃO CALCULÁVEL",
            "direcao": "-",
            "confiabilidade": "BAIXA",
            "pontos_validos": pontos_validos
        }

    valor_absoluto = abs(
        correlacao
    )

    # =========================
    # FORÇA DA CORRELAÇÃO
    # =========================

    if valor_absoluto >= 0.80:
        classificacao = "FORTE"

    elif valor_absoluto >= 0.50:
        classificacao = "MODERADA"

    elif valor_absoluto >= 0.30:
        classificacao = "FRACA"

    else:
        classificacao = "MUITO FRACA"

    # =========================
    # DIREÇÃO
    # =========================

    if correlacao > 0:
        direcao = "POSITIVA"

    elif correlacao < 0:
        direcao = "NEGATIVA"

    else:
        direcao = "NEUTRA"

    # =========================
    # CONFIABILIDADE
    # =========================

    if pontos_validos >= 30:

        if valor_absoluto >= 0.50:
            confiabilidade = "ALTA"
        else:
            confiabilidade = "MODERADA"

    elif pontos_validos >= 15:

        if valor_absoluto >= 0.50:
            confiabilidade = "MODERADA"
        else:
            confiabilidade = "BAIXA"

    else:

        confiabilidade = "BAIXA"

    return {
        "correlacao": round(
            correlacao,
            3
        ),
        "classificacao": classificacao,
        "direcao": direcao,
        "confiabilidade": confiabilidade,
        "pontos_validos": pontos_validos
    }

def gerar_ranking_correlacoes(
    historico_principal,
    historicos_comparacao,
    nome_principal="variavel_principal"
):

    ranking = []

    for nome_variavel, historico_variavel in historicos_comparacao.items():

        try:

            alinhado = alinhar_series(
                historico_principal,
                historico_variavel,
                nome_a=nome_principal,
                nome_b=nome_variavel
            )

            resultado = calcular_correlacao(
                alinhado,
                nome_a=nome_principal,
                nome_b=nome_variavel
            )

            ranking.append({
                "variavel": nome_variavel,
                "correlacao": resultado["correlacao"],
                "direcao": resultado["direcao"],
                "classificacao": resultado["classificacao"],
                "confiabilidade": resultado["confiabilidade"],
                "pontos_validos": resultado["pontos_validos"]
            })

        except Exception:

            continue

    ranking = pd.DataFrame(
        ranking
    )

    if ranking.empty:
        return ranking

    ranking["correlacao_abs"] = (
        ranking["correlacao"]
        .abs()
    )

    ranking = ranking.sort_values(
        "correlacao_abs",
        ascending=False
    )

    ranking = ranking.drop(
        columns=["correlacao_abs"]
    )

    ranking = ranking.reset_index(
        drop=True
    )

    return ranking