import streamlit as st
import pandas as pd

from adaptador_pi_af import (
    listar_elementos,
    listar_atributos,
    carregar_historico_atributo,
)

from motor_estudo_processo import (
    preparar_historico,
    gerar_ranking_correlacoes,
)


# ==========================================================
# CACHE - DATABASES AF
# ==========================================================

@st.cache_data(ttl=300)
def obter_databases_estudo_cache(servidor):
    """
    Retorna as databases disponíveis no servidor AF
    e mantém o resultado em cache por 5 minutos.
    """

    from adaptador_pi_af import listar_databases

    return listar_databases(servidor)


# ==========================================================
# CONTEXTO DO PROCESSO
# ==========================================================

def renderizar_contexto_processo():
    """
    Renderiza a seleção de contexto do processo no PI/AF.
    """

    st.subheader("Contexto do Processo")

    servidor_estudo = "CE-SRV11"

    try:

        databases_estudo = obter_databases_estudo_cache(
            servidor_estudo
        )

        database_estudo = st.selectbox(
            "Database AF",
            options=databases_estudo,
            key="database_estudo_processo"
        )

        # =========================
        # PRIMEIRO NÍVEL
        # =========================

        elementos_estudo = listar_elementos(
            servidor=servidor_estudo,
            database=database_estudo
        )

        if not elementos_estudo:

            st.warning(
                "A database selecionada não possui "
                "elementos disponíveis."
            )

            return None

        area_estudo = st.selectbox(
            "Área / Elemento",
            options=elementos_estudo,
            key="area_estudo_processo"
        )

        caminho_estudo = [
            area_estudo
        ]

        # =========================
        # NAVEGAÇÃO DINÂMICA AF
        # =========================

        nivel = 2
        max_niveis = 10

        while nivel <= max_niveis:

            subelementos_estudo = listar_elementos(
                servidor=servidor_estudo,
                database=database_estudo,
                caminho_elementos=caminho_estudo
            )

            if not subelementos_estudo:
                break

            caminho_key = "__".join(
                caminho_estudo
            )

            elemento_nivel = st.selectbox(
                f"Nível {nivel}",
                options=[
                    "Usar este elemento"
                ] + subelementos_estudo,
                key=(
                    f"nivel_estudo_processo_"
                    f"{database_estudo}_"
                    f"{caminho_key}"
                )
            )

            if elemento_nivel == "Usar este elemento":
                break

            caminho_estudo.append(
                elemento_nivel
            )

            nivel += 1

        caminho_formatado = " > ".join(
            caminho_estudo
        )

        st.success(
            f"📍 Elemento selecionado: "
            f"{database_estudo} > {caminho_formatado}"
        )

        return {
            "servidor": servidor_estudo,
            "database": database_estudo,
            "caminho": caminho_estudo,
            "caminho_formatado": caminho_formatado,
        }

    except Exception as erro:

        st.error(
            "Não foi possível consultar a estrutura PI/AF: "
            f"{erro}"
        )

        return None


# ==========================================================
# VARIÁVEL PRINCIPAL E ESCOPO
# ==========================================================

def renderizar_variavel_e_escopo(contexto):
    """
    Renderiza a seleção da variável principal
    e do escopo do estudo.
    """

    if contexto is None:
        return None

    try:

        atributos_estudo = listar_atributos(
            servidor=contexto["servidor"],
            database=contexto["database"],
            caminho_elementos=contexto["caminho"]
        )

    except Exception as erro:

        st.error(
            "Não foi possível consultar os atributos "
            f"do elemento: {erro}"
        )

        return None

    if not atributos_estudo:

        st.warning(
            "O elemento selecionado não possui "
            "atributos disponíveis para análise."
        )

        return None

    # =========================
    # VARIÁVEL PRINCIPAL
    # =========================

    st.subheader(
        "Variável Principal"
    )

    variavel_principal = st.selectbox(
        "Variável que será o foco do estudo",
        options=atributos_estudo,
        key="variavel_principal_estudo"
    )

    # =========================
    # ESCOPO
    # =========================

    st.subheader(
        "Escopo de Análise"
    )

    escopo_analise = st.radio(
        (
            "Onde o sistema poderá buscar relações "
            "com a variável principal?"
        ),
        options=[
            "Somente o elemento selecionado",
            "Área selecionada",
            "Áreas e bases selecionadas",
            "Exploração ampliada"
        ],
        index=0,
        key="escopo_analise_processo",
        help=(
            "Define até onde o motor de análise poderá "
            "buscar variáveis relacionadas ao objetivo "
            "do estudo."
        )
    )

    return {
        "atributos": atributos_estudo,
        "variavel_principal": variavel_principal,
        "escopo": escopo_analise,
    }


