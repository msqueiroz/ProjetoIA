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

            relevancia = classificar_relevancia_engenharia(
                nome_variavel
            )

            ranking.append({

                "variavel":
                    nome_variavel,

                "tipo_variavel":
                    classificar_tipo_variavel(
                        nome_variavel
                    ),

                "categoria_engenharia":
                    classificar_categoria_engenharia(
                        nome_variavel
                    ),

                "tipo_relacao":
                    tipo_relacao,

                "correlacao":
                    resultado[
                        "correlacao"
                    ],

                "direcao":
                    resultado[
                        "direcao"
                    ],

                "classificacao":
                    resultado[
                        "classificacao"
                    ],

                "confiabilidade":
                    resultado[
                        "confiabilidade"
                    ],

                "pontos_validos":
                    resultado[
                        "pontos_validos"
                    ],

                "score_prioridade":
                    prioridade[
                        "score_prioridade"
                    ],

                "prioridade_investigacao":
                    prioridade[
                        "prioridade_investigacao"
                    ],

                "relevancia_engenharia":
                    relevancia[
                        "relevancia_engenharia"
                    ],

                "peso_relevancia":
                    relevancia[
                        "peso_relevancia"
                    ],

            })

        except Exception:

            continue

    ranking = pd.DataFrame(
        ranking
    )

    if ranking.empty:
        return ranking

    ranking["correlacao_abs"] = (
        pd.to_numeric(
            ranking["correlacao"],
            errors="coerce"
        ).abs()
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
    defasagens_minutos=None,
    tolerancia="30min",
    minimo_pontos=10,
    janela_ampla_horas=24,
    passo_amplo_minutos=60,
    janela_refino_minutos=120,
    passo_refino_minutos=15
):
    """
    Analisa defasagem temporal entre duas séries.

    Estratégia padrão multiescala:
    1. Busca ampla entre -janela_ampla_horas e
       +janela_ampla_horas, usando passo horário.
    2. Identifica a melhor região pela correlação absoluta.
    3. Refina ao redor dessa região com passo menor.

    Convenção de sinal preservada:
    - defasagem > 0:
        variável de comparação antecede a principal.
    - defasagem < 0:
        variável principal antecede a comparação.
    - defasagem = 0:
        associação simultânea.

    Se defasagens_minutos for informado explicitamente,
    a função usa somente esses deslocamentos e não executa
    o refinamento automático.
    """

    # ======================================================
    # PREPARAÇÃO DAS SÉRIES
    # ======================================================

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

    principal = (
        principal
        .dropna(
            subset=[
                "data_hora",
                nome_principal
            ]
        )
        .sort_values("data_hora")
        .reset_index(drop=True)
    )

    comparacao = (
        comparacao
        .dropna(
            subset=[
                "data_hora",
                nome_comparacao
            ]
        )
        .sort_values("data_hora")
        .reset_index(drop=True)
    )

    # ======================================================
    # FUNÇÃO INTERNA DE AVALIAÇÃO
    # ======================================================

    def avaliar_deslocamentos(
        lista_defasagens,
        etapa
    ):

        resultados = []

        for minutos in lista_defasagens:

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
                    minutes=int(minutos)
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
                "defasagem_minutos":
                    int(minutos),
                "correlacao":
                    correlacao,
                "pontos_validos":
                    pontos_validos,
                "status":
                    status,
                "etapa_busca":
                    etapa
            })

        return pd.DataFrame(
            resultados
        )

    # ======================================================
    # MODO EXPLÍCITO
    # ======================================================

    if defasagens_minutos is not None:

        return avaliar_deslocamentos(
            list(
                defasagens_minutos
            ),
            etapa="EXPLICITA"
        )

    # ======================================================
    # 1. BUSCA AMPLA
    # ======================================================

    limite_amplo = int(
        janela_ampla_horas
        * 60
    )

    defasagens_amplas = list(
        range(
            -limite_amplo,
            limite_amplo + 1,
            int(
                passo_amplo_minutos
            )
        )
    )

    resultado_amplo = (
        avaliar_deslocamentos(
            defasagens_amplas,
            etapa="AMPLA"
        )
    )

    validos_amplos = (
        resultado_amplo
        .dropna(
            subset=[
                "correlacao"
            ]
        )
        .copy()
    )

    if validos_amplos.empty:

        return resultado_amplo

    validos_amplos[
        "_correlacao_abs"
    ] = (
        validos_amplos[
            "correlacao"
        ].abs()
    )

    melhor_amplo = int(
        validos_amplos.loc[
            validos_amplos[
                "_correlacao_abs"
            ].idxmax(),
            "defasagem_minutos"
        ]
    )

    # ======================================================
    # 2. REFINAMENTO
    # ======================================================

    inicio_refino = max(
        -limite_amplo,
        melhor_amplo
        - int(
            janela_refino_minutos
        )
    )

    fim_refino = min(
        limite_amplo,
        melhor_amplo
        + int(
            janela_refino_minutos
        )
    )

    defasagens_refino = list(
        range(
            inicio_refino,
            fim_refino + 1,
            int(
                passo_refino_minutos
            )
        )
    )

    resultado_refino = (
        avaliar_deslocamentos(
            defasagens_refino,
            etapa="REFINO"
        )
    )

    # ======================================================
    # CONSOLIDA, PRIORIZANDO O REFINO NOS DUPLICADOS
    # ======================================================

    resultado = pd.concat(
        [
            resultado_amplo,
            resultado_refino
        ],
        ignore_index=True
    )

    prioridade_etapa = {
        "AMPLA": 1,
        "REFINO": 2
    }

    resultado[
        "_prioridade_etapa"
    ] = resultado[
        "etapa_busca"
    ].map(
        prioridade_etapa
    ).fillna(0)

    resultado = (
        resultado
        .sort_values(
            [
                "defasagem_minutos",
                "_prioridade_etapa"
            ],
            ascending=[
                True,
                False
            ]
        )
        .drop_duplicates(
            subset=[
                "defasagem_minutos"
            ],
            keep="first"
        )
        .drop(
            columns=[
                "_prioridade_etapa"
            ]
        )
        .sort_values(
            "defasagem_minutos"
        )
        .reset_index(
            drop=True
        )
    )

    return resultado


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


