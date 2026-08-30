import streamlit as st
import pandas as pd



from motor_diagnostico import diagnosticar_parada
from qualidade_dados import gerar_relatorio_qualidade
from adaptador_fontes import carregar_e_preparar_fonte
from gerenciador_perfis import salvar_perfil
from assistente_engenharia import montar_resumo_engenharia
from manual import (
    buscar_no_manual,
    buscar_contexto_diagnostico
)


from normalizador_dinamico import (
    aplicar_mapeamento_dinamico,
    normalizar_unidades_dinamicas
)

from adaptador_pi_af import (
    inventariar_familia,
    avaliar_qualidade_inventario,
    inventariar_atributos,
    comparar_areas,
    consolidar_diagnostico_area,
    resumir_causas_problemas,
    listar_databases,
    listar_elementos,
    listar_atributos,
    carregar_historico_atributo,
)

from motor_estudo_processo import (
    preparar_historico,
    alinhar_series,
    calcular_correlacao,
    gerar_ranking_correlacoes
)

@st.cache_data(ttl=300)
def obter_databases_cache(servidor):
    return listar_databases(servidor)

st.set_page_config(
    page_title="Assistente Engenharia - Projeto Piloto",
    page_icon="⚙️",
    layout="wide"
)

st.title("Assistente de Engenharia - Projeto Piloto")

st.write(
    "Protótipo local para análise de paradas, qualidade de dados "
    "e consulta assistida por IA."
)


# =========================
# SELEÇÃO DA FONTE DE DADOS
# =========================

fonte_selecionada = st.selectbox(
    "Fonte de dados para análise:",
    [
        "CSV - dadosMult.csv",
        "CSV - dados_teste_qualidade.csv",
        "CSV - dados_heterogeneos.csv",
        "PI System - Simulado"
    ]
)


# =========================
# DADOS DO PI SIMULADO
# =========================

dados_pi = [
    {
        "Timestamp": "2026-08-20 08:00:00",
        "Running": 1,
        "Voltage": 440,
        "Current": 18.2,
        "BearingTemperature": 65,
        "Vibration": 2.1,
        "Level": 70,
        "Alarm": "NORMAL"
    },
    {
        "Timestamp": "2026-08-20 08:30:00",
        "Running": 1,
        "Voltage": 440,
        "Current": 18.5,
        "BearingTemperature": 67,
        "Vibration": 2.4,
        "Level": 68,
        "Alarm": "NORMAL"
    },
    {
        "Timestamp": "2026-08-20 09:00:00",
        "Running": 1,
        "Voltage": 439,
        "Current": 18.7,
        "BearingTemperature": 72,
        "Vibration": 5.2,
        "Level": 67,
        "Alarm": "NORMAL"
    },
    {
        "Timestamp": "2026-08-20 09:15:00",
        "Running": 1,
        "Voltage": 440,
        "Current": 18.8,
        "BearingTemperature": 74,
        "Vibration": 8.2,
        "Level": 66,
        "Alarm": "TRIP_VIBRACAO"
    },
    {
        "Timestamp": "2026-08-20 09:25:00",
        "Running": 0,
        "Voltage": 440,
        "Current": 0.0,
        "BearingTemperature": 74,
        "Vibration": 8.2,
        "Level": 66,
        "Alarm": "BOMBA_PARADA"
    }
]


# =========================
# CARREGAR E PREPARAR FONTE
# =========================

resultado_fonte = carregar_e_preparar_fonte(
    fonte_selecionada,
    dados_pi=dados_pi
)

if not resultado_fonte["sucesso"]:

    st.error(
        f"Erro ao carregar a fonte: "
        f"{resultado_fonte['erro']}"
    )

    st.stop()


dados = resultado_fonte["dados"]
origem_dados = resultado_fonte["origem"]
perfil = resultado_fonte["perfil"]
nome_fonte = resultado_fonte["nome_fonte"]
pipeline = resultado_fonte["pipeline"]


# =========================
# QUALIDADE DOS DADOS
# =========================

dados_qualidade = dados.copy()

relatorio = gerar_relatorio_qualidade(
    dados_qualidade
)

pipeline["qualidade_analisada"] = True


# =========================
# DETECTAR PARADAS
# =========================

dados["status_anterior"] = (
    dados["status_bomba"].shift(1)
)

paradas = dados[
    (dados["status_anterior"] == 1) &
    (dados["status_bomba"] == 0)
]


# =========================
# EXECUTAR DIAGNÓSTICOS
# =========================

diagnosticos = []

for indice, parada in paradas.iterrows():

    resultado = diagnosticar_parada(
        dados,
        indice
    )

    diagnosticos.append({
        "data_hora": parada["data_hora"],
        "categoria": resultado["categoria"],
        "causa": resultado["causa"],
        "confianca": resultado["confianca"],
        "evidencias": " | ".join(
            resultado["evidencias"]
        )
    })


df_diagnosticos = pd.DataFrame(
    diagnosticos
)

pipeline["diagnostico_executado"] = True