# ==========================================================
# DADOS DO ESTUDO
# ==========================================================

def renderizar_dados_estudo(
    periodo_estudo,
    contexto,
    selecao_estudo
):
    """
    Renderiza os controles para carregamento dos dados
    utilizados no estudo de processo.
    """

    if contexto is None:
        return None

    if selecao_estudo is None:
        return None

    st.subheader(
        "Dados do Estudo"
    )

    periodos_af = {
        "Últimas 24 horas": "*-24h",
        "Últimos 7 dias": "*-7d",
        "Últimos 30 dias": "*-30d",
    }

    if periodo_estudo == "Período personalizado":

        st.info(
            "A seleção de período personalizado "
            "será implementada na próxima etapa."
        )

        return None

    inicio_estudo = periodos_af[
        periodo_estudo
    ]

    fim_estudo = "*"

    carregar_estudo = st.button(
        "🔬 Carregar dados do estudo",
        key="carregar_dados_estudo"
    )

    return {
        "inicio": inicio_estudo,
        "fim": fim_estudo,
        "carregar": carregar_estudo,
    }

#===========================================================
# FUNAÇÃO AUXILIAR - CARREGAR VARIÁVEIS DE COMPARAÇÃO
#=========================================================  
def carregar_variaveis_comparacao(
    contexto,
    selecao_estudo,
    dados_estudo,
    variavel_principal
):
    """
    Carrega e prepara os históricos das variáveis
    que poderão ser comparadas com a variável principal.
    """

    historicos_comparacao = {}

    with st.spinner(
        "Consultando as demais variáveis do elemento..."
    ):

        for nome_atributo in selecao_estudo["atributos"]:

            if nome_atributo == variavel_principal:
                continue

            try:

                historico_atributo = carregar_historico_atributo(
                    servidor=contexto["servidor"],
                    database=contexto["database"],
                    caminho_elementos=contexto["caminho"],
                    nome_atributo=nome_atributo,
                    inicio=dados_estudo["inicio"],
                    fim=dados_estudo["fim"]
                )

                historico_preparado = preparar_historico(
                    historico_atributo
                )

                if not historico_preparado.empty:

                    historicos_comparacao[
                        nome_atributo
                    ] = historico_preparado

            except Exception:
                continue

    return historicos_comparacao