def calcular_score_evidencia_temporal(
    melhor_correlacao,
    correlacao_base,
    ganho_correlacao,
    pontos_validos,
    melhor_defasagem
):
    """
    Calcula um score de evidência temporal de 0 a 100.

    O score combina:
    - força da correlação na melhor defasagem;
    - quantidade de pares válidos;
    - ganho em relação à correlação sem defasagem;
    - direção temporal.

    A direção é tratada como requisito para investigação
    antecipatória:
    - defasagem > 0: candidata antecede a principal;
    - defasagem = 0: associação simultânea;
    - defasagem < 0: direção inversa.

    O score não representa causalidade.
    """

    try:
        corr = abs(
            float(
                melhor_correlacao
            )
        )
    except (TypeError, ValueError):
        corr = 0.0

    try:
        ganho = max(
            float(
                ganho_correlacao
            ),
            0.0
        )
    except (TypeError, ValueError):
        ganho = 0.0

    try:
        pontos = int(
            pontos_validos
        )
    except (TypeError, ValueError):
        pontos = 0

    try:
        defasagem = int(
            melhor_defasagem
        )
    except (TypeError, ValueError):
        defasagem = 0

    # --------------------------------------------------
    # FORÇA DA CORRELAÇÃO: até 35 pontos
    # --------------------------------------------------

    if corr >= 0.80:
        score_correlacao = 35
    elif corr >= 0.60:
        score_correlacao = 28
    elif corr >= 0.40:
        score_correlacao = 20
    elif corr >= 0.30:
        score_correlacao = 12
    else:
        score_correlacao = 5

    # --------------------------------------------------
    # QUANTIDADE DE DADOS: até 35 pontos
    # --------------------------------------------------

    if pontos >= 100:
        score_pontos = 35
    elif pontos >= 50:
        score_pontos = 28
    elif pontos >= 30:
        score_pontos = 22
    elif pontos >= 20:
        score_pontos = 16
    elif pontos >= 15:
        score_pontos = 10
    elif pontos >= 10:
        score_pontos = 5
    else:
        score_pontos = 0

    # --------------------------------------------------
    # GANHO COM A DEFASAGEM: até 20 pontos
    # --------------------------------------------------

    if ganho >= 0.20:
        score_ganho = 20
    elif ganho >= 0.15:
        score_ganho = 16
    elif ganho >= 0.10:
        score_ganho = 12
    elif ganho >= 0.05:
        score_ganho = 8
    elif ganho > 0:
        score_ganho = 3
    else:
        score_ganho = 0

    # --------------------------------------------------
    # DIREÇÃO TEMPORAL: até 10 pontos
    # --------------------------------------------------

    if defasagem > 0:
        score_direcao = 10
        direcao = "ANTECIPA A PRINCIPAL"
    elif defasagem == 0:
        score_direcao = 3
        direcao = "SIMULTÂNEA"
    else:
        score_direcao = 0
        direcao = "DIREÇÃO INVERSA"

    score_total = (
        score_correlacao
        + score_pontos
        + score_ganho
        + score_direcao
    )

    # Penalização forte quando há poucos pares válidos.
    if pontos < 15:
        score_total = min(
            score_total,
            59
        )

    # Relação simultânea ou inversa não pode ser classificada
    # como evidência temporal forte para antecipação.
    if defasagem <= 0:
        score_total = min(
            score_total,
            49
        )

    if score_total >= 80:
        classificacao = "FORTE"
    elif score_total >= 60:
        classificacao = "MODERADA"
    elif score_total >= 40:
        classificacao = "BAIXA"
    else:
        classificacao = "MUITO BAIXA"

    return {
        "score_evidencia_temporal":
            int(
                score_total
            ),
        "classificacao_evidencia_temporal":
            classificacao,
        "direcao_temporal":
            direcao,
        "score_correlacao":
            score_correlacao,
        "score_pontos":
            score_pontos,
        "score_ganho":
            score_ganho,
        "score_direcao":
            score_direcao,
    }