# =========================
# INFORMAÇÕES DA FONTE
# =========================

st.caption(
    f"Origem: {origem_dados} | "
    f"Fonte: {nome_fonte} | "
    f"Perfil: {perfil} | "
    f"Registros: {len(dados)} | "
    f"Normalização: concluída"
)


# =========================
# PIPELINE DE PROCESSAMENTO
# =========================

with st.expander("🔎 Pipeline de processamento"):

    if pipeline["fonte_carregada"]:
        st.write("✅ Fonte carregada")
    else:
        st.write("❌ Fonte não carregada")

    if pipeline["perfil_identificado"]:
        st.write(
            f"✅ Perfil identificado: {perfil}"
        )
    else:
        st.write(
            "❌ Perfil não identificado"
        )

    if pipeline["mapeamento_concluido"]:
        st.write(
            "✅ Mapeamento de colunas concluído"
        )
    else:
        st.write(
            "❌ Mapeamento de colunas não concluído"
        )

    if pipeline["normalizacao_concluida"]:
        st.write(
            "✅ Normalização concluída"
        )
    else:
        st.write(
            "❌ Normalização não concluída"
        )

    if pipeline["qualidade_analisada"]:
        st.write(
            "✅ Qualidade dos dados analisada"
        )
    else:
        st.write(
            "❌ Qualidade dos dados não analisada"
        )

    if pipeline["diagnostico_executado"]:
        st.write(
            "✅ Diagnóstico executado"
        )
    else:
        st.write(
            "❌ Diagnóstico não executado"
        )

    st.write(
        f"📊 Registros disponíveis: {len(dados)}"
    )


# =========================
# ABAS
# =========================

aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "Visão Operacional",
    "Qualidade dos Dados",
    "Assistente",
    "Configuração da Fonte",
    "Governança PI/AF",
    "Estudo de Processo"
])


# =========================
# ABA 1 - VISÃO OPERACIONAL
# =========================

with aba1:

    st.subheader("Visão Operacional")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Registros analisados",
            len(dados)
        )

    with col2:

        st.metric(
            "Paradas detectadas",
            len(paradas)
        )

    with col3:

        disponibilidade = (
            dados["status_bomba"].mean() * 100
        )

        st.metric(
            "Bomba ligada",
            f"{disponibilidade:.1f}%"
        )

    st.divider()

    st.subheader("Eventos de parada")

    if not df_diagnosticos.empty:

        st.dataframe(
            df_diagnosticos,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "Nenhuma parada detectada na base selecionada."
        )


# =========================
# ABA 2 - QUALIDADE DOS DADOS
# =========================

with aba2:

    st.subheader("Qualidade dos Dados")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.metric(
            "Completude",
            f"{relatorio['completude']:.1f}%"
        )

    with col2:

        st.metric(
            "Valores ausentes",
            relatorio["valores_ausentes"]
        )

    with col3:

        st.metric(
            "Variáveis",
            f"{relatorio['variaveis_presentes']}/"
            f"{relatorio['variaveis_esperadas']}"
        )

    with col4:

        st.metric(
            "Status geral",
            relatorio["status"]
        )

    with col5:

        st.metric(
            "Aptidão para diagnóstico",
            relatorio["aptidao_diagnostico"]
        )

    st.divider()


    # =========================
    # DADOS AUSENTES
    # =========================

    st.subheader(
        "Dados ausentes encontrados"
    )

    if relatorio["detalhes_ausentes"]:

        df_ausentes = pd.DataFrame(
            relatorio["detalhes_ausentes"]
        )

        st.warning(
            f"Foram encontrados "
            f"{relatorio['valores_ausentes']} "
            f"valores ausentes na base."
        )

        st.dataframe(
            df_ausentes,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "Nenhum valor ausente encontrado na base."
        )


    # =========================
    # INCONSISTÊNCIAS
    # =========================

    st.subheader(
        "Inconsistências"
    )

    if relatorio["inconsistencias"]:

        for problema in relatorio["inconsistencias"]:
            st.warning(problema)

    else:

        st.success(
            "Nenhuma inconsistência detectada."
        )


    # =========================
    # CONTINUIDADE TEMPORAL
    # =========================

    st.subheader(
        "Continuidade temporal"
    )

    if relatorio["gaps_temporais"]:

        st.warning(
            f"Foram detectados "
            f"{relatorio['quantidade_gaps']} "
            f"gaps temporais na base."
        )

        df_gaps = pd.DataFrame(
            relatorio["gaps_temporais"]
        )

        st.dataframe(
            df_gaps,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "Nenhum gap temporal detectado."
        )


# =========================
# ABA 3 - ASSISTENTE
# =========================