# ==========================================================
# EXECUÇÃO DO ESTUDO
# ==========================================================
def executar_estudo_processo(
    contexto,
    selecao_estudo,
    dados_estudo
):
    """
    Executa o estudo de processo:
    - carrega a variável principal;
    - carrega variáveis de comparação;
    - calcula correlações;
    - apresenta ranking estatístico;
    - prioriza candidatos para investigação de engenharia.
    """

    if contexto is None:
        return

    if selecao_estudo is None:
        return

    if dados_estudo is None:
        return

    if not dados_estudo["carregar"]:
        return

    variavel_principal = selecao_estudo[
        "variavel_principal"
    ]

    try:

        # ==================================================
        # 1. VARIÁVEL PRINCIPAL
        # ==================================================

        with st.spinner(
            "Consultando variável principal no PI..."
        ):

            historico_principal = (
                carregar_historico_atributo(
                    servidor=contexto["servidor"],
                    database=contexto["database"],
                    caminho_elementos=contexto["caminho"],
                    nome_atributo=variavel_principal,
                    inicio=dados_estudo["inicio"],
                    fim=dados_estudo["fim"]
                )
            )

            historico_principal = preparar_historico(
                historico_principal
            )

        if historico_principal.empty:

            st.warning(
                "Não foram encontrados dados numéricos "
                "suficientes para a variável principal."
            )

            return

        st.success(
            f"{len(historico_principal)} registros válidos "
            f"carregados para {variavel_principal}."
        )

        # ==================================================
        # 2. VARIÁVEIS DE COMPARAÇÃO
        # ==================================================

        historicos_comparacao = (
            carregar_variaveis_comparacao(
                contexto=contexto,
                selecao_estudo=selecao_estudo,
                dados_estudo=dados_estudo,
                variavel_principal=variavel_principal
            )
        )

        if not historicos_comparacao:

            st.warning(
                "Nenhuma outra variável com histórico "
                "numérico válido foi encontrada."
            )

            return

        st.success(
            f"{len(historicos_comparacao)} variáveis "
            "com histórico numérico disponíveis "
            "para comparação."
        )

        # ==================================================
        # 3. RANKING DE CORRELAÇÕES
        # ==================================================

        with st.spinner(
            "Calculando relações entre as variáveis..."
        ):

            ranking_correlacoes = (
                gerar_ranking_correlacoes(
                    historico_principal=historico_principal,
                    historicos_comparacao=historicos_comparacao,
                    nome_principal=variavel_principal
                )
            )

        if ranking_correlacoes.empty:

            st.warning(
                "Não foi possível calcular relações "
                "estatísticas com os dados disponíveis."
            )

            return

        # ==================================================
        # 4. PREPARAÇÃO DOS RESULTADOS
        # ==================================================

        ranking_resultado = ranking_correlacoes.copy()

        ranking_resultado[
            "correlacao_numerica"
        ] = pd.to_numeric(
            ranking_resultado["correlacao"],
            errors="coerce"
        )

        ranking_resultado[
            "correlacao_abs"
        ] = ranking_resultado[
            "correlacao_numerica"
        ].abs()

        ranking_resultado[
            "score_prioridade"
        ] = pd.to_numeric(
            ranking_resultado["score_prioridade"],
            errors="coerce"
        ).fillna(0)

        ranking_resultado[
            "pontos_validos"
        ] = pd.to_numeric(
            ranking_resultado["pontos_validos"],
            errors="coerce"
        ).fillna(0)

        # ==================================================
        # 5. RANKING ESTATÍSTICO
        # ==================================================

        ranking_estatistico = (
            ranking_resultado
            .sort_values(
                by="correlacao_abs",
                ascending=False
            )
            .reset_index(drop=True)
        )

        st.divider()

        st.markdown(
            "## 🔗 Variáveis mais relacionadas"
        )

        st.caption(
            f"Ranking estatístico das variáveis relacionadas "
            f"a **{variavel_principal}**, ordenado pela "
            "intensidade absoluta da correlação."
        )

        colunas_exibicao = [
            coluna
            for coluna in [
                "variavel",
                "tipo_variavel",
                "categoria_engenharia",
                "tipo_relacao",
                "correlacao",
                "direcao",
                "classificacao",
                "confiabilidade",
                "pontos_validos",
                "score_prioridade",
                "prioridade_investigacao",
            ]
            if coluna in ranking_estatistico.columns
        ]

        st.dataframe(
            ranking_estatistico[
                colunas_exibicao
            ].head(10),
            width="stretch",
            hide_index=True
        )

        # ==================================================
        # 6. MAIOR ASSOCIAÇÃO ESTATÍSTICA
        # ==================================================

        ranking_validos = ranking_estatistico.dropna(
            subset=["correlacao_numerica"]
        )

        if not ranking_validos.empty:

            maior_associacao = ranking_validos.iloc[0]

            nome_estatistico = maior_associacao[
                "variavel"
            ]

            correlacao_estatistica = maior_associacao[
                "correlacao_numerica"
            ]

            tipo_estatistico = maior_associacao[
                "tipo_variavel"
            ]

            categoria_estatistica = maior_associacao[
                "categoria_engenharia"
            ]

            st.markdown(
                "### 📊 Maior associação estatística"
            )

            st.info(
                f"**{nome_estatistico}** apresentou a maior "
                f"associação estatística com "
                f"**{variavel_principal}**, com correlação "
                f"**{correlacao_estatistica:.3f}**. "
                f"A variável é classificada como "
                f"**{tipo_estatistico} | "
                f"{categoria_estatistica}**."
            )

        # ==================================================
        # 7. PRIORIDADE DE ENGENHARIA
        # ==================================================

        ranking_engenharia = ranking_resultado.dropna(
            subset=["correlacao_numerica"]
        ).copy()

        # Peso utilizado somente como critério de desempate.
        # O score de prioridade continua sendo o critério principal.

        pesos_relacao = {
            "RELAÇÃO DE PROCESSO": 4,
            "RELAÇÃO OPERACIONAL": 3,
            "RELAÇÃO CALCULADA": 2,
            "RELAÇÃO DERIVADA / KPI": 1,
            "RELAÇÃO NÃO CLASSIFICADA": 0,
        }

        ranking_engenharia[
            "peso_relacao_engenharia"
        ] = ranking_engenharia[
            "tipo_relacao"
        ].map(
            pesos_relacao
        ).fillna(0)

        ranking_engenharia = (
            ranking_engenharia
            .sort_values(
                by=[
                    "score_prioridade",
                    "peso_relacao_engenharia",
                    "correlacao_abs",
                    "pontos_validos",
                ],
                ascending=[
                    False,
                    False,
                    False,
                    False,
                ]
            )
            .reset_index(drop=True)
        )

        # ==================================================
        # 8. TABELA DE PRIORIDADE DE ENGENHARIA
        # ==================================================

        st.divider()

        st.markdown(
            "## 🎯 Prioridades para Investigação de Engenharia"
        )

        st.caption(
            "O score de prioridade é o critério principal. "
            "Em caso de empate, relações físicas de processo "
            "são priorizadas em relação a variáveis "
            "calculadas ou KPIs."
        )

        ranking_engenharia[
            "ordem_investigacao"
        ] = range(
            1,
            len(ranking_engenharia) + 1
        )

        colunas_engenharia = [
            coluna
            for coluna in [
                "ordem_investigacao",
                "variavel",
                "tipo_variavel",
                "categoria_engenharia",
                "tipo_relacao",
                "correlacao",
                "classificacao",
                "confiabilidade",
                "pontos_validos",
                "score_prioridade",
                "prioridade_investigacao",
            ]
            if coluna in ranking_engenharia.columns
        ]

        st.dataframe(
            ranking_engenharia[
                colunas_engenharia
            ].head(10),
            width="stretch",
            hide_index=True
        )

        # ==================================================
        # 9. PRINCIPAL CANDIDATO DE ENGENHARIA
        # ==================================================

        if not ranking_engenharia.empty:

            candidato = ranking_engenharia.iloc[0]

            nome_candidato = candidato[
                "variavel"
            ]

            categoria_candidato = candidato[
                "categoria_engenharia"
            ]

            tipo_candidato = candidato[
                "tipo_variavel"
            ]

            relacao_candidato = candidato[
                "tipo_relacao"
            ]

            correlacao_candidato = candidato[
                "correlacao_numerica"
            ]

            score_candidato = int(
                candidato[
                    "score_prioridade"
                ]
            )

            prioridade_candidato = candidato[
                "prioridade_investigacao"
            ]

            st.markdown(
                "### 🔎 Principal candidato "
                "para investigação de engenharia"
            )

            st.success(
                f"**{nome_candidato}** foi priorizada como "
                f"primeiro candidato para investigação em "
                f"relação a **{variavel_principal}**. "
                f"É uma variável **{tipo_candidato}**, "
                f"da categoria **{categoria_candidato}**, "
                f"com relação classificada como "
                f"**{relacao_candidato}**. "
                f"A correlação observada foi "
                f"**{correlacao_candidato:.3f}**, "
                f"com score de prioridade "
                f"**{score_candidato} "
                f"({prioridade_candidato})**."
            )

            st.caption(
                "A prioridade indica onde iniciar a "
                "investigação técnica. Correlação e "
                "prioridade não comprovam causalidade."
            )

    except Exception as erro:

        st.error(
            "Não foi possível executar o estudo: "
            f"{erro}"
        )

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================