def gerar_hipotese_engenharia_temporal(
    variavel_principal,
    variavel_candidata,
    defasagem_texto,
    melhor_correlacao,
    correlacao_base,
    ganho_correlacao,
    pontos_validos,
    score_evidencia_temporal,
    classificacao_evidencia_temporal,
    direcao_temporal
):
    """
    Gera uma hipótese de investigação de engenharia a partir
    de evidências estatísticas e temporais já calculadas.

    A função é determinística e não afirma causalidade.
    Ela organiza:
    - hipótese;
    - evidências;
    - verificações sugeridas;
    - limitações.
    """

    nome = str(
        variavel_candidata
    ).lower()

    # --------------------------------------------------
    # FOCO DE VERIFICAÇÃO POR SEMÂNTICA DA VARIÁVEL
    # --------------------------------------------------

    verificacoes = []

    if any(
        termo in nome
        for termo in [
            "cot",
            "dqo",
            "dbo",
            "carga"
        ]
    ):
        verificacoes.extend([
            "Verificar coerência entre carga orgânica, vazão e concentração na entrada.",
            "Comparar o comportamento entre os diferentes tanques/aerados do processo.",
            "Avaliar se a defasagem observada é compatível com transporte e tempo de retenção do sistema.",
        ])

    if any(
        termo in nome
        for termo in [
            "nh3",
            "n-nh3",
            "nnh3",
            "amônia",
            "amonia",
            "nitrogênio",
            "nitrogenio"
        ]
    ):
        verificacoes.extend([
            "Comparar NH3 de entrada e saída no mesmo intervalo operacional.",
            "Avaliar condições relacionadas à nitrificação, incluindo aeração e oxigênio dissolvido.",
        ])

    if any(
        termo in nome
        for termo in [
            "aerador",
            "ligado",
            "status",
            "estado"
        ]
    ):
        verificacoes.extend([
            "Verificar quantidade e combinação de aeradores em operação.",
            "Comparar períodos com mudança de estado operacional antes da resposta na variável principal.",
        ])

    if any(
        termo in nome
        for termo in [
            "vazão",
            "vazao"
        ]
    ):
        verificacoes.extend([
            "Avaliar impacto da vazão sobre carga aplicada e tempo de retenção.",
            "Verificar se mudanças de vazão antecedem alterações de qualidade no efluente.",
        ])

    if any(
        termo in nome
        for termo in [
            "oxigênio dissolvido",
            "oxigenio dissolvido",
            " od"
        ]
    ):
        verificacoes.extend([
            "Avaliar disponibilidade de oxigênio no período anterior à alteração da variável principal.",
            "Comparar oxigênio dissolvido com estado dos aeradores e carga aplicada.",
        ])

    if any(
        termo in nome
        for termo in [
            "temperatura",
            "ph"
        ]
    ):
        verificacoes.append(
            "Verificar se a condição físico-química permaneceu em faixa operacional compatível no período analisado."
        )

    # Sempre mantém verificações gerais.
    verificacoes.extend([
        "Confirmar a qualidade e a representatividade temporal das duas séries.",
        "Repetir a análise em outra janela de tempo antes de concluir que o padrão é recorrente.",
    ])

    # Remove duplicatas preservando a ordem.
    verificacoes_unicas = []

    for item in verificacoes:
        if item not in verificacoes_unicas:
            verificacoes_unicas.append(
                item
            )

    # --------------------------------------------------
    # EVIDÊNCIAS
    # --------------------------------------------------

    evidencias = [
        (
            f"Correlação máxima com defasagem: "
            f"{float(melhor_correlacao):.3f}."
        ),
        (
            f"Defasagem observada: "
            f"{defasagem_texto}."
        ),
        (
            f"Pares válidos na melhor defasagem: "
            f"{int(pontos_validos)}."
        ),
        (
            f"Score de evidência temporal: "
            f"{int(score_evidencia_temporal)}/100 "
            f"({classificacao_evidencia_temporal})."
        ),
    ]

    if (
        correlacao_base is not None
        and not pd.isna(
            correlacao_base
        )
    ):
        evidencias.append(
            (
                f"Correlação sem defasagem: "
                f"{float(correlacao_base):.3f}."
            )
        )

    if (
        ganho_correlacao is not None
        and not pd.isna(
            ganho_correlacao
        )
    ):
        evidencias.append(
            (
                f"Ganho absoluto de correlação com a defasagem: "
                f"{float(ganho_correlacao):.3f}."
            )
        )

    # --------------------------------------------------
    # HIPÓTESE
    # --------------------------------------------------

    if direcao_temporal == "ANTECIPA A PRINCIPAL":

        hipotese = (
            f"Alterações em {variavel_candidata} apresentam "
            f"evidência temporal {str(classificacao_evidencia_temporal).lower()} "
            f"de antecedência em relação a {variavel_principal}, "
            f"com defasagem aproximada de "
            f"{str(defasagem_texto).replace('+', '')}."
        )

    elif direcao_temporal == "SIMULTÂNEA":

        hipotese = (
            f"{variavel_candidata} e {variavel_principal} "
            "apresentam associação predominantemente simultânea "
            "na janela analisada, sem evidência de antecedência."
        )

    else:

        hipotese = (
            f"A associação temporal entre {variavel_candidata} "
            f"e {variavel_principal} ocorre em direção inversa "
            "à necessária para uso como indicador antecipador."
        )

    # --------------------------------------------------
    # PRIORIDADE DA HIPÓTESE
    # --------------------------------------------------

    if (
        direcao_temporal == "ANTECIPA A PRINCIPAL"
        and score_evidencia_temporal >= 80
    ):
        prioridade = "ALTA"

    elif (
        direcao_temporal == "ANTECIPA A PRINCIPAL"
        and score_evidencia_temporal >= 60
    ):
        prioridade = "MODERADA"

    elif (
        direcao_temporal == "ANTECIPA A PRINCIPAL"
        and score_evidencia_temporal >= 40
    ):
        prioridade = "BAIXA"

    else:
        prioridade = "MUITO BAIXA"

    return {
        "hipotese":
            hipotese,
        "prioridade_hipotese":
            prioridade,
        "evidencias":
            evidencias,
        "verificacoes_sugeridas":
            verificacoes_unicas,
        "limitacao":
            (
                "A hipótese organiza evidências estatísticas e "
                "temporais para orientar a investigação. "
                "Correlação e precedência temporal não comprovam "
                "relação causal."
            ),
    }



