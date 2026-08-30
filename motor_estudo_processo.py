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

def analisar_defasagem(
    historico_principal,
    historico_comparacao,
    nome_principal="variavel_principal",
    nome_comparacao="variavel_comparacao",
    defasagens_minutos=(
        -120,
        -90,
        -60,
        -30,
        0,
        30,
        60,
        90,
        120
    ),
    tolerancia="30min",
    minimo_pontos=10
):

    # =========================
    # PREPARAÇÃO DAS SÉRIES
    # =========================

    principal = historico_principal[
        [
            "data_hora",
            "valor_numerico"
        ]
    ].copy()

    principal = principal.rename(
        columns={
            "valor_numerico": nome_principal
        }
    )

    comparacao = historico_comparacao[
        [
            "data_hora",
            "valor_numerico"
        ]
    ].copy()

    comparacao = comparacao.rename(
        columns={
            "valor_numerico": nome_comparacao
        }
    )

    principal["data_hora"] = pd.to_datetime(
        principal["data_hora"],
        errors="coerce"
    )

    comparacao["data_hora"] = pd.to_datetime(
        comparacao["data_hora"],
        errors="coerce"
    )

    principal[nome_principal] = pd.to_numeric(
        principal[nome_principal],
        errors="coerce"
    )

    comparacao[nome_comparacao] = pd.to_numeric(
        comparacao[nome_comparacao],
        errors="coerce"
    )

    principal = principal.dropna(
        subset=[
            "data_hora",
            nome_principal
        ]
    )

    comparacao = comparacao.dropna(
        subset=[
            "data_hora",
            nome_comparacao
        ]
    )

    principal = principal.sort_values(
        "data_hora"
    )

    comparacao = comparacao.sort_values(
        "data_hora"
    )

    # =========================
    # TESTE DAS DEFASAGENS
    # =========================

    resultados = []

    for minutos in defasagens_minutos:

        comparacao_deslocada = (
            comparacao.copy()
        )

        comparacao_deslocada[
            "data_hora"
        ] = (
            comparacao_deslocada[
                "data_hora"
            ]
            + pd.Timedelta(
                minutes=minutos
            )
        )

        alinhado = pd.merge_asof(
            principal,
            comparacao_deslocada,
            on="data_hora",
            direction="nearest",
            tolerance=pd.Timedelta(
                tolerancia
            )
        )

        alinhado = alinhado.dropna(
            subset=[
                nome_principal,
                nome_comparacao
            ]
        )

        pontos_validos = len(
            alinhado
        )

        correlacao = None
        status = "DADOS INSUFICIENTES"

        if pontos_validos >= minimo_pontos:

            desvio_principal = alinhado[
                nome_principal
            ].std()

            desvio_comparacao = alinhado[
                nome_comparacao
            ].std()

            if (
                desvio_principal == 0
                or desvio_comparacao == 0
                or pd.isna(desvio_principal)
                or pd.isna(desvio_comparacao)
            ):

                status = "SEM VARIAÇÃO"

            else:

                valor_correlacao = alinhado[
                    nome_principal
                ].corr(
                    alinhado[
                        nome_comparacao
                    ]
                )

                if pd.isna(
                    valor_correlacao
                ):

                    status = "NÃO CALCULÁVEL"

                else:

                    correlacao = round(
                        float(
                            valor_correlacao
                        ),
                        3
                    )

                    status = "OK"

        resultados.append({
            "defasagem_minutos": minutos,
            "correlacao": correlacao,
            "pontos_validos": pontos_validos,
            "status": status
        })

    return pd.DataFrame(
        resultados
    )