def renderizar_estudo_processo():
    """
    Renderiza a interface principal do módulo
    Estudo de Processo.
    """

    st.header(
        "🔬 Estudo de Processo"
    )

    st.info(
        "Módulo destinado à investigação, análise "
        "e melhoria de processos industriais."
    )

    # ======================================================
    # CONFIGURAÇÃO DO ESTUDO
    # ======================================================

    st.subheader(
        "Configuração do Estudo"
    )

    col1, col2 = st.columns(2)

    with col1:

        tipo_estudo = st.selectbox(
            "Tipo de estudo",
            options=[
                "Investigação de anomalia",
                "Melhoria de processo",
                "Comparação operacional",
                "Exploração de dados"
            ],
            key="tipo_estudo_processo"
        )

    with col2:

        periodo_estudo = st.selectbox(
            "Período inicial de análise",
            options=[
                "Últimas 24 horas",
                "Últimos 7 dias",
                "Últimos 30 dias",
                "Período personalizado"
            ],
            key="periodo_estudo_processo"
        )

    objetivo_estudo = st.text_area(
        "Objetivo do estudo",
        placeholder=(
            "Ex.: Identificar quais variáveis de processo "
            "estão relacionadas à variação observada..."
        ),
        key="objetivo_estudo_processo"
    )

    # ======================================================
    # CONTEXTO DO PROCESSO
    # ======================================================

    contexto = renderizar_contexto_processo()

    # ======================================================
    # VARIÁVEL PRINCIPAL E ESCOPO
    # ======================================================

    selecao_estudo = renderizar_variavel_e_escopo(
        contexto
    )

    # ======================================================
    # DADOS DO ESTUDO
    # ======================================================

    dados_estudo = renderizar_dados_estudo(
        periodo_estudo=periodo_estudo,
        contexto=contexto,
        selecao_estudo=selecao_estudo
    )

    # ======================================================
    # EXECUÇÃO
    # ======================================================

    executar_estudo_processo(
        contexto=contexto,
        selecao_estudo=selecao_estudo,
        dados_estudo=dados_estudo
    )