with aba3:

    st.subheader("Assistente")

    st.write(
        "Consulte o manual de operação e localize "
        "informações técnicas relacionadas ao processo."
    )

    # =========================
    # CARREGAMENTO DO MANUAL
    # =========================

    manual_pdf = st.file_uploader(
        "Carregar manual em PDF:",
        type=["pdf"],
        key="manual_pdf"
    )

    # =========================
    # CONSULTA MANUAL
    # =========================

    termo_manual = st.text_input(
        "Buscar no manual:",
        placeholder="Ex.: vibração, nível baixo, subtensão",
        key="termo_manual"
    )

    if st.button(
        "Consultar manual",
        key="consultar_manual"
    ):

        if manual_pdf is None:

            st.warning(
                "Carregue um manual em PDF antes da consulta."
            )

        elif not termo_manual.strip():

            st.warning(
                "Digite um termo para pesquisar."
            )

        else:

            resultados_manual = buscar_no_manual(
                termo_manual,
                manual_pdf
            )

            if resultados_manual:

                st.success(
                    f"Foram encontrados "
                    f"{len(resultados_manual)} "
                    f"trechos relacionados."
                )

                for numero, trecho in enumerate(
                    resultados_manual,
                    start=1
                ):

                    with st.expander(
                        f"Trecho encontrado {numero}"
                    ):

                        st.text(trecho)

            else:

                st.info(
                    "Nenhuma informação encontrada "
                    "para esse termo."
                )

    # =========================
    # CONSULTA AUTOMÁTICA
    # =========================

    st.divider()

    st.subheader(
        "Consulta automática a partir do diagnóstico"
    )

    if manual_pdf is not None:

        if not df_diagnosticos.empty:

            opcoes_eventos = []

            for indice, linha in df_diagnosticos.iterrows():

                texto_evento = (
                    f"{linha['data_hora']} | "
                    f"{linha['causa']}"
                )

                opcoes_eventos.append(
                    (texto_evento, linha)
                )

            evento_escolhido = st.selectbox(
                "Selecione um evento diagnosticado:",
                [item[0] for item in opcoes_eventos],
                key="evento_diagnostico_manual"
            )

            linha_evento = next(
                item[1]
                for item in opcoes_eventos
                if item[0] == evento_escolhido
            )

            if st.button(
                "Buscar contexto técnico",
                key="buscar_contexto_diagnostico"
            ):

                contexto = buscar_contexto_diagnostico(
                    linha_evento["causa"],
                    manual_pdf
                )

                resumo_engenharia = montar_resumo_engenharia(
                    evento=linha_evento["data_hora"],
                    categoria=linha_evento["categoria"],
                    causa=linha_evento["causa"],
                    confianca=linha_evento["confianca"],
                    evidencias=linha_evento["evidencias"].split(" | "),
                    documento=manual_pdf.name,
                    referencias=contexto["resultados"]
                )

                # =========================
                # CASO DE ENGENHARIA
                # =========================

                st.markdown("## Caso de Engenharia")

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        f"**Evento:** "
                        f"{resumo_engenharia['evento']}"
                    )

                    st.write(
                        f"**Categoria:** "
                        f"{resumo_engenharia['categoria']}"
                    )

                    st.write(
                        f"**Causa provável:** "
                        f"{resumo_engenharia['causa']}"
                    )

                with col2:

                    st.write(
                        f"**Confiança:** "
                        f"{resumo_engenharia['confianca']}%"
                    )

                # =========================
                # EVIDÊNCIAS
                # =========================

                st.markdown(
                    "### Evidências observadas"
                )

                for evidencia in (
                    resumo_engenharia["evidencias"]
                ):

                    st.write(
                        f"- {evidencia}"
                    )

                # =========================
                # REFERÊNCIA DE ENGENHARIA
                # =========================

                st.markdown(
                    "### Referência de Engenharia"
                )

                st.write(
                    f"**Documento:** "
                    f"{resumo_engenharia['documento']}"
                )

                if contexto["resultados"]:

                    st.success(
                        "Contexto técnico encontrado "
                        "no manual."
                    )

                    for numero, referencia in enumerate(
                        resumo_engenharia["referencias"],
                        start=1
                    ):

                        pagina = referencia["pagina"]
                        titulo = referencia["titulo"]
                        texto = referencia["texto"]

                        with st.expander(
                            f"{titulo} - Página {pagina}"
                        ):

                            st.write(
                                f"**Seção:** {titulo}"
                            )

                            st.write(
                                f"**Página:** {pagina}"
                            )

                            st.text(texto)      

                else:

                    st.info(
                        "Nenhum contexto técnico encontrado "
                        "para esse diagnóstico."
                    )

        else:

            st.info(
                "Nenhum evento diagnosticado "
                "está disponível."
            )

# =========================
# ABA 4 - CONFIGURAÇÃO DA FONTE
# =========================

