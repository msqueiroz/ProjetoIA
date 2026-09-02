import streamlit as st
import pandas as pd
import time
import hashlib
from adaptador_pi_af import (
    listar_elementos,
    listar_atributos,
    carregar_historico_inteligente,
)

from motor_estudo_processo import (
    preparar_historico,
    gerar_ranking_correlacoes,
    analisar_defasagem,
    interpretar_defasagem,
    calcular_score_evidencia_temporal,
    gerar_hipotese_engenharia_temporal,
    consolidar_investigacao_assistida,
)

from adaptador_ia import (
    verificar_ollama,
    consultar_ia,
)

import tempfile
from pathlib import Path

from gerenciador_conhecimento import (
    criar_trechos_pdf,
    buscar_trechos,
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
# PREPARAÇÃO SEGURA DE HISTÓRICO
# ==========================================================

def preparar_historico_seguro(historico):
    """
    Valida o DataFrame recebido do PI antes de chamar
    preparar_historico().

    Evita erros quando o PI retorna:
    - None;
    - DataFrame vazio;
    - DataFrame sem as colunas esperadas.
    """

    if historico is None:
        return pd.DataFrame(
            columns=[
                "data_hora",
                "valor",
                "valor_numerico",
            ]
        )

    if not isinstance(historico, pd.DataFrame):
        return pd.DataFrame(
            columns=[
                "data_hora",
                "valor",
                "valor_numerico",
            ]
        )

    if historico.empty:
        return pd.DataFrame(
            columns=[
                "data_hora",
                "valor",
                "valor_numerico",
            ]
        )

    # ------------------------------------------------------
    # Normalização defensiva de nomes
    # ------------------------------------------------------

    dados = historico.copy()

    mapa_colunas = {}

    for coluna in dados.columns:

        nome_normalizado = (
            str(coluna)
            .strip()
            .lower()
        )

        if nome_normalizado in [
            "timestamp",
            "time",
            "datetime",
            "data",
            "datahora",
            "data_hora",
        ]:
            mapa_colunas[coluna] = "data_hora"

        elif nome_normalizado in [
            "value",
            "valor",
        ]:
            mapa_colunas[coluna] = "valor"

    if mapa_colunas:
        dados = dados.rename(
            columns=mapa_colunas
        )

    # ------------------------------------------------------
    # Verificação obrigatória
    # ------------------------------------------------------

    if "data_hora" not in dados.columns:
        return pd.DataFrame(
            columns=[
                "data_hora",
                "valor",
                "valor_numerico",
            ]
        )

    if "valor" not in dados.columns:
        return pd.DataFrame(
            columns=[
                "data_hora",
                "valor",
                "valor_numerico",
            ]
        )

    try:

        return preparar_historico(
            dados
        )

    except Exception:

        return pd.DataFrame(
            columns=[
                "data_hora",
                "valor",
                "valor_numerico",
            ]
        )


# ==========================================================
# CONTEXTO DO PROCESSO
# ==========================================================

def renderizar_contexto_processo():
    """
    Renderiza duas navegações independentes no PI/AF:

    1. Origem da variável principal
       Ex.: ETF > ETF - Atendimento à Legislação

    2. Contexto físico da investigação
       Ex.: ETE > ETE

    Isso permite investigar uma variável armazenada em um ramo
    diferente daquele onde estão as variáveis explicativas.
    """

    st.subheader("Contexto do Processo")

    servidor_estudo = "CE-SRV11"

    try:

        # ==================================================
        # DATABASE
        # ==================================================

        databases_estudo = obter_databases_estudo_cache(
            servidor_estudo
        )

        if not databases_estudo:

            st.warning(
                "Nenhuma database AF foi encontrada."
            )

            return None

        database_estudo = st.selectbox(
            "Database AF",
            options=databases_estudo,
            key="database_estudo_processo"
        )

        # ==================================================
        # FUNÇÃO INTERNA DE NAVEGAÇÃO
        # ==================================================

        def navegar_hierarquia(
            titulo,
            prefixo_key
        ):
            """
            Permite navegar dinamicamente pela árvore AF
            e retorna o caminho selecionado.
            """

            st.markdown(
                f"#### {titulo}"
            )

            elementos_raiz = listar_elementos(
                servidor=servidor_estudo,
                database=database_estudo,
                caminho_elementos=[]
            )

            if not elementos_raiz:

                st.warning(
                    "A database selecionada não possui "
                    "elementos disponíveis."
                )

                return None

            elemento_raiz = st.selectbox(
                "Área / Elemento",
                options=elementos_raiz,
                key=f"{prefixo_key}_nivel_1"
            )

            caminho = [
                elemento_raiz
            ]

            nivel = 2
            max_niveis = 10

            while nivel <= max_niveis:

                try:

                    subelementos = listar_elementos(
                        servidor=servidor_estudo,
                        database=database_estudo,
                        caminho_elementos=caminho
                    )

                except Exception:
                    break

                if not subelementos:
                    break

                caminho_key = "__".join(
                    caminho
                )

                elemento_nivel = st.selectbox(
                    f"Nível {nivel}",
                    options=[
                        "Usar este elemento"
                    ] + subelementos,
                    key=(
                        f"{prefixo_key}_"
                        f"{database_estudo}_"
                        f"{caminho_key}_"
                        f"nivel_{nivel}"
                    )
                )

                if (
                    elemento_nivel
                    == "Usar este elemento"
                ):
                    break

                caminho.append(
                    elemento_nivel
                )

                nivel += 1

            return caminho

        # ==================================================
        # 1. ORIGEM DA VARIÁVEL PRINCIPAL
        # ==================================================

        caminho_variavel = navegar_hierarquia(
            titulo="🎯 Origem da variável principal",
            prefixo_key="origem_variavel_estudo"
        )

        if not caminho_variavel:
            return None

        caminho_variavel_formatado = " > ".join(
            caminho_variavel
        )

        st.success(
            f"📍 Elemento da variável: "
            f"{database_estudo} > "
            f"{caminho_variavel_formatado}"
        )

        st.divider()

        # ==================================================
        # 2. CONTEXTO FÍSICO DA INVESTIGAÇÃO
        # ==================================================

        caminho_contexto = navegar_hierarquia(
            titulo="🏭 Contexto para investigação",
            prefixo_key="contexto_investigacao_estudo"
        )

        if not caminho_contexto:
            return None

        caminho_contexto_formatado = " > ".join(
            caminho_contexto
        )

        st.info(
            f"🏭 Contexto do processo: "
            f"{database_estudo} > "
            f"{caminho_contexto_formatado}"
        )

        # ==================================================
        # RESUMO VISUAL
        # ==================================================

        st.caption(
            "A variável principal pode estar armazenada "
            "em um ramo diferente daquele utilizado como "
            "contexto físico da investigação."
        )

        # ==================================================
        # RETORNO
        # ==================================================

        return {
            "servidor": servidor_estudo,
            "database": database_estudo,

            # Onde a variável principal está armazenada
            "caminho": caminho_variavel,

            # Onde o sistema buscará variáveis explicativas
            "caminho_contexto": caminho_contexto,

            "caminho_formatado":
                caminho_variavel_formatado,

            "contexto_formatado":
                caminho_contexto_formatado,
        }

    except Exception as erro:

        st.error(
            "Não foi possível consultar "
            "a estrutura PI/AF: "
            f"{erro}"
        )

        return None


# ==========================================================
# VARIÁVEL PRINCIPAL E ESCOPO
# ==========================================================

def renderizar_variavel_e_escopo(
    contexto
):
    """
    Renderiza a seleção da variável principal
    e do escopo do estudo.
    """

    if contexto is None:
        return None

    try:

        atributos_estudo = listar_atributos(
            servidor=contexto[
                "servidor"
            ],
            database=contexto[
                "database"
            ],
            caminho_elementos=contexto[
                "caminho"
            ]
        )

    except Exception as erro:

        st.error(
            "Não foi possível consultar "
            "os atributos do elemento: "
            f"{erro}"
        )

        return None

    if not atributos_estudo:

        st.warning(
            "O elemento selecionado não possui "
            "atributos disponíveis para análise."
        )

        return None

    # ======================================================
    # VARIÁVEL PRINCIPAL
    # ======================================================

    st.subheader(
        "Variável Principal"
    )

    variavel_principal = st.selectbox(
        "Variável que será o foco do estudo",
        options=atributos_estudo,
        key="variavel_principal_estudo"
    )

    # ======================================================
    # ESCOPO
    # ======================================================

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

    # ------------------------------------------------------
    # Explicação visual do escopo
    # ------------------------------------------------------

    if (
        escopo_analise
        == "Somente o elemento selecionado"
    ):

        st.caption(
            "🔹 As comparações serão realizadas somente "
            "com atributos do elemento onde está a "
            "variável principal."
        )

    elif (
        escopo_analise
        == "Exploração ampliada"
    ):

        st.caption(
            "🔎 O estudo poderá utilizar o contexto "
            "ampliado definido acima para procurar "
            "variáveis em outros elementos do processo."
        )

        st.info(
            "A exploração hierárquica ampliada será "
            "utilizada nas próximas etapas da POC."
        )

    return {

        "atributos":
            atributos_estudo,

        "variavel_principal":
            variavel_principal,

        "escopo":
            escopo_analise,

        "caminho_contexto":
            contexto.get(
                "caminho_contexto",
                contexto["caminho"]
            ),
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
    Renderiza os controles utilizados para
    carregamento dos dados do estudo.
    """

    if contexto is None:
        return None

    if selecao_estudo is None:
        return None

    st.subheader(
        "Dados do Estudo"
    )

    periodos_af = {

        "Últimas 24 horas":
            "*-24h",

        "Últimos 7 dias":
            "*-7d",

        "Últimos 30 dias":
            "*-30d",
    }

    if (
        periodo_estudo
        == "Período personalizado"
    ):

        st.info(
            "A seleção de período personalizado "
            "será implementada em uma próxima etapa."
        )

        return None

    inicio_estudo = (
        periodos_af[
            periodo_estudo
        ]
    )

    fim_estudo = "*"

    carregar_estudo = st.button(
        "🔬 Carregar dados do estudo",
        key="carregar_dados_estudo"
    )

    return {

        "inicio":
            inicio_estudo,

        "fim":
            fim_estudo,

        "carregar":
            carregar_estudo,

        "periodo_solicitado":
            periodo_estudo,
    }


# ==========================================================
# CARREGAR VARIÁVEIS DE COMPARAÇÃO
# ==========================================================
def carregar_variaveis_comparacao(
    contexto,
    selecao_estudo,
    dados_estudo,
    variavel_principal
):
    """
    Carrega históricos numéricos para comparação com a
    variável principal.

    Antes de consultar o histórico no PI/AF, aplica um filtro
    de relevância de engenharia para reduzir consultas
    desnecessárias.
    """

    historicos_comparacao = {}

    escopo = selecao_estudo.get(
        "escopo",
        "Somente o elemento selecionado"
    )

    inicio_total = time.perf_counter()

    # ======================================================
    # ÁREA DE STATUS
    # ======================================================

    status_execucao = st.empty()
    detalhe_execucao = st.empty()

    # ======================================================
    # FUNÇÃO INTERNA
    # FILTRO ANTES DA CONSULTA AO PI
    # ======================================================

    def atributo_relevante(nome_atributo):
        """
        Decide se vale a pena consultar o histórico do
        atributo durante o estudo de processo.

        Retorna:
        - True  -> consultar histórico
        - False -> não consultar
        """

        nome = str(nome_atributo).lower()

        # --------------------------------------------------
        # EXCLUSÕES
        # Acumuladores / manutenção / tempos auxiliares
        # --------------------------------------------------

        termos_excluir = [
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

        if any(
            termo in nome
            for termo in termos_excluir
        ):
            return False

        # --------------------------------------------------
        # VARIÁVEIS DE PROCESSO
        # --------------------------------------------------

        termos_processo = [
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
            "turbidez",
            "recirculação",
            "recirculacao",
            "fator de carga",
            "carga",
        ]

        if any(
            termo in nome
            for termo in termos_processo
        ):
            return True

        # --------------------------------------------------
        # VARIÁVEIS OPERACIONAIS
        # --------------------------------------------------

        termos_operacao = [
            "status",
            "estado",
            "modo",
            "ligado",
            "operação",
            "operacao",
            "disponibilidade",
        ]

        if any(
            termo in nome
            for termo in termos_operacao
        ):
            return True

        # --------------------------------------------------
        # ENERGIA / ELÉTRICA
        # --------------------------------------------------

        termos_energia = [
            "potência",
            "potencia",
            "energia",
            "corrente",
            "tensão",
            "tensao",
            "frequência",
            "frequencia",
            "consumo",
        ]

        if any(
            termo in nome
            for termo in termos_energia
        ):
            return True

        # --------------------------------------------------
        # DESCONHECIDO
        #
        # Nesta fase da POC preferimos NÃO consultar
        # automaticamente atributos sem relevância conhecida.
        # --------------------------------------------------

        return False

    # ======================================================
    # FUNÇÃO INTERNA PARA CARREGAR UM ELEMENTO
    # ======================================================

    def carregar_elemento(
        caminho_elemento,
        prefixo_variavel=None,
        ignorar_variavel_principal=False
    ):

        inicio_elemento = time.perf_counter()

        nome_elemento = (
            caminho_elemento[-1]
            if caminho_elemento
            else "Elemento"
        )

        status_execucao.info(
            f"⏳ Analisando elemento: **{nome_elemento}**"
        )

        # --------------------------------------------------
        # LISTAR ATRIBUTOS
        # --------------------------------------------------

        try:

            atributos_elemento = listar_atributos(
                servidor=contexto["servidor"],
                database=contexto["database"],
                caminho_elementos=caminho_elemento
            )

        except Exception as erro:

            st.warning(
                f"Não foi possível listar atributos de "
                f"**{nome_elemento}**: {erro}"
            )

            return 0, 0, 0, 0

        if not atributos_elemento:

            detalhe_execucao.caption(
                f"{nome_elemento}: nenhum atributo encontrado."
            )

            return 0, 0, 0, 0

        total_atributos = len(
            atributos_elemento
        )

        # --------------------------------------------------
        # FILTRAR ANTES DE CONSULTAR O HISTÓRICO
        # --------------------------------------------------

        atributos_candidatos = []

        for nome_atributo in atributos_elemento:

            if (
                ignorar_variavel_principal
                and nome_atributo == variavel_principal
            ):
                continue

            if atributo_relevante(
                nome_atributo
            ):
                atributos_candidatos.append(
                    nome_atributo
                )

        total_candidatos = len(
            atributos_candidatos
        )

        total_ignorados = (
            total_atributos
            - total_candidatos
        )

        detalhe_execucao.caption(
            f"🧠 {nome_elemento}: "
            f"{total_atributos} atributos encontrados → "
            f"{total_candidatos} candidatos de engenharia → "
            f"{total_ignorados} consultas evitadas."
        )

        # --------------------------------------------------
        # NENHUM CANDIDATO
        # --------------------------------------------------

        if total_candidatos == 0:

            tempo_elemento = (
                time.perf_counter()
                - inicio_elemento
            )

            st.info(
                f"ℹ️ {nome_elemento}: "
                f"{total_atributos} atributos encontrados, "
                "mas nenhum foi classificado como candidato "
                "de engenharia."
            )

            return (
                total_atributos,
                0,
                0,
                tempo_elemento
            )

        # --------------------------------------------------
        # CONSULTAR SOMENTE CANDIDATOS
        # --------------------------------------------------

        total_validos = 0

        barra_atributos = st.progress(0)

        for indice, nome_atributo in enumerate(
            atributos_candidatos,
            start=1
        ):

            detalhe_execucao.caption(
                f"📡 {nome_elemento} — "
                f"candidato {indice}/{total_candidatos}: "
                f"**{nome_atributo}**"
            )

            inicio_atributo = (
                time.perf_counter()
            )

            try:

                resultado_historico = (
                    carregar_historico_inteligente(
                        servidor=contexto["servidor"],
                        database=contexto["database"],
                        caminho_elementos=caminho_elemento,
                        nome_atributo=nome_atributo,
                        inicio=dados_estudo["inicio"],
                        fim=dados_estudo["fim"]
                    )
                )

                historico_atributo = resultado_historico[
                    "dados"
                ]

                historico_preparado = (
                    preparar_historico_seguro(
                        historico_atributo
                    )
                )

                tempo_atributo = (
                    time.perf_counter()
                    - inicio_atributo
                )

                if tempo_atributo >= 5:

                    st.warning(
                        f"🐢 Consulta lenta: "
                        f"**{nome_elemento} | "
                        f"{nome_atributo}** "
                        f"levou {tempo_atributo:.1f} s."
                    )

                if not historico_preparado.empty:

                    if prefixo_variavel:

                        nome_variavel = (
                            f"{prefixo_variavel} | "
                            f"{nome_atributo}"
                        )

                    else:

                        nome_variavel = (
                            nome_atributo
                        )

                    historicos_comparacao[
                        nome_variavel
                    ] = historico_preparado

                    total_validos += 1

            except Exception:

                tempo_atributo = (
                    time.perf_counter()
                    - inicio_atributo
                )

                st.caption(
                    f"⚠️ {nome_elemento} | "
                    f"{nome_atributo}: "
                    f"consulta ignorada "
                    f"({tempo_atributo:.1f} s)."
                )

            barra_atributos.progress(
                indice / total_candidatos
            )

        barra_atributos.empty()

        tempo_elemento = (
            time.perf_counter()
            - inicio_elemento
        )

        st.success(
            f"✅ {nome_elemento}: "
            f"{total_atributos} atributos encontrados → "
            f"{total_candidatos} consultados → "
            f"{total_validos} históricos numéricos válidos → "
            f"{total_ignorados} consultas evitadas → "
            f"{tempo_elemento:.1f} s."
        )

        return (
            total_atributos,
            total_candidatos,
            total_validos,
            tempo_elemento
        )

    # ======================================================
    # SOMENTE ELEMENTO SELECIONADO
    # ======================================================

    if (
        escopo
        == "Somente o elemento selecionado"
    ):

        carregar_elemento(
            caminho_elemento=contexto["caminho"],
            prefixo_variavel=None,
            ignorar_variavel_principal=True
        )

        tempo_total = (
            time.perf_counter()
            - inicio_total
        )

        status_execucao.success(
            f"✅ Consulta concluída em "
            f"{tempo_total:.1f} s."
        )

        detalhe_execucao.empty()

        return historicos_comparacao

    # ======================================================
    # EXPLORAÇÃO AMPLIADA
    # ======================================================

    if escopo == "Exploração ampliada":

        caminho_contexto = contexto.get(
            "caminho_contexto",
            contexto["caminho"]
        )

        status_execucao.info(
            "🔎 Mapeando contexto ampliado..."
        )

        try:

            elementos_contexto = listar_elementos(
                servidor=contexto["servidor"],
                database=contexto["database"],
                caminho_elementos=caminho_contexto
            )

        except Exception as erro:

            st.warning(
                "Não foi possível consultar os elementos "
                f"do contexto ampliado: {erro}"
            )

            return historicos_comparacao

        if not elementos_contexto:

            st.warning(
                "O contexto ampliado selecionado não "
                "possui elementos filhos disponíveis."
            )

            return historicos_comparacao

        st.markdown(
            "#### 🔎 Elementos incluídos na exploração"
        )

        st.caption(
            "Nesta etapa serão analisados somente os "
            "filhos diretos do contexto selecionado. "
            "Os atributos são filtrados antes da consulta "
            "ao histórico do PI."
        )

        st.write(
            " • ".join(
                elementos_contexto
            )
        )

        barra_elementos = st.progress(0)

        total_elementos = len(
            elementos_contexto
        )

        resumo_tempos = []

        # ==================================================
        # CONSULTA DOS FILHOS DIRETOS
        # ==================================================

        for indice, nome_elemento in enumerate(
            elementos_contexto,
            start=1
        ):

            caminho_filho = (
                caminho_contexto
                + [nome_elemento]
            )

            elemento_origem_principal = (
                caminho_filho
                == contexto["caminho"]
            )

            (
                total_atributos,
                total_candidatos,
                total_validos,
                tempo
            ) = carregar_elemento(
                caminho_elemento=caminho_filho,
                prefixo_variavel=nome_elemento,
                ignorar_variavel_principal=(
                    elemento_origem_principal
                )
            )

            resumo_tempos.append({
                "elemento":
                    nome_elemento,

                "atributos_encontrados":
                    total_atributos,

                "candidatos_consultados":
                    total_candidatos,

                "historicos_validos":
                    total_validos,

                "consultas_evitadas":
                    max(
                        total_atributos
                        - total_candidatos,
                        0
                    ),

                "tempo_s":
                    round(
                        tempo,
                        1
                    ),
            })

            barra_elementos.progress(
                indice / total_elementos
            )

        barra_elementos.empty()

        tempo_total = (
            time.perf_counter()
            - inicio_total
        )

        status_execucao.success(
            f"✅ Exploração concluída em "
            f"{tempo_total:.1f} s."
        )

        detalhe_execucao.empty()

        # ==================================================
        # RESUMO DE DESEMPENHO
        # ==================================================

        if resumo_tempos:

            st.markdown(
                "#### ⏱️ Desempenho da consulta"
            )

            dataframe_tempos = pd.DataFrame(
                resumo_tempos
            )

            st.dataframe(
                dataframe_tempos,
                width="stretch",
                hide_index=True
            )

            total_encontrados = int(
                dataframe_tempos[
                    "atributos_encontrados"
                ].sum()
            )

            total_consultados = int(
                dataframe_tempos[
                    "candidatos_consultados"
                ].sum()
            )

            total_evitados = int(
                dataframe_tempos[
                    "consultas_evitadas"
                ].sum()
            )

            st.info(
                f"🧠 Pré-filtro de engenharia: "
                f"{total_encontrados} atributos encontrados → "
                f"{total_consultados} históricos consultados → "
                f"{total_evitados} consultas ao PI evitadas."
            )

        return historicos_comparacao

    # ======================================================
    # OUTROS ESCOPOS
    # ======================================================

    st.info(
        "Este escopo ainda não possui estratégia "
        "específica. Será utilizado somente o "
        "elemento selecionado."
    )

    carregar_elemento(
        caminho_elemento=contexto["caminho"],
        prefixo_variavel=None,
        ignorar_variavel_principal=True
    )

    tempo_total = (
        time.perf_counter()
        - inicio_total
    )

    status_execucao.success(
        f"✅ Consulta concluída em "
        f"{tempo_total:.1f} s."
    )

    detalhe_execucao.empty()

    return historicos_comparacao

# ==========================================================
# BASE DE CONHECIMENTO DOCUMENTAL
# ==========================================================

def renderizar_base_conhecimento():
    """
    Permite carregar um manual técnico em PDF e mantê-lo
    processado na sessão do Streamlit.

    Nesta fase da POC:
    - o documento é carregado localmente;
    - o texto é dividido em trechos pesquisáveis;
    - os trechos ficam em session_state;
    - o motor de processo não depende do caminho físico do PDF.

    Futuramente a mesma camada poderá receber documentos
    vindos de SharePoint, planilhas e outras fontes.
    """

    st.divider()

    st.subheader(
        "📚 Base de Conhecimento de Engenharia"
    )

    st.caption(
        "Carregue um manual técnico para complementar a investigação "
        "com referências documentais. O documento não substitui os "
        "dados do PI nem as evidências calculadas pelo motor."
    )

    arquivo_manual = st.file_uploader(
        "Manual ou documento técnico (PDF)",
        type=["pdf"],
        key="arquivo_base_conhecimento_ete",
        help=(
            "Para a POC, utilize o MO-ETE-001. "
            "A arquitetura foi preparada para outras fontes no futuro."
        ),
    )

    # ------------------------------------------------------
    # NENHUM NOVO ARQUIVO SELECIONADO
    # ------------------------------------------------------

    if arquivo_manual is None:

        documento_atual = st.session_state.get(
            "documento_base_conhecimento_ete"
        )

        trechos_atuais = st.session_state.get(
            "trechos_base_conhecimento_ete",
            []
        )

        if documento_atual and trechos_atuais:

            nome_documento = documento_atual.get(
                "nome",
                "Documento técnico"
            )

            st.success(
                f"✅ Base documental ativa: **{nome_documento}** — "
                f"{len(trechos_atuais)} trechos disponíveis."
            )

        else:

            st.info(
                "Nenhum documento técnico foi carregado nesta sessão. "
                "A investigação continuará funcionando somente com as "
                "evidências calculadas a partir dos dados do processo."
            )

        return

    # ------------------------------------------------------
    # IDENTIFICA O CONTEÚDO DO ARQUIVO
    # ------------------------------------------------------

    conteudo_pdf = arquivo_manual.getvalue()

    hash_documento = hashlib.sha256(
        conteudo_pdf
    ).hexdigest()

    hash_atual = st.session_state.get(
        "hash_base_conhecimento_ete"
    )

    trechos_atuais = st.session_state.get(
        "trechos_base_conhecimento_ete",
        []
    )

    # Evita reprocessar o mesmo PDF a cada rerun do Streamlit.
    if hash_atual == hash_documento and trechos_atuais:

        st.success(
            f"✅ **{arquivo_manual.name}** já está indexado nesta sessão — "
            f"{len(trechos_atuais)} trechos disponíveis."
        )

        return

    caminho_temporario = None

    try:

        with st.spinner(
            "Lendo e indexando o documento técnico..."
        ):

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf"
            ) as arquivo_temporario:

                arquivo_temporario.write(
                    conteudo_pdf
                )

                caminho_temporario = Path(
                    arquivo_temporario.name
                )

            trechos = criar_trechos_pdf(
                caminho_temporario
            )

        if not trechos:

            st.warning(
                "O PDF foi recebido, mas nenhum texto pesquisável "
                "foi extraído."
            )

            return

        documento = {
            "nome": arquivo_manual.name,
            "tipo": "PDF",
            "origem": "LOCAL",
            "hash_sha256": hash_documento,
            "total_trechos": len(trechos),
        }

        st.session_state[
            "documento_base_conhecimento_ete"
        ] = documento

        st.session_state[
            "trechos_base_conhecimento_ete"
        ] = trechos

        st.session_state[
            "hash_base_conhecimento_ete"
        ] = hash_documento

        # Uma nova base documental muda o contexto disponível para a IA.
        st.session_state[
            "resultado_ia_estudo_processo"
        ] = None

        st.success(
            f"✅ **{arquivo_manual.name}** indexado com sucesso — "
            f"{len(trechos)} trechos pesquisáveis."
        )

        st.caption(
            "O documento foi processado localmente e seus trechos "
            "ficaram disponíveis para a investigação desta sessão."
        )

    except Exception as erro:

        st.error(
            "Não foi possível processar o documento técnico: "
            f"{erro}"
        )

    finally:

        if caminho_temporario is not None:

            try:
                caminho_temporario.unlink(
                    missing_ok=True
                )
            except Exception:
                pass


# ==========================================================
# INTERPRETAÇÃO COM IA
# ==========================================================

def renderizar_interpretacao_ia():
    """
    Renderiza a camada de IA usando o contexto determinístico
    salvo na sessão.

    A função é independente da execução do estudo porque qualquer
    clique em um botão do Streamlit provoca um novo rerun.
    """

    contexto_ia = st.session_state.get(
        "contexto_ia_estudo_processo"
    )

    if not contexto_ia:
        return

    st.divider()

    st.markdown(
        "## 🤖 Interpretação com IA"
    )

    st.caption(
        "A IA interpreta as evidências produzidas pelo motor "
        "determinístico. Ela não recalcula os resultados, não "
        "confirma causa raiz e não executa alterações no processo."
    )

    status_ollama = verificar_ollama()

    if not status_ollama.get("disponivel"):

        st.warning(
            "O serviço local do Ollama não está acessível "
            "neste momento."
        )

        erro_ollama = status_ollama.get("erro")

        if erro_ollama:
            st.caption(
                f"Detalhe técnico: {erro_ollama}"
            )

        return

    modelos = status_ollama.get(
        "modelos",
        []
    )

    if not modelos:

        st.warning(
            "O Ollama está acessível, mas nenhum modelo "
            "local foi encontrado."
        )

        return

    modelo_padrao = "llama3.2:3b"

    indice_modelo = (
        modelos.index(modelo_padrao)
        if modelo_padrao in modelos
        else 0
    )

    modelo_ia = st.selectbox(
        "Modelo local",
        options=modelos,
        index=indice_modelo,
        key="modelo_ia_estudo_processo"
    )

    if st.button(
        "🤖 Interpretar investigação com IA",
        key="interpretar_investigacao_ia"
    ):

        with st.spinner(
            "Interpretando as evidências de engenharia..."
        ):

            resultado_ia = consultar_ia(
                contexto_ia=contexto_ia,
                provedor="OLLAMA",
                modelo=modelo_ia,
            )

        st.session_state[
            "resultado_ia_estudo_processo"
        ] = resultado_ia

    resultado_ia = st.session_state.get(
        "resultado_ia_estudo_processo"
    )

    if not resultado_ia:
        st.info(
            "Clique no botão acima para solicitar uma leitura "
            "técnica das evidências já calculadas."
        )
        return

    if not resultado_ia.get("ok"):

        st.error(
            "Não foi possível gerar a interpretação com IA."
        )

        erro_ia = resultado_ia.get("erro")

        if erro_ia:
            st.caption(
                f"Detalhe técnico: {erro_ia}"
            )

        return

    st.success(
        f"Interpretação gerada localmente com "
        f"**{resultado_ia.get('modelo', modelo_ia)}**."
    )

    st.markdown(
        resultado_ia.get(
            "resposta",
            ""
        )
    )

    st.warning(
        "⚠️ A interpretação da IA é apoio à investigação. "
        "As evidências numéricas continuam sendo fornecidas "
        "pelo motor determinístico e a validação final cabe "
        "à engenharia de processo."
    )


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

    1. Carrega variável principal.
    2. Carrega variáveis de comparação.
    3. Calcula correlações.
    4. Mostra ranking estatístico.
    5. Gera ranking de engenharia.
    """

    if contexto is None:
        return

    if selecao_estudo is None:
        return

    if dados_estudo is None:
        return

    if not dados_estudo[
        "carregar"
    ]:
        renderizar_interpretacao_ia()
        return

    variavel_principal = (
        selecao_estudo[
            "variavel_principal"
        ]
    )

    try:

        # ==================================================
        # 1. VARIÁVEL PRINCIPAL
        # ==================================================

        with st.spinner(
            "Consultando variável principal no PI..."
        ):

            resultado_principal = (
                carregar_historico_inteligente(
                    servidor=contexto[
                        "servidor"
                    ],
                    database=contexto[
                        "database"
                    ],
                    caminho_elementos=contexto[
                        "caminho"
                    ],
                    nome_atributo=variavel_principal,
                    inicio=dados_estudo[
                        "inicio"
                    ],
                    fim=dados_estudo[
                        "fim"
                    ]
                )
            )

            historico_principal_bruto = resultado_principal[
                "dados"
            ]

            historico_principal = (
                preparar_historico_seguro(
                    historico_principal_bruto
                )
            )

        if historico_principal.empty:

            status_principal = resultado_principal.get(
                "status",
                ""
            )

            estrategia_principal = resultado_principal.get(
                "estrategia",
                ""
            )

            detalhe_principal = resultado_principal.get(
                "detalhe",
                ""
            )

            if status_principal == "FONTE_CALCULADA":

                st.warning(
                    f"**{variavel_principal}** é um atributo "
                    "calculado pelo AF (Analysis/Formula). "
                    "A consulta histórica automática foi "
                    "evitada para não provocar reavaliações "
                    "lentas no AF."
                )

                st.caption(
                    detalhe_principal
                )

            else:

                st.warning(
                    "Não foram encontrados dados numéricos "
                    "válidos para a variável principal."
                )

                st.caption(
                    f"Estratégia: {estrategia_principal or 'não identificada'}. "
                    f"{detalhe_principal}"
                )

            return

        st.success(
            f"{len(historico_principal)} registros "
            f"válidos carregados para "
            f"{variavel_principal}."
        )

        # ==================================================
        # VALIDAÇÃO DA JANELA REAL DE DADOS
        # ==================================================

        periodo_solicitado = dados_estudo.get(
            "periodo_solicitado",
            "Período não informado"
        )

        primeiro_registro = (
            historico_principal["data_hora"].min()
        )

        ultimo_registro = (
            historico_principal["data_hora"].max()
        )

        cobertura = (
            ultimo_registro
            - primeiro_registro
        )

        cobertura_horas = (
            cobertura.total_seconds()
            / 3600
        )

        cobertura_dias = (
            cobertura_horas
            / 24
        )

        mapa_horas_solicitadas = {
            "Últimas 24 horas": 24,
            "Últimos 7 dias": 24 * 7,
            "Últimos 30 dias": 24 * 30,
        }

        horas_solicitadas = (
            mapa_horas_solicitadas.get(
                periodo_solicitado
            )
        )

        if horas_solicitadas:

            cobertura_pct = (
                cobertura_horas
                / horas_solicitadas
                * 100
            )

        else:

            cobertura_pct = None

        st.markdown(
            "### 📅 Cobertura real dos dados"
        )

        col_periodo, col_registros = st.columns(
            2
        )

        with col_periodo:

            st.metric(
                "Período solicitado",
                periodo_solicitado
            )

        with col_registros:

            st.metric(
                "Registros válidos",
                len(
                    historico_principal
                )
            )

        st.write(
            f"🕐 **Primeiro registro válido:** "
            f"{primeiro_registro.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        st.write(
            f"🕐 **Último registro válido:** "
            f"{ultimo_registro.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        if cobertura_dias >= 1:

            texto_cobertura = (
                f"{cobertura_dias:.2f} dias"
            )

        else:

            texto_cobertura = (
                f"{cobertura_horas:.2f} horas"
            )

        if cobertura_pct is not None:

            st.write(
                f"⏱️ **Cobertura observada:** "
                f"{texto_cobertura} "
                f"({cobertura_pct:.1f}% da janela solicitada)"
            )

            if cobertura_pct < 70:

                st.warning(
                    "⚠️ A cobertura real da variável principal "
                    "é significativamente menor que a janela "
                    "solicitada. Correlações e análises temporais "
                    "devem ser interpretadas com cautela."
                )

            elif cobertura_pct < 90:

                st.info(
                    "ℹ️ A variável principal cobre a maior parte "
                    "da janela solicitada, mas existem lacunas "
                    "ou ausência de eventos nas extremidades."
                )

            else:

                st.success(
                    "✅ A variável principal apresenta boa "
                    "cobertura temporal para a janela solicitada."
                )

        else:

            st.write(
                f"⏱️ **Cobertura observada:** "
                f"{texto_cobertura}"
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
            "Calculando relações entre "
            "as variáveis..."
        ):

            ranking_correlacoes = (
                gerar_ranking_correlacoes(
                    historico_principal=
                        historico_principal,
                    historicos_comparacao=
                        historicos_comparacao,
                    nome_principal=
                        variavel_principal
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

        ranking_resultado = (
            ranking_correlacoes.copy()
        )

        ranking_resultado[
            "correlacao_numerica"
        ] = pd.to_numeric(
            ranking_resultado[
                "correlacao"
            ],
            errors="coerce"
        )

        ranking_resultado[
            "correlacao_abs"
        ] = ranking_resultado[
            "correlacao_numerica"
        ].abs()

        if (
            "score_prioridade"
            in ranking_resultado.columns
        ):

            ranking_resultado[
                "score_prioridade"
            ] = pd.to_numeric(
                ranking_resultado[
                    "score_prioridade"
                ],
                errors="coerce"
            ).fillna(0)

        else:

            ranking_resultado[
                "score_prioridade"
            ] = 0

        if (
            "pontos_validos"
            in ranking_resultado.columns
        ):

            ranking_resultado[
                "pontos_validos"
            ] = pd.to_numeric(
                ranking_resultado[
                    "pontos_validos"
                ],
                errors="coerce"
            ).fillna(0)

        else:

            ranking_resultado[
                "pontos_validos"
            ] = 0

        # ==================================================
        # 5. RANKING ESTATÍSTICO
        # ==================================================

        ranking_estatistico = (
            ranking_resultado
            .sort_values(
                by="correlacao_abs",
                ascending=False
            )
            .reset_index(
                drop=True
            )
        )

        st.divider()

        st.markdown(
            "## 🔗 Variáveis mais relacionadas"
        )

        st.caption(
            f"Ranking estatístico das variáveis "
            f"relacionadas a **{variavel_principal}**, "
            "ordenado pela intensidade absoluta "
            "da correlação."
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

            if coluna
            in ranking_estatistico.columns
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

        ranking_validos = (
            ranking_estatistico
            .dropna(
                subset=[
                    "correlacao_numerica"
                ]
            )
        )

        if not ranking_validos.empty:

            maior_associacao = (
                ranking_validos.iloc[0]
            )

            nome_estatistico = (
                maior_associacao[
                    "variavel"
                ]
            )

            correlacao_estatistica = (
                maior_associacao[
                    "correlacao_numerica"
                ]
            )

            tipo_estatistico = (
                maior_associacao.get(
                    "tipo_variavel",
                    "NÃO CLASSIFICADA"
                )
            )

            categoria_estatistica = (
                maior_associacao.get(
                    "categoria_engenharia",
                    "NÃO CLASSIFICADA"
                )
            )

            st.markdown(
                "### 📊 Maior associação estatística"
            )

            st.info(
                f"**{nome_estatistico}** apresentou "
                f"a maior associação estatística com "
                f"**{variavel_principal}**, "
                f"com correlação "
                f"**{correlacao_estatistica:.3f}**. "
                f"A variável é classificada como "
                f"**{tipo_estatistico} | "
                f"{categoria_estatistica}**."
            )

         # ==================================================
        # 7. PRIORIDADE DE ENGENHARIA
        # ==================================================

        ranking_engenharia = (
            ranking_resultado
            .dropna(
                subset=[
                    "correlacao_numerica"
                ]
            )
            .copy()
        )

        pesos_relacao = {

            "RELAÇÃO DE PROCESSO":
                4,

            "RELAÇÃO OPERACIONAL":
                3,

            "RELAÇÃO CALCULADA":
                2,

            "RELAÇÃO DERIVADA / KPI":
                1,

            "RELAÇÃO NÃO CLASSIFICADA":
                0,
        }

        if (
            "tipo_relacao"
            in ranking_engenharia.columns
        ):

            ranking_engenharia[
                "peso_relacao_engenharia"
            ] = ranking_engenharia[
                "tipo_relacao"
            ].map(
                pesos_relacao
            ).fillna(0)

        else:

            ranking_engenharia[
                "peso_relacao_engenharia"
            ] = 0

        # ==================================================
        # SCORE DE RELEVÂNCIA DE ENGENHARIA
        # ==================================================

        if (
            "peso_relevancia"
            in ranking_engenharia.columns
        ):

            ranking_engenharia[
                "score_engenharia"
            ] = (
                ranking_engenharia[
                    "score_prioridade"
                ]
                + ranking_engenharia[
                    "peso_relevancia"
                ]
            )

        else:

            ranking_engenharia[
                "score_engenharia"
            ] = ranking_engenharia[
                "score_prioridade"
            ]

        # ==================================================
        # ORDENAÇÃO FINAL DE ENGENHARIA
        # ==================================================

        ranking_engenharia = (
            ranking_engenharia
            .sort_values(
                by=[
                    "score_engenharia",
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
            .reset_index(
                drop=True
            )
        )

        # ==================================================
        # 8. TABELA DE PRIORIDADE
        # ==================================================

        st.divider()

        st.markdown(
            "## 🎯 Prioridades para "
            "Investigação de Engenharia"
        )

        st.caption(
            "O score de prioridade é o critério "
            "principal. Em caso de empate, relações "
            "físicas de processo são priorizadas "
            "em relação a variáveis calculadas ou KPIs."
        )

        ranking_engenharia[
            "ordem_investigacao"
        ] = range(
            1,
            len(
                ranking_engenharia
            ) + 1
        )

        colunas_engenharia = [

            coluna

            for coluna in [

                "ordem_investigacao",
                "variavel",
                "tipo_variavel",
                "categoria_engenharia",
                "relevancia_engenharia",
                "tipo_relacao",
                "correlacao",
                "classificacao",
                "confiabilidade",
                "pontos_validos",
                "score_prioridade",
                "score_engenharia",
                "prioridade_investigacao",



            ]

            if coluna
            in ranking_engenharia.columns
        ]

        st.dataframe(
            ranking_engenharia[
                colunas_engenharia
            ].head(10),
            width="stretch",
            hide_index=True
        )

        # ==================================================
        # 9. PRINCIPAL CANDIDATO
        # ==================================================

        if not ranking_engenharia.empty:

            candidato = (
                ranking_engenharia.iloc[0]
            )

            nome_candidato = (
                candidato[
                    "variavel"
                ]
            )

            categoria_candidato = (
                candidato.get(
                    "categoria_engenharia",
                    "NÃO CLASSIFICADA"
                )
            )

            tipo_candidato = (
                candidato.get(
                    "tipo_variavel",
                    "NÃO CLASSIFICADA"
                )
            )

            relacao_candidato = (
                candidato.get(
                    "tipo_relacao",
                    "RELAÇÃO NÃO CLASSIFICADA"
                )
            )

            correlacao_candidato = (
                candidato[
                    "correlacao_numerica"
                ]
            )

            score_candidato = int(
                candidato[
                    "score_prioridade"
                ]
            )

            prioridade_candidato = (
                candidato.get(
                    "prioridade_investigacao",
                    "NÃO AVALIADA"
                )
            )

            st.markdown(
                "### 🔎 Principal candidato "
                "para investigação de engenharia"
            )

            st.success(
                f"**{nome_candidato}** foi priorizada "
                f"como primeiro candidato para "
                f"investigação em relação a "
                f"**{variavel_principal}**. "
                f"É uma variável "
                f"**{tipo_candidato}**, "
                f"da categoria "
                f"**{categoria_candidato}**, "
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

        # ==================================================
        # 10. ANÁLISE TEMPORAL DOS PRINCIPAIS CANDIDATOS
        # ==================================================

        st.divider()

        st.markdown(
            "## 🕒 Análise Temporal"
        )

        st.caption(
            "Avalia se a maior associação ocorre sem "
            "deslocamento ou com defasagem temporal. "
            "O motor faz uma busca ampla entre -24 h e +24 h "
            "em passos de 60 minutos e depois refina a região "
            "mais promissora em passos de 15 minutos."
        )

        candidatos_temporais = (
            ranking_engenharia
            .dropna(
                subset=[
                    "correlacao_numerica"
                ]
            )
            .copy()
        )

        # Evita levar para a análise temporal relações
        # simultâneas com dados claramente insuficientes.
        candidatos_temporais = (
            candidatos_temporais[
                candidatos_temporais[
                    "pontos_validos"
                ] >= 5
            ]
            .head(3)
        )

        resultados_temporais = []

        if candidatos_temporais.empty:

            st.info(
                "Não há candidatos com dados suficientes "
                "para a análise temporal."
            )

        else:

            with st.spinner(
                "Analisando defasagem temporal dos "
                "principais candidatos..."
            ):

                for _, linha_candidato in (
                    candidatos_temporais.iterrows()
                ):

                    nome_temporal = str(
                        linha_candidato[
                            "variavel"
                        ]
                    )

                    historico_temporal = (
                        historicos_comparacao.get(
                            nome_temporal
                        )
                    )

                    if (
                        historico_temporal is None
                        or historico_temporal.empty
                    ):
                        continue

                    try:

                        resultado_defasagem = (
                            analisar_defasagem(
                                historico_principal=
                                    historico_principal,
                                historico_comparacao=
                                    historico_temporal,
                                nome_principal=
                                    variavel_principal,
                                nome_comparacao=
                                    nome_temporal,
                                minimo_pontos=10
                            )
                        )

                        interpretacao_temporal = (
                            interpretar_defasagem(
                                resultado_defasagem,
                                nome_principal=
                                    variavel_principal,
                                nome_comparacao=
                                    nome_temporal
                            )
                        )

                        melhor_defasagem = (
                            interpretacao_temporal[
                                "melhor_defasagem"
                            ]
                        )

                        melhor_correlacao = (
                            interpretacao_temporal[
                                "melhor_correlacao"
                            ]
                        )

                        correlacao_base = (
                            interpretacao_temporal[
                                "correlacao_base"
                            ]
                        )

                        ganho_correlacao = (
                            interpretacao_temporal[
                                "ganho_correlacao"
                            ]
                        )

                        pontos_temporais = int(
                            interpretacao_temporal[
                                "pontos_validos"
                            ]
                        )

                        relevancia_temporal = (
                            interpretacao_temporal[
                                "relevancia"
                            ]
                        )

                        if melhor_defasagem is None:

                            defasagem_texto = (
                                "Não determinada"
                            )

                        elif melhor_defasagem == 0:

                            defasagem_texto = (
                                "0 min"
                            )

                        elif melhor_defasagem > 0:

                            horas = (
                                melhor_defasagem
                                // 60
                            )
                            minutos_restantes = (
                                melhor_defasagem
                                % 60
                            )

                            if horas > 0 and minutos_restantes > 0:
                                defasagem_texto = (
                                    f"+{horas} h "
                                    f"{minutos_restantes} min"
                                )
                            elif horas > 0:
                                defasagem_texto = (
                                    f"+{horas} h"
                                )
                            else:
                                defasagem_texto = (
                                    f"+{melhor_defasagem} min"
                                )

                        else:

                            minutos_abs = abs(
                                melhor_defasagem
                            )
                            horas = (
                                minutos_abs
                                // 60
                            )
                            minutos_restantes = (
                                minutos_abs
                                % 60
                            )

                            if horas > 0 and minutos_restantes > 0:
                                defasagem_texto = (
                                    f"-{horas} h "
                                    f"{minutos_restantes} min"
                                )
                            elif horas > 0:
                                defasagem_texto = (
                                    f"-{horas} h"
                                )
                            else:
                                defasagem_texto = (
                                    f"{melhor_defasagem} min"
                                )

                        if melhor_defasagem is None:
                            classe_direcao = "NÃO DETERMINADA"
                        elif melhor_defasagem > 0:
                            classe_direcao = "ANTECIPA A PRINCIPAL"
                        elif melhor_defasagem < 0:
                            classe_direcao = "DIREÇÃO INVERSA"
                        else:
                            classe_direcao = "SIMULTÂNEA"

                        score_temporal = (
                            calcular_score_evidencia_temporal(
                                melhor_correlacao=
                                    melhor_correlacao,
                                correlacao_base=
                                    correlacao_base,
                                ganho_correlacao=
                                    ganho_correlacao,
                                pontos_validos=
                                    pontos_temporais,
                                melhor_defasagem=
                                    melhor_defasagem
                            )
                        )

                        resultados_temporais.append({
                            "variavel":
                                nome_temporal,
                            "direcao_temporal":
                                classe_direcao,
                            "defasagem":
                                defasagem_texto,
                            "melhor_correlacao":
                                melhor_correlacao,
                            "correlacao_sem_defasagem":
                                correlacao_base,
                            "ganho_abs_correlacao":
                                ganho_correlacao,
                            "pontos_validos":
                                pontos_temporais,
                            "relevancia_temporal":
                                relevancia_temporal,
                            "score_evidencia_temporal":
                                score_temporal[
                                    "score_evidencia_temporal"
                                ],
                            "classificacao_evidencia_temporal":
                                score_temporal[
                                    "classificacao_evidencia_temporal"
                                ],
                            "_melhor_defasagem":
                                melhor_defasagem,
                            "_interpretacao":
                                interpretacao_temporal[
                                    "interpretacao"
                                ],
                            "_direcao_temporal":
                                interpretacao_temporal[
                                    "direcao_temporal"
                                ],
                        })

                    except Exception as erro_temporal:

                        resultados_temporais.append({
                            "variavel":
                                nome_temporal,
                            "direcao_temporal":
                                "NÃO DETERMINADA",
                            "defasagem":
                                "Erro",
                            "melhor_correlacao":
                                None,
                            "correlacao_sem_defasagem":
                                None,
                            "ganho_abs_correlacao":
                                None,
                            "pontos_validos":
                                0,
                            "relevancia_temporal":
                                "NÃO AVALIADA",
                            "score_evidencia_temporal":
                                0,
                            "classificacao_evidencia_temporal":
                                "NÃO AVALIADA",
                            "_melhor_defasagem":
                                None,
                            "_interpretacao":
                                (
                                    "Não foi possível avaliar "
                                    f"a defasagem: {erro_temporal}"
                                ),
                            "_direcao_temporal":
                                "Não foi possível determinar",
                        })

            if resultados_temporais:

                df_temporal = pd.DataFrame(
                    resultados_temporais
                )

                colunas_temporais = [
                    "variavel",
                    "direcao_temporal",
                    "defasagem",
                    "melhor_correlacao",
                    "correlacao_sem_defasagem",
                    "ganho_abs_correlacao",
                    "pontos_validos",
                    "score_evidencia_temporal",
                    "classificacao_evidencia_temporal",
                    "relevancia_temporal",
                ]

                st.dataframe(
                    df_temporal[
                        colunas_temporais
                    ],
                    width="stretch",
                    hide_index=True
                )

                # Para investigação antecipatória, somente
                # relações em que a variável candidata antecede
                # a principal podem ser destacadas.
                antecedentes = df_temporal[
                    df_temporal[
                        "direcao_temporal"
                    ] == "ANTECIPA A PRINCIPAL"
                ].copy()

                st.markdown(
                    "### 🔎 Evidência temporal em destaque"
                )

                if antecedentes.empty:

                    st.info(
                        "Nenhuma das variáveis avaliadas apresentou "
                        "antecedência temporal em relação à variável "
                        f"principal {variavel_principal}. "
                        "Relações simultâneas ou em direção inversa "
                        "não são tratadas como indicadores antecipadores."
                    )

                else:

                    pesos_temporais = {
                        "ALTA": 4,
                        "MODERADA": 3,
                        "BAIXA": 2,
                        "MUITO BAIXA": 1,
                        "NÃO AVALIADA": 0,
                    }

                    antecedentes[
                        "_peso_temporal"
                    ] = antecedentes[
                        "relevancia_temporal"
                    ].map(
                        pesos_temporais
                    ).fillna(0)

                    antecedentes[
                        "_correlacao_abs"
                    ] = pd.to_numeric(
                        antecedentes[
                            "melhor_correlacao"
                        ],
                        errors="coerce"
                    ).abs().fillna(0)

                    destaque_temporal = (
                        antecedentes
                        .sort_values(
                            by=[
                                "score_evidencia_temporal",
                                "_peso_temporal",
                                "_correlacao_abs",
                                "pontos_validos",
                            ],
                            ascending=[
                                False,
                                False,
                                False,
                                False,
                            ]
                        )
                        .iloc[0]
                    )

                    pontos_destaque = int(
                        destaque_temporal[
                            "pontos_validos"
                        ]
                    )

                    classificacao_oficial = str(
                        destaque_temporal[
                            "classificacao_evidencia_temporal"
                        ]
                    )

                    nome_destaque = str(
                        destaque_temporal[
                            "variavel"
                        ]
                    )

                    defasagem_destaque = str(
                        destaque_temporal[
                            "defasagem"
                        ]
                    )

                    melhor_corr_destaque = float(
                        destaque_temporal[
                            "melhor_correlacao"
                        ]
                    )

                    correlacao_base_destaque = (
                        destaque_temporal[
                            "correlacao_sem_defasagem"
                        ]
                    )

                    ganho_destaque = (
                        destaque_temporal[
                            "ganho_abs_correlacao"
                        ]
                    )

                    texto_oficial = (
                        f"**{nome_destaque}** antecede "
                        f"**{variavel_principal}** em aproximadamente "
                        f"**{defasagem_destaque.replace('+', '')}**, "
                        f"com correlação máxima de "
                        f"**{melhor_corr_destaque:.3f}** "
                    )

                    if (
                        correlacao_base_destaque is not None
                        and not pd.isna(
                            correlacao_base_destaque
                        )
                    ):

                        texto_oficial += (
                            f"(correlação sem defasagem: "
                            f"**{float(correlacao_base_destaque):.3f}**"
                        )

                        if (
                            ganho_destaque is not None
                            and not pd.isna(
                                ganho_destaque
                            )
                        ):
                            texto_oficial += (
                                f"; ganho absoluto: "
                                f"**{float(ganho_destaque):.3f}**"
                            )

                        texto_oficial += "). "

                    texto_oficial += (
                        f"A evidência temporal foi classificada como "
                        f"**{classificacao_oficial}**, "
                        f"com **{pontos_destaque} pares válidos**."
                    )

                    if classificacao_oficial in [
                        "FORTE",
                        "MODERADA"
                    ]:

                        st.success(
                            texto_oficial
                        )

                    else:

                        st.info(
                            texto_oficial
                        )

                    if classificacao_oficial in [
                        "BAIXA",
                        "MUITO BAIXA"
                    ]:

                        st.warning(
                            "A variável antecede a principal, mas "
                            "a evidência ainda é exploratória. "
                            "Ela pode orientar a investigação, "
                            "mas ainda não deve ser tratada como "
                            "indicador antecipador confirmado."
                        )

                    st.metric(
                        "Score de evidência temporal",
                        (
                            f"{int(destaque_temporal['score_evidencia_temporal'])}"
                            f"/100 — "
                            f"{classificacao_oficial}"
                        )
                    )

                st.caption(
                    "⚠️ Precedência temporal e correlação "
                    "não comprovam causalidade. Resultados com "
                    "poucos pares válidos devem ser tratados "
                    "como evidência exploratória."
                )

                # ==============================================
                # 11. HIPÓTESES DE ENGENHARIA
                # ==============================================

                st.divider()

                st.markdown(
                    "## 🧠 Hipóteses para Investigação de Engenharia"
                )

                st.caption(
                    "As hipóteses abaixo são geradas de forma "
                    "determinística a partir das evidências já "
                    "calculadas. Elas orientam verificações e não "
                    "representam diagnóstico causal."
                )

                candidatos_hipotese = (
                    df_temporal[
                        df_temporal[
                            "direcao_temporal"
                        ] == "ANTECIPA A PRINCIPAL"
                    ]
                    .copy()
                )

                if candidatos_hipotese.empty:

                    st.info(
                        "Nenhuma variável avaliada apresentou "
                        "antecedência temporal suficiente para "
                        "geração de hipótese antecipatória."
                    )

                else:

                    candidatos_hipotese = (
                        candidatos_hipotese
                        .sort_values(
                            by=[
                                "score_evidencia_temporal",
                                "pontos_validos",
                            ],
                            ascending=[
                                False,
                                False,
                            ]
                        )
                        .head(3)
                    )

                    for indice_hipotese, (
                        _,
                        linha_hipotese
                    ) in enumerate(
                        candidatos_hipotese.iterrows(),
                        start=1
                    ):

                        hipotese = (
                            gerar_hipotese_engenharia_temporal(
                                variavel_principal=
                                    variavel_principal,
                                variavel_candidata=
                                    linha_hipotese[
                                        "variavel"
                                    ],
                                defasagem_texto=
                                    linha_hipotese[
                                        "defasagem"
                                    ],
                                melhor_correlacao=
                                    linha_hipotese[
                                        "melhor_correlacao"
                                    ],
                                correlacao_base=
                                    linha_hipotese[
                                        "correlacao_sem_defasagem"
                                    ],
                                ganho_correlacao=
                                    linha_hipotese[
                                        "ganho_abs_correlacao"
                                    ],
                                pontos_validos=
                                    linha_hipotese[
                                        "pontos_validos"
                                    ],
                                score_evidencia_temporal=
                                    linha_hipotese[
                                        "score_evidencia_temporal"
                                    ],
                                classificacao_evidencia_temporal=
                                    linha_hipotese[
                                        "classificacao_evidencia_temporal"
                                    ],
                                direcao_temporal=
                                    linha_hipotese[
                                        "direcao_temporal"
                                    ],
                            )
                        )

                        titulo_hipotese = (
                            f"Hipótese {indice_hipotese} — "
                            f"{linha_hipotese['variavel']} "
                            f"[{hipotese['prioridade_hipotese']}]"
                        )

                        with st.expander(
                            titulo_hipotese,
                            expanded=(
                                indice_hipotese == 1
                            )
                        ):

                            st.markdown(
                                "### Hipótese"
                            )

                            st.write(
                                hipotese[
                                    "hipotese"
                                ]
                            )

                            st.markdown(
                                "### Evidências utilizadas"
                            )

                            for evidencia in (
                                hipotese[
                                    "evidencias"
                                ]
                            ):

                                st.write(
                                    f"- {evidencia}"
                                )

                            st.markdown(
                                "### O que verificar no processo"
                            )

                            for verificacao in (
                                hipotese[
                                    "verificacoes_sugeridas"
                                ]
                            ):

                                st.write(
                                    f"- {verificacao}"
                                )

                            st.warning(
                                hipotese[
                                    "limitacao"
                                ]
                            )

                    # ==========================================
                    # 12. INVESTIGAÇÃO ASSISTIDA
                    # ==========================================

                    hipoteses_para_consolidacao = []

                    for _, linha_hip in (
                        candidatos_hipotese.iterrows()
                    ):

                        hipoteses_para_consolidacao.append({
                            "variavel":
                                linha_hip["variavel"],
                            "defasagem":
                                linha_hip["defasagem"],
                            "melhor_correlacao":
                                linha_hip["melhor_correlacao"],
                            "correlacao_sem_defasagem":
                                linha_hip["correlacao_sem_defasagem"],
                            "ganho_abs_correlacao":
                                linha_hip["ganho_abs_correlacao"],
                            "pontos_validos":
                                int(
                                    linha_hip["pontos_validos"]
                                ),
                            "score_evidencia_temporal":
                                int(
                                    linha_hip[
                                        "score_evidencia_temporal"
                                    ]
                                ),
                            "classificacao_evidencia_temporal":
                                linha_hip[
                                    "classificacao_evidencia_temporal"
                                ],
                        })

                    cobertura_pct_investigacao = None

                    if horas_solicitadas:

                        cobertura_pct_investigacao = (
                            cobertura_pct
                        )

                    # ==========================================
                    # CONHECIMENTO DOCUMENTAL DA INVESTIGAÇÃO
                    # ==========================================

                    conhecimento_documental = []

                    trechos_conhecimento = st.session_state.get(
                        "trechos_base_conhecimento_ete",
                        []
                    )

                    documento_conhecimento = st.session_state.get(
                        "documento_base_conhecimento_ete"
                    )

                    consulta_documental = None

                    if trechos_conhecimento:

                        termos_consulta = [
                            str(variavel_principal)
                        ]

                        for hipotese_item in (
                            hipoteses_para_consolidacao[:3]
                        ):

                            variavel_hipotese = hipotese_item.get(
                                "variavel"
                            )

                            if variavel_hipotese:
                                termos_consulta.append(
                                    str(variavel_hipotese)
                                )

                        # Termos físicos complementares ajudam a busca
                        # documental do POC sem alterar a análise estatística.
                        termos_consulta.extend([
                            "oxigênio dissolvido",
                            "tanque de aeração",
                            "tempo de detenção",
                            "carga orgânica",
                            "vazão",
                        ])

                        consulta_documental = " ".join(
                            termos_consulta
                        )

                        resultados_documentais = buscar_trechos(
                            trechos=trechos_conhecimento,
                            consulta=consulta_documental,
                            limite=5,
                        )

                        for resultado in resultados_documentais:

                            conhecimento_documental.append({
                                "documento": (
                                    documento_conhecimento.get(
                                        "nome",
                                        "Documento técnico"
                                    )
                                    if isinstance(
                                        documento_conhecimento,
                                        dict
                                    )
                                    else str(
                                        documento_conhecimento
                                        or "Documento técnico"
                                    )
                                ),
                                "tipo": (
                                    documento_conhecimento.get(
                                        "tipo",
                                        "PDF"
                                    )
                                    if isinstance(
                                        documento_conhecimento,
                                        dict
                                    )
                                    else "PDF"
                                ),
                                "origem": (
                                    documento_conhecimento.get(
                                        "origem",
                                        "LOCAL"
                                    )
                                    if isinstance(
                                        documento_conhecimento,
                                        dict
                                    )
                                    else "LOCAL"
                                ),
                                "pagina": resultado.get(
                                    "pagina"
                                ),
                                "id_trecho": resultado.get(
                                    "id_trecho"
                                ),
                                "pontuacao_busca": resultado.get(
                                    "pontuacao_busca"
                                ),
                                "termos_encontrados": resultado.get(
                                    "termos_encontrados",
                                    []
                                ),
                                "texto": resultado.get(
                                    "texto",
                                    ""
                                ),
                            })

                    investigacao = (
                        consolidar_investigacao_assistida(
                            variavel_principal=
                                variavel_principal,
                            hipoteses=
                                hipoteses_para_consolidacao,
                            cobertura_principal_pct=
                                cobertura_pct_investigacao,
                            registros_principal=
                                len(
                                    historico_principal
                                ),
                            conhecimento_documental=
                                conhecimento_documental,
                        )
                    )

                    st.divider()

                    st.markdown(
                        "## 🧭 Investigação Assistida"
                    )

                    st.caption(
                        "Consolidação das evidências para orientar "
                        "a próxima ação do engenheiro. Esta etapa "
                        "ainda é determinística e será a base segura "
                        "para a futura camada de IA."
                    )

                    st.info(
                        investigacao[
                            "resumo"
                        ]
                    )

                    # ==========================================
                    # REFERÊNCIAS DOCUMENTAIS RECUPERADAS
                    # ==========================================

                    if conhecimento_documental:

                        st.markdown(
                            "### 📚 Conhecimento documental recuperado"
                        )

                        st.caption(
                            "Trechos recuperados automaticamente da base "
                            "documental a partir da variável principal e das "
                            "hipóteses desta investigação."
                        )

                        for indice_doc, item_doc in enumerate(
                            conhecimento_documental,
                            start=1
                        ):

                            pagina_doc = item_doc.get(
                                "pagina"
                            )

                            documento_doc = item_doc.get(
                                "documento",
                                "Documento técnico"
                            )

                            titulo_doc = (
                                f"Referência {indice_doc} — "
                                f"{documento_doc}"
                            )

                            if pagina_doc is not None:
                                titulo_doc += (
                                    f" — pág. {pagina_doc}"
                                )

                            with st.expander(
                                titulo_doc,
                                expanded=(indice_doc == 1)
                            ):

                                st.write(
                                    item_doc.get(
                                        "texto",
                                        ""
                                    )
                                )

                                termos_doc = item_doc.get(
                                    "termos_encontrados",
                                    []
                                )

                                if termos_doc:
                                    st.caption(
                                        "Termos relacionados: "
                                        + ", ".join(termos_doc)
                                    )

                        if consulta_documental:

                            with st.expander(
                                "🔎 Consulta documental utilizada"
                            ):
                                st.write(
                                    consulta_documental
                                )

                    else:

                        st.caption(
                            "📚 Nenhuma referência documental foi associada. "
                            "Carregue um manual na Base de Conhecimento para "
                            "enriquecer a investigação."
                        )

                    col_evidencias, col_lacunas = st.columns(
                        2
                    )

                    with col_evidencias:

                        st.markdown(
                            "### Evidências-chave"
                        )

                        for evidencia in (
                            investigacao[
                                "evidencias_chave"
                            ]
                        ):

                            st.write(
                                f"- {evidencia}"
                            )

                    with col_lacunas:

                        st.markdown(
                            "### O que ainda reduz a confiança"
                        )

                        if investigacao[
                            "lacunas"
                        ]:

                            for lacuna in (
                                investigacao[
                                    "lacunas"
                                ]
                            ):

                                st.write(
                                    f"- {lacuna}"
                                )

                        else:

                            st.write(
                                "- Nenhuma lacuna crítica "
                                "identificada nesta etapa."
                            )

                    st.markdown(
                        "### Próximos passos recomendados"
                    )

                    for passo in (
                        investigacao[
                            "proximos_passos"
                        ]
                    ):

                        st.write(
                            f"- {passo}"
                        )

                    with st.expander(
                        "🔒 Contexto estruturado para futura IA"
                    ):

                        st.json(
                            investigacao[
                                "contexto_ia"
                            ]
                        )

                        st.caption(
                            "A futura IA deverá interpretar este "
                            "contexto sem alterar os valores calculados "
                            "e sem transformar hipótese em causalidade."
                        )

                    # ------------------------------------------
                    # CONTEXTO REAL DISPONÍVEL PARA A CAMADA DE IA
                    # ------------------------------------------

                    novo_contexto_ia = investigacao[
                        "contexto_ia"
                    ]

                    contexto_anterior = st.session_state.get(
                        "contexto_ia_estudo_processo"
                    )

                    # Se uma nova investigação produzir outro contexto,
                    # a resposta anterior da IA não deve permanecer na tela.
                    if contexto_anterior != novo_contexto_ia:

                        st.session_state[
                            "resultado_ia_estudo_processo"
                        ] = None

                    st.session_state[
                        "contexto_ia_estudo_processo"
                    ] = novo_contexto_ia

                    renderizar_interpretacao_ia()

            else:

                st.info(
                    "Nenhuma análise temporal válida "
                    "foi produzida."
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

    col1, col2 = st.columns(
        2
    )

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
    # BASE DE CONHECIMENTO
    # ======================================================

    renderizar_base_conhecimento()

    # ======================================================
    # CONTEXTO DO PROCESSO
    # ======================================================

    contexto = (
        renderizar_contexto_processo()
    )

    # ======================================================
    # VARIÁVEL PRINCIPAL E ESCOPO
    # ======================================================

    selecao_estudo = (
        renderizar_variavel_e_escopo(
            contexto
        )
    )

    # ======================================================
    # DADOS DO ESTUDO
    # ======================================================

    dados_estudo = (
        renderizar_dados_estudo(
            periodo_estudo=
                periodo_estudo,
            contexto=
                contexto,
            selecao_estudo=
                selecao_estudo
        )
    )

    # ======================================================
    # EXECUÇÃO
    # ======================================================

    executar_estudo_processo(
        contexto=contexto,
        selecao_estudo=selecao_estudo,
        dados_estudo=dados_estudo
    )