def interpretar_defasagem(
    resultado_defasagem
):

    if resultado_defasagem.empty:

        return {
            "melhor_defasagem": None,
            "melhor_correlacao": None,
            "correlacao_base": None,
            "ganho_correlacao": None,
            "relevancia": "SEM DADOS",
            "interpretacao": (
                "Não existem dados suficientes "
                "para avaliar a relação temporal."
            )
        }

    dados = resultado_defasagem.copy()

    dados["correlacao"] = pd.to_numeric(
        dados["correlacao"],
        errors="coerce"
    )

    dados_validos = dados.dropna(
        subset=["correlacao"]
    )

    if dados_validos.empty:

        return {
            "melhor_defasagem": None,
            "melhor_correlacao": None,
            "correlacao_base": None,
            "ganho_correlacao": None,
            "relevancia": "NÃO CALCULÁVEL",
            "interpretacao": (
                "Não foi possível calcular uma "
                "associação temporal válida."
            )
        }

    # =========================
    # CORRELAÇÃO SEM DEFASAGEM
    # =========================

    linha_base = dados_validos[
        dados_validos[
            "defasagem_minutos"
        ] == 0
    ]

    if linha_base.empty:

        correlacao_base = None

    else:

        correlacao_base = float(
            linha_base.iloc[0][
                "correlacao"
            ]
        )

    # =========================
    # MELHOR ASSOCIAÇÃO
    # =========================

    dados_validos[
        "correlacao_abs"
    ] = dados_validos[
        "correlacao"
    ].abs()

    indice_melhor = dados_validos[
        "correlacao_abs"
    ].idxmax()

    melhor = dados_validos.loc[
        indice_melhor
    ]

    melhor_defasagem = int(
        melhor[
            "defasagem_minutos"
        ]
    )

    melhor_correlacao = float(
        melhor[
            "correlacao"
        ]
    )

    pontos_validos = int(
        melhor[
            "pontos_validos"
        ]
    )

    # =========================
    # GANHO SOBRE O TEMPO ZERO
    # =========================

    if correlacao_base is None:

        ganho_correlacao = None

    else:

        ganho_correlacao = (
            abs(melhor_correlacao)
            - abs(correlacao_base)
        )

        ganho_correlacao = round(
            ganho_correlacao,
            3
        )

    # =========================
    # RELEVÂNCIA TEMPORAL
    # =========================

    forca = abs(
        melhor_correlacao
    )

    if (
        forca >= 0.70
        and ganho_correlacao is not None
        and ganho_correlacao >= 0.15
        and pontos_validos >= 30
    ):

        relevancia = "ALTA"

    elif (
        forca >= 0.50
        and ganho_correlacao is not None
        and ganho_correlacao >= 0.10
        and pontos_validos >= 20
    ):

        relevancia = "MODERADA"

    elif (
        forca >= 0.30
        and ganho_correlacao is not None
        and ganho_correlacao >= 0.05
    ):

        relevancia = "BAIXA"

    else:

        relevancia = "MUITO BAIXA"

    # =========================
    # INTERPRETAÇÃO
    # =========================

    if melhor_defasagem == 0:

        interpretacao = (
            "A maior associação foi observada "
            "sem deslocamento temporal. "
            "Não foi identificada evidência de "
            "defasagem relevante."
        )

    elif relevancia in [
        "ALTA",
        "MODERADA"
    ]:

        interpretacao = (
            f"Foi observada uma associação temporal "
            f"mais relevante em {melhor_defasagem} minutos. "
            f"A correlação passou de "
            f"{correlacao_base} no tempo zero para "
            f"{round(melhor_correlacao, 3)}. "
            f"Esse resultado indica uma relação temporal "
            f"que merece investigação de engenharia, "
            f"mas não comprova causalidade."
        )

    else:

        interpretacao = (
            f"A maior associação ocorreu em "
            f"{melhor_defasagem} minutos, com correlação "
            f"{round(melhor_correlacao, 3)}. "
            f"Entretanto, a evidência temporal foi "
            f"classificada como {relevancia}. "
            f"O resultado isolado não é suficiente para "
            f"indicar uma relação temporal relevante."
        )

    return {
        "melhor_defasagem": melhor_defasagem,
        "melhor_correlacao": round(
            melhor_correlacao,
            3
        ),
        "correlacao_base": (
            round(
                correlacao_base,
                3
            )
            if correlacao_base is not None
            else None
        ),
        "ganho_correlacao": ganho_correlacao,
        "pontos_validos": pontos_validos,
        "relevancia": relevancia,
        "interpretacao": interpretacao
    }