with aba4:

    st.subheader("Configuração da Fonte")

    st.write(
        "Nesta área será possível configurar novas fontes "
        "de dados e mapear variáveis para o modelo padrão "
        "do sistema."
    )

    st.divider()

    tipo_fonte_config = st.selectbox(
        "Tipo de fonte:",
        [
            "CSV",
            "PI System"
        ],
        key="tipo_fonte_config"
    )

    nome_configuracao = st.text_input(
        "Nome da configuração:",
        placeholder="Ex.: Elevatória Atlântica"
    )
    # =========================
    # CONFIGURAÇÃO DINÂMICA
    # =========================

    if tipo_fonte_config == "CSV":

        st.markdown("### Configuração CSV")

        arquivo_csv_config = st.file_uploader(
            "Selecione um arquivo CSV:",
            type=["csv"],
            key="arquivo_csv_config"
        )

        separador_csv = st.selectbox(
            "Separador do arquivo:",
            [",", ";", "\t"],
            key="separador_csv"
        )

        if arquivo_csv_config is not None:

            try:

                df_config = pd.read_csv(
                    arquivo_csv_config,
                    sep=separador_csv
                )

                st.success(
                    f"Arquivo carregado com sucesso: "
                    f"{len(df_config)} registros encontrados."
                )

                st.markdown("### Colunas encontradas")

                st.write(
                    list(df_config.columns)
                )

                st.markdown(
                    "### Mapeamento para o modelo padrão"
                )

                colunas_disponiveis = (
                    ["Não mapear"]
                    + list(df_config.columns)
                )

                map_data_hora = st.selectbox(
                    "Data e hora →",
                    colunas_disponiveis,
                    index=(
                        colunas_disponiveis.index(
                            "data_hora"
                        )
                        if "data_hora"
                        in colunas_disponiveis
                        else 0
                    ),
                    key="map_data_hora"
                )

                map_status_bomba = st.selectbox(
                    "Status da bomba →",
                    colunas_disponiveis,
                    index=(
                        colunas_disponiveis.index(
                            "status_bomba"
                        )
                        if "status_bomba"
                        in colunas_disponiveis
                        else 0
                    ),
                    key="map_status_bomba"
                )

                map_tensao = st.selectbox(
                    "Tensão →",
                    colunas_disponiveis,
                    index=(
                        colunas_disponiveis.index(
                            "tensao_v"
                        )
                        if "tensao_v"
                        in colunas_disponiveis
                        else 0
                    ),
                    key="map_tensao"
                )

                unidade_tensao = st.selectbox(
                    "Unidade da tensão na fonte:",
                    [
                        "V",
                        "kV"
                    ],
                    key="unidade_tensao"
                )

                map_corrente = st.selectbox(
                    "Corrente →",
                    colunas_disponiveis,
                    index=(
                        colunas_disponiveis.index(
                            "corrente_a"
                        )
                        if "corrente_a"
                        in colunas_disponiveis
                        else 0
                    ),
                    key="map_corrente"
                )

                map_temperatura = st.selectbox(
                    "Temperatura do mancal →",
                    colunas_disponiveis,
                    index=(
                        colunas_disponiveis.index(
                            "temp_mancal_c"
                        )
                        if "temp_mancal_c"
                        in colunas_disponiveis
                        else 0
                    ),
                    key="map_temperatura"
                )

                unidade_temperatura = st.selectbox(
                    "Unidade da temperatura na fonte:",
                    [
                        "°C",
                        "°F"
                    ],
                    key="unidade_temperatura"
                )

                map_vibracao = st.selectbox(
                    "Vibração →",
                    colunas_disponiveis,
                    index=(
                        colunas_disponiveis.index(
                            "vibracao_mm_s"
                        )
                        if "vibracao_mm_s"
                        in colunas_disponiveis
                        else 0
                    ),
                    key="map_vibracao"
                )

                map_nivel = st.selectbox(
                    "Nível →",
                    colunas_disponiveis,
                    index=(
                        colunas_disponiveis.index(
                            "nivel_pct"
                        )
                        if "nivel_pct"
                        in colunas_disponiveis
                        else 0
                    ),
                    key="map_nivel"
                )

                unidade_nivel = st.selectbox(
                    "Formato do nível na fonte:",
                    [
                        "%",
                        "Fração 0-1"
                    ],
                    key="unidade_nivel"
                )

                map_alarme = st.selectbox(
                    "Alarme →",
                    colunas_disponiveis,
                    index=(
                        colunas_disponiveis.index(
                            "alarme"
                        )
                        if "alarme"
                        in colunas_disponiveis
                        else 0
                    ),
                    key="map_alarme"
                )

                st.divider()

                if st.button(
                    "Pré-visualizar normalização",
                    key="preview_normalizacao"
                ):

                    df_preview = df_config.copy()

                    mapa_dinamico = {}

                    if map_data_hora != "Não mapear":
                        mapa_dinamico[
                            map_data_hora
                        ] = "data_hora"

                    if map_status_bomba != "Não mapear":
                        mapa_dinamico[
                            map_status_bomba
                        ] = "status_bomba"

                    if map_tensao != "Não mapear":
                        mapa_dinamico[
                            map_tensao
                        ] = "tensao_v"

                    if map_corrente != "Não mapear":
                        mapa_dinamico[
                            map_corrente
                        ] = "corrente_a"

                    if map_temperatura != "Não mapear":
                        mapa_dinamico[
                            map_temperatura
                        ] = "temp_mancal_c"

                    if map_vibracao != "Não mapear":
                        mapa_dinamico[
                            map_vibracao
                        ] = "vibracao_mm_s"

                    if map_nivel != "Não mapear":
                        mapa_dinamico[
                            map_nivel
                        ] = "nivel_pct"

                    if map_alarme != "Não mapear":
                        mapa_dinamico[
                            map_alarme
                        ] = "alarme"
                    df_preview = aplicar_mapeamento_dinamico(
                        df_config,
                        mapa_dinamico
                    )

                    df_preview = normalizar_unidades_dinamicas(
                        df_preview,
                        unidade_tensao=unidade_tensao,
                        unidade_temperatura=unidade_temperatura,
                        unidade_nivel=unidade_nivel
                    )
 
                    st.success(
                        "Pré-visualização normalizada "
                        "com sucesso."
                    )

                    st.dataframe(
                        df_preview.head(10),
                        use_container_width=True,
                        hide_index=True
                    )

                if st.button(
                    "Salvar perfil",
                    key="salvar_perfil"
                ):

                    perfil_configurado = {
                        "nome": nome_configuracao,
                        "tipo_fonte": tipo_fonte_config,

                        "mapeamento": {
                            "data_hora": map_data_hora,
                            "status_bomba": map_status_bomba,
                            "tensao_v": map_tensao,
                            "corrente_a": map_corrente,
                            "temp_mancal_c": map_temperatura,
                            "vibracao_mm_s": map_vibracao,
                            "nivel_pct": map_nivel,
                            "alarme": map_alarme
                        },

                        "unidades": {
                            "tensao": unidade_tensao,
                            "temperatura": unidade_temperatura,
                            "nivel": unidade_nivel
                        }
                    }

                    nome_arquivo = nome_configuracao.strip().lower()

                    nome_arquivo = (
                        nome_arquivo
                        .replace(" ", "_")
                        .replace("/", "_")
                        .replace("\\", "_")
                    )

                    caminho_perfil = salvar_perfil(
                        nome_arquivo,
                        perfil_configurado
                    )

                    st.success(
                        f"Perfil salvo com sucesso em: "
                        f"{caminho_perfil}"
                    )

            except Exception as erro:

                st.error(
                    f"Não foi possível ler o arquivo: "
                    f"{erro}"
                )

    elif tipo_fonte_config == "PI System":

        st.markdown("### Configuração PI System")

        st.info(
            "A conexão será inicialmente configurada "
            "somente para leitura."
        )

        servidor_pi = st.text_input(
            "Servidor / endpoint do PI:",
            placeholder="Ex.: servidor-pi",
            key="servidor_pi"
        )

        ativo_pi = st.text_input(
            "Ativo ou equipamento:",
            placeholder="Ex.: Bomba P-101",
            key="ativo_pi"
        )





