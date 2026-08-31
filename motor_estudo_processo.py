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

            tipo_relacao = classificar_tipo_relacao(
                nome_principal,
                nome_variavel
            )

            prioridade = calcular_prioridade_investigacao(
                tipo_relacao=tipo_relacao,
                correlacao=resultado[
                    "correlacao"
                ],
                confiabilidade=resultado[
                    "confiabilidade"
                ],
                pontos_validos=resultado[
                    "pontos_validos"
                ]
            )

            ranking.append({
                "variavel": nome_variavel,

                "tipo_variavel": classificar_tipo_variavel(
                    nome_variavel
                ),

                "categoria_engenharia": classificar_categoria_engenharia(
                    nome_variavel
                ),

                "tipo_relacao": tipo_relacao,

                "correlacao": resultado[
                    "correlacao"
                ],

                "direcao": resultado[
                    "direcao"
                ],

                "classificacao": resultado[
                    "classificacao"
                ],

                "confiabilidade": resultado[
                    "confiabilidade"
                ],

                "pontos_validos": resultado[
                    "pontos_validos"
                ],

                "score_prioridade": prioridade[
                    "score_prioridade"
                ],

                "prioridade_investigacao": prioridade[
                    "prioridade_investigacao"
                ]
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
    resultado_defasagem,
    nome_principal="Variável principal",
    nome_comparacao="Variável de comparação"
):

    dados = resultado_defasagem.copy()

    dados["correlacao"] = pd.to_numeric(
        dados["correlacao"],
        errors="coerce"
    )

    dados_validos = dados.dropna(
        subset=["correlacao"]
    ).copy()

    if dados_validos.empty:

        return {
            "melhor_defasagem": None,
            "melhor_correlacao": None,
            "correlacao_base": None,
            "ganho_correlacao": None,
            "pontos_validos": 0,
            "relevancia": "NÃO AVALIADA",
            "direcao_temporal": "Não foi possível determinar",
            "interpretacao": (
                "Não foi possível identificar uma "
                "associação temporal válida."
            )
        }

    dados_validos["correlacao_abs"] = (
        dados_validos["correlacao"].abs()
    )

    melhor_linha = dados_validos.loc[
        dados_validos["correlacao_abs"].idxmax()
    ]

    melhor_defasagem = int(
        melhor_linha["defasagem_minutos"]
    )

    melhor_correlacao = float(
        melhor_linha["correlacao"]
    )

    pontos_validos = int(
        melhor_linha["pontos_validos"]
    )

    linha_base = dados_validos[
        dados_validos["defasagem_minutos"] == 0
    ]

    if linha_base.empty:

        correlacao_base = None
        ganho_correlacao = None

    else:

        correlacao_base = float(
            linha_base.iloc[0]["correlacao"]
        )

        ganho_correlacao = round(
            abs(melhor_correlacao)
            - abs(correlacao_base),
            3
        )

    if (
        abs(melhor_correlacao) >= 0.70
        and ganho_correlacao is not None
        and ganho_correlacao >= 0.15
        and pontos_validos >= 30
    ):

        relevancia = "ALTA"

    elif (
        abs(melhor_correlacao) >= 0.50
        and ganho_correlacao is not None
        and ganho_correlacao >= 0.10
        and pontos_validos >= 20
    ):

        relevancia = "MODERADA"

    elif (
        abs(melhor_correlacao) >= 0.30
        and ganho_correlacao is not None
        and ganho_correlacao >= 0.05
    ):

        relevancia = "BAIXA"

    else:

        relevancia = "MUITO BAIXA"

    # --------------------------------------------------
    # INTERPRETAÇÃO DA DIREÇÃO TEMPORAL
    # --------------------------------------------------

    if melhor_defasagem == 0:

        direcao_temporal = (
            f"{nome_principal} e {nome_comparacao} "
            "apresentam maior associação sem "
            "defasagem temporal."
        )

    elif melhor_defasagem < 0:

        minutos = abs(
            melhor_defasagem
        )

        direcao_temporal = (
            f"{nome_principal} antecede "
            f"{nome_comparacao} em aproximadamente "
            f"{minutos} minutos."
        )

    else:

        minutos = abs(
            melhor_defasagem
        )

        direcao_temporal = (
            f"{nome_comparacao} antecede "
            f"{nome_principal} em aproximadamente "
            f"{minutos} minutos."
        )

    # --------------------------------------------------
    # TEXTO DE INTERPRETAÇÃO
    # --------------------------------------------------

    if melhor_defasagem == 0:

        interpretacao = (
            f"A maior associação entre "
            f"{nome_principal} e {nome_comparacao} "
            f"ocorreu sem deslocamento temporal, "
            f"com correlação {melhor_correlacao:.3f}. "
            "Não foi identificada evidência de uma "
            "defasagem temporal relevante."
        )

    elif relevancia in [
        "ALTA",
        "MODERADA"
    ]:

        interpretacao = (
            f"{direcao_temporal} "
            f"A correlação máxima foi "
            f"{melhor_correlacao:.3f}"
        )

        if correlacao_base is not None:

            interpretacao += (
                f", comparada a "
                f"{correlacao_base:.3f} "
                "sem defasagem"
            )

        interpretacao += (
            ". A associação temporal merece "
            "investigação de engenharia, mas não "
            "representa evidência de causalidade."
        )

    else:

        interpretacao = (
            f"A maior associação ocorreu com "
            f"defasagem de {melhor_defasagem} minutos, "
            f"com correlação {melhor_correlacao:.3f}. "
            f"{direcao_temporal} "
            f"Entretanto, a evidência temporal foi "
            f"classificada como {relevancia}. "
            "O resultado isolado não é suficiente "
            "para indicar uma relação temporal relevante."
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
        "direcao_temporal": direcao_temporal,
        "interpretacao": interpretacao
    }

def gerar_teste_defasagem_conhecida():

    datas = pd.date_range(
        start="2026-01-01 00:00:00",
        periods=20,
        freq="10min"
    )

    valores_base = list(
        range(20)
    )

    principal = pd.DataFrame({
        "data_hora": datas,
        "valor": valores_base
    })

    comparacao = pd.DataFrame({
        "data_hora": datas + pd.Timedelta(
            minutes=30
        ),
        "valor": valores_base
    })

    principal = preparar_historico(
        principal
    )

    comparacao = preparar_historico(
        comparacao
    )

    resultado = analisar_defasagem(
        principal,
        comparacao,
        nome_principal="principal",
        nome_comparacao="comparacao"
    )

    return resultado

def classificar_tipo_variavel(
    nome_variavel
):

    nome = str(
        nome_variavel
    ).lower()

    # --------------------------------------------------
    # STATUS / ESTADO OPERACIONAL
    # --------------------------------------------------

    termos_status = [
        "status",
        "estado",
        "modo"
    ]

    if any(
        termo in nome
        for termo in termos_status
    ):

        return "STATUS/ESTADO"

    # --------------------------------------------------
    # KPI
    # --------------------------------------------------

    termos_kpi = [
        "kpi",
        "produtividade",
        "disponibilidade"
    ]

    if any(
        termo in nome
        for termo in termos_kpi
    ):

        return "KPI"

    # --------------------------------------------------
    # VARIÁVEIS FÍSICAS DE PROCESSO
    #
    # A prioridade aqui é proposital.
    # "Corrente Média", por exemplo, continua sendo
    # tratada como uma variável física de processo.
    # --------------------------------------------------

    termos_medida = [
        "vazão",
        "vazao",
        "pressão",
        "pressao",
        "nível",
        "nivel",
        "temperatura",
        "corrente",
        "tensão",
        "tensao",
        "potência",
        "potencia",
        "ph"
    ]

    if any(
        termo in nome
        for termo in termos_medida
    ):

        return "MEDIDA"

    # --------------------------------------------------
    # VARIÁVEIS CALCULADAS / DERIVADAS
    # --------------------------------------------------

    termos_calculados = [
        "diferencial",
        "totalizador",
        "cálculo",
        "calculo",
        "modelo",
        "estimado",
        "estimada"
    ]

    if any(
        termo in nome
        for termo in termos_calculados
    ):

        return "CALCULADA"

    # --------------------------------------------------
    # FALLBACK
    # --------------------------------------------------

    return "NÃO CLASSIFICADA"

def classificar_tipo_relacao(
    nome_principal,
    nome_comparacao
):

    tipo_principal = classificar_tipo_variavel(
        nome_principal
    )

    tipo_comparacao = classificar_tipo_variavel(
        nome_comparacao
    )

    # Relação entre duas variáveis físicas
    if (
        tipo_principal == "MEDIDA"
        and tipo_comparacao == "MEDIDA"
    ):

        return "RELAÇÃO DE PROCESSO"

    # Relações envolvendo KPI
    if (
        tipo_principal == "KPI"
        or tipo_comparacao == "KPI"
    ):

        return "RELAÇÃO DERIVADA / KPI"

    # Relações envolvendo variáveis calculadas
    if (
        tipo_principal == "CALCULADA"
        or tipo_comparacao == "CALCULADA"
    ):

        return "RELAÇÃO CALCULADA"

    # Estado operacional pode explicar mudanças
    if (
        tipo_principal == "STATUS/ESTADO"
        or tipo_comparacao == "STATUS/ESTADO"
    ):

        return "RELAÇÃO OPERACIONAL"

    return "RELAÇÃO NÃO CLASSIFICADA"

def calcular_prioridade_investigacao(
    tipo_relacao,
    correlacao,
    confiabilidade,
    pontos_validos
):
    """
    Calcula a prioridade de investigação de engenharia.

    A correlação funciona como um limitador da prioridade:
    relações estatisticamente muito fracas não podem receber
    prioridade alta apenas por serem relações físicas ou
    possuírem muitos pontos válidos.
    """

    # ======================================================
    # VALIDAR CORRELAÇÃO
    # ======================================================

    try:
        correlacao = float(correlacao)

        if pd.isna(correlacao):
            raise ValueError

    except (TypeError, ValueError):

        return {
            "score_prioridade": 0,
            "prioridade_investigacao": "NÃO AVALIADA"
        }

    correlacao_abs = abs(correlacao)

    # ======================================================
    # PESO DO TIPO DE RELAÇÃO
    # ======================================================

    pesos_relacao = {
        "RELAÇÃO DE PROCESSO": 40,
        "RELAÇÃO OPERACIONAL": 30,
        "RELAÇÃO CALCULADA": 15,
        "RELAÇÃO DERIVADA / KPI": 5,
        "RELAÇÃO NÃO CLASSIFICADA": 10,
    }

    score = pesos_relacao.get(
        tipo_relacao,
        10
    )

    # ======================================================
    # PESO DA CORRELAÇÃO
    # ======================================================

    if correlacao_abs >= 0.80:
        score += 30

    elif correlacao_abs >= 0.50:
        score += 22

    elif correlacao_abs >= 0.30:
        score += 14

    elif correlacao_abs >= 0.10:
        score += 6

    # ======================================================
    # PESO DA CONFIABILIDADE
    # ======================================================

    pesos_confiabilidade = {
        "ALTA": 20,
        "MODERADA": 12,
        "BAIXA": 5,
    }

    score += pesos_confiabilidade.get(
        confiabilidade,
        0
    )

    # ======================================================
    # PESO DA QUANTIDADE DE DADOS
    # ======================================================

    if pontos_validos >= 100:
        score += 10

    elif pontos_validos >= 30:
        score += 7

    elif pontos_validos >= 15:
        score += 3

    # ======================================================
    # LIMITADORES ESTATÍSTICOS
    # ======================================================
    #
    # Uma relação física pode ser interessante para
    # investigação, mas correlação muito baixa não deve
    # receber prioridade elevada somente pelo contexto.
    # ======================================================

    if correlacao_abs < 0.10:

        prioridade = "MUITO BAIXA"

    elif correlacao_abs < 0.30:

        prioridade = "BAIXA"

    elif correlacao_abs < 0.50:

        if score >= 55:
            prioridade = "MODERADA"
        else:
            prioridade = "BAIXA"

    else:

        if score >= 70:
            prioridade = "ALTA"

        elif score >= 55:
            prioridade = "MODERADA"

        elif score >= 35:
            prioridade = "BAIXA"

        else:
            prioridade = "MUITO BAIXA"

    return {
        "score_prioridade": int(score),
        "prioridade_investigacao": prioridade
    }

def classificar_categoria_engenharia(
    nome_variavel
):

    nome = str(
        nome_variavel
    ).lower()

    # --------------------------------------------------
    # ELÉTRICA
    # --------------------------------------------------

    termos_eletrica = [
        "corrente",
        "tensão",
        "tensao",
        "potência",
        "potencia",
        "frequência",
        "frequencia",
        "fator de potência",
        "fator de potencia"
    ]

    if any(
        termo in nome
        for termo in termos_eletrica
    ):

        return "ELÉTRICA"

    # --------------------------------------------------
    # DIFERENCIAIS ELÉTRICOS CALCULADOS
    # Ex.: Diferencial R-S, R-T, S-T
    # --------------------------------------------------

    if "diferencial" in nome:

        fases_eletricas = [
            "r-s",
            "r-t",
            "s-t"
        ]

        if any(
            fase in nome
            for fase in fases_eletricas
        ):

            return "ELÉTRICA"

    # --------------------------------------------------
    # TÉRMICA
    # --------------------------------------------------

    termos_termica = [
        "temperatura",
        "térmica",
        "termica"
    ]

    if any(
        termo in nome
        for termo in termos_termica
    ):

        return "TÉRMICA"

    # --------------------------------------------------
    # PROCESSO
    # --------------------------------------------------

    termos_processo = [
        "vazão",
        "vazao",
        "pressão",
        "pressao",
        "nível",
        "nivel",
        "ph",
        "volume"
    ]

    if any(
        termo in nome
        for termo in termos_processo
    ):

        return "PROCESSO"

    # --------------------------------------------------
    # ESTADO OPERACIONAL
    # --------------------------------------------------

    termos_estado = [
        "status",
        "estado",
        "modo"
    ]

    if any(
        termo in nome
        for termo in termos_estado
    ):

        return "ESTADO OPERACIONAL"

    # --------------------------------------------------
    # KPI
    # --------------------------------------------------

    termos_kpi = [
        "kpi",
        "produtividade",
        "disponibilidade",
        "eficiência",
        "eficiencia"
    ]

    if any(
        termo in nome
        for termo in termos_kpi
    ):

        return "KPI"

    # --------------------------------------------------
    # NÃO CLASSIFICADA
    # --------------------------------------------------

    return "NÃO CLASSIFICADA"