def consolidar_investigacao_assistida(
    variavel_principal,
    hipoteses,
    cobertura_principal_pct=None,
    registros_principal=None
):
    """
    Consolida as hipóteses determinísticas em um briefing
    de investigação técnica.

    Objetivo:
    - resumir a principal hipótese;
    - listar evidências-chave;
    - apontar lacunas de confiança;
    - sugerir próximos passos;
    - preparar um contexto estruturado para futura camada de IA.

    A função não gera diagnóstico causal.
    """

    if not hipoteses:

        return {
            "resumo":
                (
                    "Não há hipóteses temporais suficientes "
                    "para consolidar uma investigação assistida."
                ),
            "principal_hipotese": None,
            "evidencias_chave": [],
            "lacunas": [],
            "proximos_passos": [],
            "contexto_ia": {},
        }

    # Ordena por score temporal e depois por pontos válidos.
    hipoteses_ordenadas = sorted(
        hipoteses,
        key=lambda item: (
            item.get(
                "score_evidencia_temporal",
                0
            ),
            item.get(
                "pontos_validos",
                0
            )
        ),
        reverse=True
    )

    principal = hipoteses_ordenadas[0]

    evidencias_chave = []

    for item in hipoteses_ordenadas[:3]:

        evidencias_chave.append(
            (
                f"{item['variavel']} → "
                f"defasagem {str(item['defasagem']).replace('+', '')}; "
                f"correlação {float(item['melhor_correlacao']):.3f}; "
                f"{int(item['pontos_validos'])} pares; "
                f"score temporal "
                f"{int(item['score_evidencia_temporal'])}/100 "
                f"({item['classificacao_evidencia_temporal']})."
            )
        )

    lacunas = []

    if cobertura_principal_pct is not None:

        if cobertura_principal_pct < 90:

            lacunas.append(
                (
                    f"A variável principal cobre "
                    f"{cobertura_principal_pct:.1f}% da janela "
                    "solicitada; avaliar lacunas temporais."
                )
            )

    if registros_principal is not None:

        if registros_principal < 30:

            lacunas.append(
                (
                    "A variável principal possui poucos registros "
                    "válidos para uma investigação temporal robusta."
                )
            )

    if principal.get(
        "pontos_validos",
        0
    ) < 30:

        lacunas.append(
            (
                "A principal hipótese possui poucos pares válidos; "
                "repetir a análise em outra janela antes de elevar "
                "a confiança."
            )
        )

    if principal.get(
        "score_evidencia_temporal",
        0
    ) < 80:

        lacunas.append(
            (
                "A evidência temporal ainda não atingiu nível forte; "
                "validar coerência física e recorrência operacional."
            )
        )

    proximos_passos = [
        (
            "Verificar se a defasagem da principal hipótese é "
            "compatível com o tempo de transporte/retenção do processo."
        ),
        (
            "Comparar a hipótese principal com vazão, carga de entrada, "
            "aeração/estado dos aeradores e qualidade afluente."
        ),
        (
            "Repetir o estudo em outra janela de 7 dias e depois em "
            "30 dias para avaliar estabilidade do padrão."
        ),
        (
            "Registrar a avaliação do engenheiro de processo sobre "
            "plausibilidade física antes de qualquer recomendação operacional."
        ),
    ]

    resumo = (
        f"A principal hipótese de investigação para "
        f"{variavel_principal} é {principal['variavel']}, "
        f"que antecede a variável principal em aproximadamente "
        f"{str(principal['defasagem']).replace('+', '')}, "
        f"com score temporal "
        f"{int(principal['score_evidencia_temporal'])}/100 "
        f"({principal['classificacao_evidencia_temporal']}). "
        "O resultado deve ser tratado como evidência para investigação, "
        "não como causa confirmada."
    )

    contexto_ia = {
        "variavel_principal":
            variavel_principal,
        "principal_hipotese": {
            "variavel":
                principal["variavel"],
            "defasagem":
                principal["defasagem"],
            "melhor_correlacao":
                principal["melhor_correlacao"],
            "correlacao_sem_defasagem":
                principal["correlacao_sem_defasagem"],
            "ganho_abs_correlacao":
                principal["ganho_abs_correlacao"],
            "pontos_validos":
                principal["pontos_validos"],
            "score_evidencia_temporal":
                principal["score_evidencia_temporal"],
            "classificacao_evidencia_temporal":
                principal["classificacao_evidencia_temporal"],
        },
        "outras_hipoteses":
            hipoteses_ordenadas[1:3],
        "cobertura_principal_pct":
            cobertura_principal_pct,
        "registros_principal":
            registros_principal,
        "lacunas":
            lacunas,
        "proximos_passos":
            proximos_passos,
        "regra_de_seguranca":
            (
                "Não afirmar causalidade nem recomendar controle "
                "automático com base apenas nestas evidências."
            ),
    }

    return {
        "resumo":
            resumo,
        "principal_hipotese":
            principal,
        "evidencias_chave":
            evidencias_chave,
        "lacunas":
            lacunas,
        "proximos_passos":
            proximos_passos,
        "contexto_ia":
            contexto_ia,
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
        "modo",
        "ligado",
        "ligados",
        "desligado",
        "desligados",
        "em operação",
        "em operacao",
        "operando"
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
    # VARIÁVEIS FÍSICAS / ANALÍTICAS DE PROCESSO
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
        "ph",
        "cot",
        "dqo",
        "dbo",
        "nh3",
        "n-nh3",
        "nnh3",
        "amônia",
        "amonia",
        "nitrogênio",
        "nitrogenio",
        "oxigênio dissolvido",
        "oxigenio dissolvido",
        "od ",
        " od",
        "sólidos",
        "solidos",
        "turbidez",
        "recirculação",
        "recirculacao",
        "carga "
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
        "estimada",
        "índice",
        "indice"
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
    # ESTADO OPERACIONAL
    # --------------------------------------------------

    termos_estado = [
        "status",
        "estado",
        "modo",
        "ligado",
        "ligados",
        "desligado",
        "desligados",
        "em operação",
        "em operacao",
        "operando",
        "aeradores ligados"
    ]

    if any(
        termo in nome
        for termo in termos_estado
    ):
        return "ESTADO OPERACIONAL"

    # --------------------------------------------------
    # QUALIDADE / PROCESSO BIOLÓGICO-QUÍMICO
    # --------------------------------------------------

    termos_qualidade = [
        "cot",
        "dqo",
        "dbo",
        "nh3",
        "n-nh3",
        "nnh3",
        "amônia",
        "amonia",
        "nitrogênio",
        "nitrogenio",
        "sólidos",
        "solidos",
        "turbidez"
    ]

    if any(
        termo in nome
        for termo in termos_qualidade
    ):
        return "PROCESSO / QUALIDADE"

    # --------------------------------------------------
    # ENERGIA / ELÉTRICA
    # --------------------------------------------------

    termos_energia = [
        "energia",
        "consumo",
        "potência",
        "potencia",
        "corrente",
        "tensão",
        "tensao",
        "frequência",
        "frequencia",
        "fator de potência",
        "fator de potencia"
    ]

    if any(
        termo in nome
        for termo in termos_energia
    ):
        return "ENERGIA / ELÉTRICA"

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
        return "PROCESSO"

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
        "volume",
        "oxigênio dissolvido",
        "oxigenio dissolvido",
        "recirculação",
        "recirculacao",
        "carga ",
        "od "
    ]

    if any(
        termo in nome
        for termo in termos_processo
    ):
        return "PROCESSO"

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
    # DIFERENCIAIS ELÉTRICOS CALCULADOS
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
            return "ENERGIA / ELÉTRICA"

    return "NÃO CLASSIFICADA"