# =========================
# ABA 5 - GOVERNANÇA PI/AF
# =========================

def classificar_status_area(
    qualidade_pct
):

    if qualidade_pct >= 90:
        return "PRONTO"

    elif qualidade_pct >= 70:
        return "ATENÇÃO"

    else:
        return "CRÍTICO"

with aba5:

    st.subheader("Governança PI/AF")

    st.write(
        "Diagnóstico de qualidade, integridade e "
        "prontidão dos dados de engenharia do PI System."
    )

    st.divider()

    # ========================================
    # SELEÇÃO DINÂMICA DA FONTE PI/AF
    # ========================================

    st.markdown(
        "### Seleção da área para diagnóstico"
    )

    servidor_pi = st.text_input(
        "Servidor PI/AF",
        value="CE-SRV11",
        key="servidor_governanca_pi"
    )

    database_selecionada = None
    elemento_selecionado = None

    # ========================================
    # DATABASES DISPONÍVEIS
    # ========================================

    try:

        databases_disponiveis = obter_databases_cache(
            servidor_pi
        )

        if databases_disponiveis:

            database_selecionada = st.selectbox(
                "Database AF",
                options=databases_disponiveis,
                key="database_governanca_pi"
            )

        else:

            st.warning(
                "Nenhuma database AF foi encontrada "
                "no servidor informado."
            )

    except Exception as erro:

        st.error(
            "Não foi possível consultar as databases AF: "
            f"{erro}"
        )

    # ========================================
    # ELEMENTOS DISPONÍVEIS
    # ========================================

    if database_selecionada:

        try:

            elementos_disponiveis = listar_elementos(
                servidor=servidor_pi,
                database=database_selecionada,
                caminho_elementos=[]
            )

            if elementos_disponiveis:

                elemento_selecionado = st.selectbox(
                    "Elemento / Área",
                    options=elementos_disponiveis,
                    key="elemento_governanca_pi"
                )

            else:

                st.info(
                    "A database selecionada não possui "
                    "elementos disponíveis neste nível."
                )

        except Exception as erro:

            st.error(
                "Não foi possível consultar os elementos "
                f"da database: {erro}"
            )

    # ========================================
    # BOTÃO DE EXECUÇÃO
    # ========================================

    executar_diagnostico = st.button(
        "Executar diagnóstico PI/AF",
        key="executar_diagnostico_pi"
    )

    if executar_diagnostico:

        if (
            not database_selecionada
            or not elemento_selecionado
        ):

            st.warning(
                "Selecione uma database e um elemento "
                "antes de executar o diagnóstico."
            )

        else:

            with st.spinner(
                "Consultando PI AF e avaliando os ativos..."
            ):

                try:

                    # ========================================
                    # INVENTÁRIO DINÂMICO
                    # ========================================

                    inventario_area = inventariar_familia(
                        servidor=servidor_pi,
                        database=database_selecionada,
                        caminho_pai=[
                            elemento_selecionado
                        ]
                    )

                    # ========================================
                    # QUALIDADE
                    # ========================================

                    inventario_area = (
                        avaliar_qualidade_inventario(
                            inventario_area
                        )
                    )

                    # ========================================
                    # IDENTIFICAÇÃO DA ÁREA
                    # ========================================

                    nome_area = (
                        f"{database_selecionada}"
                        f" - {elemento_selecionado}"
                    )

                    # ========================================
                    # COMPARATIVO
                    # ========================================

                    comparativo_area = comparar_areas(
                        {
                            nome_area:
                                inventario_area
                        }
                    )

                    # ========================================
                    # SESSION STATE
                    # ========================================

                    st.session_state[
                        "diagnostico_pi_executado"
                    ] = True

                    st.session_state[
                        "inventario_area_pi"
                    ] = inventario_area

                    st.session_state[
                        "comparativo_pi"
                    ] = comparativo_area

                    st.session_state[
                        "nome_area_pi"
                    ] = nome_area

                    st.session_state[
                        "database_diagnostico_pi"
                    ] = database_selecionada

                    st.session_state[
                        "elemento_diagnostico_pi"
                    ] = elemento_selecionado

                    st.success(
                        "Diagnóstico PI/AF concluído."
                    )

                except Exception as erro:

                    st.error(
                        "Erro durante a execução do diagnóstico: "
                        f"{erro}"
                    )

    # ========================================
    # EXIBIÇÃO PERSISTENTE
    # ========================================

    if st.session_state.get(
        "diagnostico_pi_executado",
        False
    ):

        inventario_area = st.session_state[
            "inventario_area_pi"
        ]

        comparativo = st.session_state[
            "comparativo_pi"
        ]

        nome_area = st.session_state[
            "nome_area_pi"
        ]

        database_diagnostico = st.session_state[
            "database_diagnostico_pi"
        ]

        elemento_diagnostico = st.session_state[
            "elemento_diagnostico_pi"
        ]

        st.divider()

        st.markdown(
            f"## Resultado: {nome_area}"
        )

        # ========================================
        # INDICADORES
        # ========================================

        total_atributos = len(
            inventario_area
        )

        total_ok = int(
            (
                inventario_area[
                    "classificacao_qualidade"
                ] == "OK"
            ).sum()
        )

        total_alertas = int(
            (
                inventario_area[
                    "classificacao_qualidade"
                ] == "ALERTA"
            ).sum()
        )

        total_erros = int(
            (
                inventario_area[
                    "classificacao_qualidade"
                ] == "ERRO"
            ).sum()
        )

        col1, col2, col3, col4 = st.columns(
            4
        )

        col1.metric(
            "Atributos analisados",
            total_atributos
        )

        col2.metric(
            "OK",
            total_ok
        )

        col3.metric(
            "Alertas",
            total_alertas
        )

        col4.metric(
            "Erros",
            total_erros
        )

        # ========================================
        # STATUS DA ÁREA
        # ========================================

        st.divider()

        st.markdown(
            "### Status da área"
        )

        if not comparativo.empty:

            linha_area = comparativo.iloc[
                0
            ]

            qualidade = float(
                linha_area[
                    "qualidade_pct"
                ]
            )

            status_area = classificar_status_area(
                qualidade
            )

            if status_area == "PRONTO":

                icone = "🟢"

            elif status_area == "ATENÇÃO":

                icone = "🟡"

            else:

                icone = "🔴"

            col_area, col_status, col_qualidade = (
                st.columns(
                    [2, 1, 1]
                )
            )

            col_area.markdown(
                f"### {nome_area}"
            )

            col_status.metric(
                "Status",
                f"{icone} {status_area}"
            )

            col_qualidade.metric(
                "Qualidade",
                f"{qualidade:.1f}%"
            )

            st.progress(
                qualidade / 100
            )

            st.caption(
                f"{total_ok} OK | "
                f"{total_alertas} alertas | "
                f"{total_erros} erros"
            )

        # ========================================
        # TABELA RESUMO
        # ========================================

        st.divider()

        st.markdown(
            "### Resumo do diagnóstico"
        )

        st.dataframe(
            comparativo,
            width="stretch",
            hide_index=True
        )

        # ========================================
        # PROBLEMAS DA ÁREA
        # ========================================

        problemas_area = (
            inventario_area[
                inventario_area[
                    "classificacao_qualidade"
                ] != "OK"
            ]
            .copy()
        )

        st.divider()

        st.markdown(
            "### Detalhamento dos problemas"
        )

        if problemas_area.empty:

            st.success(
                "Nenhum problema encontrado "
                "na área selecionada."
            )

        else:

            # ========================================
            # FILTRO POR CLASSIFICAÇÃO
            # ========================================

            classificacoes_disponiveis = sorted(
                problemas_area[
                    "classificacao_qualidade"
                ]
                .dropna()
                .unique()
                .tolist()
            )

            filtro_classificacao = st.multiselect(
                "Classificação",
                options=classificacoes_disponiveis,
                default=classificacoes_disponiveis,
                key=(
                    "filtro_classificacao_"
                    + str(database_diagnostico)
                    + "_"
                    + str(elemento_diagnostico)
                )
            )

            problemas_filtrados = (
                problemas_area[
                    problemas_area[
                        "classificacao_qualidade"
                    ].isin(
                        filtro_classificacao
                    )
                ]
                .copy()
            )

            # ========================================
            # FILTRO POR ELEMENTO
            # ========================================

            elementos_diagnostico = sorted(
                problemas_filtrados[
                    "elemento"
                ]
                .dropna()
                .unique()
                .tolist()
            )

            filtro_elemento = st.multiselect(
                "Elemento",
                options=elementos_diagnostico,
                default=elementos_diagnostico,
                key=(
                    "filtro_elemento_"
                    + str(database_diagnostico)
                    + "_"
                    + str(elemento_diagnostico)
                )
            )

            problemas_filtrados = (
                problemas_filtrados[
                    problemas_filtrados[
                        "elemento"
                    ].isin(
                        filtro_elemento
                    )
                ]
                .copy()
            )

            # ========================================
            # RESUMO DO FILTRO
            # ========================================

            total_problemas = len(
                problemas_filtrados
            )

            erros_filtrados = int(
                (
                    problemas_filtrados[
                        "classificacao_qualidade"
                    ] == "ERRO"
                ).sum()
            )

            alertas_filtrados = int(
                (
                    problemas_filtrados[
                        "classificacao_qualidade"
                    ] == "ALERTA"
                ).sum()
            )

            col_a, col_b, col_c = st.columns(
                3
            )

            col_a.metric(
                "Problemas encontrados",
                total_problemas
            )

            col_b.metric(
                "Erros",
                erros_filtrados
            )

            col_c.metric(
                "Alertas",
                alertas_filtrados
            )

            # ========================================
            # TABELA DE DIAGNÓSTICO
            # ========================================

            colunas_detalhamento = [
                "caminho_elemento",
                "elemento",
                "atributo",
                "data_reference",
                "uom",
                "classificacao_qualidade",
                "categoria_erro",
                "codigo_erro",
                "observacao_qualidade"
            ]

            colunas_detalhamento = [
                coluna
                for coluna
                in colunas_detalhamento
                if coluna
                in problemas_filtrados.columns
            ]

            st.dataframe(
                problemas_filtrados[
                    colunas_detalhamento
                ],
                width="stretch",
                hide_index=True
            )

            # ========================================
            # CAUSAS DOS PROBLEMAS
            # ========================================

            st.divider()

            st.markdown(
                "### Causas dos problemas"
            )

            colunas_necessarias = {
                "categoria_erro",
                "codigo_erro",
                "classificacao_qualidade"
            }

            if colunas_necessarias.issubset(
                problemas_filtrados.columns
            ):

                resumo_causas = (
                    problemas_filtrados
                    .groupby(
                        [
                            "categoria_erro",
                            "codigo_erro",
                            "classificacao_qualidade"
                        ],
                        dropna=False
                    )
                    .size()
                    .reset_index(
                        name="quantidade"
                    )
                    .sort_values(
                        "quantidade",
                        ascending=False
                    )
                )

                st.dataframe(
                    resumo_causas,
                    width="stretch",
                    hide_index=True
                )

                # ========================================
                # DISTRIBUIÇÃO POR CATEGORIA
                # ========================================

                resumo_categoria = (
                    problemas_filtrados
                    .groupby(
                        "categoria_erro",
                        dropna=False
                    )
                    .size()
                    .reset_index(
                        name="quantidade"
                    )
                    .sort_values(
                        "quantidade",
                        ascending=False
                    )
                )

                st.markdown(
                    "#### Distribuição por categoria"
                )

                st.bar_chart(
                    resumo_categoria,
                    x="categoria_erro",
                    y="quantidade"
                )

            else:

                st.warning(
                    "As colunas categoria_erro e codigo_erro "
                    "não estão disponíveis no diagnóstico."
                )

  # =========================
# ABA 6 - ESTUDO DE PROCESSO
# =========================

with aba6:

    st.header("🔬 Estudo de Processo")

    st.info(
        "Módulo destinado à investigação, análise "
        "e melhoria de processos industriais."
    )

    st.subheader("Configuração do Estudo")

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

    # =========================
    # CONTEXTO DO PROCESSO
    # =========================

    st.subheader("Contexto do Processo")

    servidor_estudo = "CE-SRV11"

    try:

        databases_estudo = obter_databases_cache(
            servidor_estudo
        )

        database_estudo = st.selectbox(
            "Database AF",
            options=databases_estudo,
            key="database_estudo_processo"
        )

        elementos_estudo = listar_elementos(
            servidor=servidor_estudo,
            database=database_estudo
        )

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

        # =========================
        # ATRIBUTOS
        # =========================

        atributos_estudo = listar_atributos(
            servidor=servidor_estudo,
            database=database_estudo,
            caminho_elementos=caminho_estudo
        )

        if atributos_estudo:

            # =========================
            # VARIÁVEL PRINCIPAL
            # =========================

            st.subheader("Variável Principal")

            variavel_principal = st.selectbox(
                "Variável que será o foco do estudo",
                options=atributos_estudo,
                key="variavel_principal_estudo"
            )

            # =========================
            # ESCOPO
            # =========================

            st.subheader("Escopo de Análise")

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

            # =========================
            # DADOS DO ESTUDO
            # =========================

            st.subheader("Dados do Estudo")

            periodos_af = {
                "Últimas 24 horas": "*-24h",
                "Últimos 7 dias": "*-7d",
                "Últimos 30 dias": "*-30d"
            }

            if periodo_estudo != "Período personalizado":

                inicio_estudo = periodos_af[
                    periodo_estudo
                ]

                fim_estudo = "*"

                if st.button(
                    "🔬 Carregar dados do estudo",
                    key="carregar_dados_estudo"
                ):

                    try:

                        # =========================
                        # VARIÁVEL PRINCIPAL
                        # =========================

                        with st.spinner(
                            "Consultando dados históricos no PI..."
                        ):

                            historico_principal = (
                                carregar_historico_atributo(
                                    servidor=servidor_estudo,
                                    database=database_estudo,
                                    caminho_elementos=caminho_estudo,
                                    nome_atributo=variavel_principal,
                                    inicio=inicio_estudo,
                                    fim=fim_estudo
                                )
                            )

                            historico_principal = (
                                preparar_historico(
                                    historico_principal
                                )
                            )

                        if historico_principal.empty:

                            st.warning(
                                "Não foram encontrados dados "
                                "numéricos suficientes para a "
                                "variável principal."
                            )

                        else:

                            st.success(
                                f"{len(historico_principal)} "
                                "registros válidos da variável "
                                "principal."
                            )

                            # =========================
                            # OUTRAS VARIÁVEIS
                            # =========================

                            historicos_comparacao = {}

                            with st.spinner(
                                "Analisando as demais variáveis "
                                "do elemento..."
                            ):

                                for nome_atributo in atributos_estudo:

                                    if (
                                        nome_atributo
                                        == variavel_principal
                                    ):
                                        continue

                                    try:

                                        historico_atributo = (
                                            carregar_historico_atributo(
                                                servidor=servidor_estudo,
                                                database=database_estudo,
                                                caminho_elementos=caminho_estudo,
                                                nome_atributo=nome_atributo,
                                                inicio=inicio_estudo,
                                                fim=fim_estudo
                                            )
                                        )

                                        historico_preparado = (
                                            preparar_historico(
                                                historico_atributo
                                            )
                                        )

                                        if not historico_preparado.empty:

                                            historicos_comparacao[
                                                nome_atributo
                                            ] = historico_preparado

                                    except Exception:

                                        continue

                            # =========================
                            # RANKING
                            # =========================

                            if not historicos_comparacao:

                                st.warning(
                                    "Nenhuma outra variável "
                                    "numérica com histórico foi "
                                    "encontrada para comparação."
                                )

                            else:

                                ranking_correlacoes = (
                                    gerar_ranking_correlacoes(
                                        historico_principal=(
                                            historico_principal
                                        ),
                                        historicos_comparacao=(
                                            historicos_comparacao
                                        ),
                                        nome_principal=(
                                            "variavel_principal"
                                        )
                                    )
                                )

                                st.subheader(
                                    "🔗 Variáveis Relacionadas"
                                )

                                if ranking_correlacoes.empty:

                                    st.warning(
                                        "Não foi possível calcular "
                                        "correlações com os dados "
                                        "disponíveis."
                                    )

                                else:

                                    st.dataframe(
                                        ranking_correlacoes,
                                        width="stretch"
                                    )

                    except Exception as erro:

                        st.error(
                            "Não foi possível executar o estudo: "
                            f"{erro}"
                        )

            else:

                st.info(
                    "A seleção de período personalizado "
                    "será implementada na próxima etapa."
                )

        else:

            st.warning(
                "O elemento selecionado não possui "
                "atributos disponíveis para análise."
            )

    except Exception as erro:

        st.error(
            "Não foi possível consultar a estrutura PI/AF: "
            f"{erro}"
        )