def classificar_relevancia_engenharia(nome_variavel):
    """
    Classifica a relevância de uma variável para investigação
    de processo.

    A ordem das regras é importante:
    primeiro identificamos variáveis auxiliares/acumulativas,
    depois variáveis físicas de processo e, por último,
    variáveis operacionais.
    """

    nome = str(nome_variavel).lower()

    # ======================================================
    # BAIXA RELEVÂNCIA
    # Acumuladores / manutenção / tempos auxiliares
    # Devem ser avaliados ANTES de termos como "aerador"
    # ======================================================

    termos_baixa = [
        "tempo manutenção",
        "tempo manutencao",
        "tempo desligado",
        "tempo ligado",
        "horímetro",
        "horimetro",
        "contador",
        "contagem",
        "tempo operação",
        "tempo operacao",
        "última manutenção",
        "ultima manutencao",
    ]

    for termo in termos_baixa:

        if termo in nome:

            return {
                "relevancia_engenharia": "BAIXA",
                "peso_relevancia": -25,
            }

    # ======================================================
    # ALTA RELEVÂNCIA
    # Variáveis diretamente relacionadas ao processo
    # ======================================================

    termos_alta = [
        "oxigênio dissolvido",
        "oxigenio dissolvido",
        "vazão",
        "vazao",
        "pressão",
        "pressao",
        "nível",
        "nivel",
        "temperatura",
        "ph",
        "sólidos",
        "solidos",
        "cot",
        "dqo",
        "dbo",
        "nh3",
        "n-nh3",
        "nnh3",
        "nitrogênio",
        "nitrogenio",
        "tco",
        "recirculação",
        "recirculacao",
        "fator de carga",
        "f/m",
        "turbidez",
    ]

    for termo in termos_alta:

        if termo in nome:

            return {
                "relevancia_engenharia": "ALTA",
                "peso_relevancia": 30,
            }

    # ======================================================
    # MÉDIA RELEVÂNCIA
    # Estado operacional / energia / atuação
    # ======================================================

    termos_media = [
        "status",
        "estado",
        "ligado",
        "desligado",
        "potência",
        "potencia",
        "energia",
        "corrente",
        "tensão",
        "tensao",
        "frequência",
        "frequencia",
        "consumo",
        "aerador",
        "disponibilidade",
    ]

    for termo in termos_media:

        if termo in nome:

            return {
                "relevancia_engenharia": "MÉDIA",
                "peso_relevancia": 15,
            }

    # ======================================================
    # NÃO CLASSIFICADA
    # ======================================================

    return {
        "relevancia_engenharia": "NÃO CLASSIFICADA",
        "peso_relevancia": 0,
    }