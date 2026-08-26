import streamlit as st
import pandas as pd

from motor_diagnostico import diagnosticar_parada
from qualidade_dados import gerar_relatorio_qualidade
from adaptador_fontes import carregar_e_preparar_fonte
from gerenciador_perfis import salvar_perfil
from manual import (
    buscar_no_manual,
    buscar_contexto_diagnostico
)


from normalizador_dinamico import (
    aplicar_mapeamento_dinamico,
    normalizar_unidades_dinamicas
)


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

aba1, aba2, aba3, aba4 = st.tabs([
    "Visão Operacional",
    "Qualidade dos Dados",
    "Assistente",
    "Configuração da Fonte"
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

    manual_pdf = st.file_uploader(
        "Carregar manual em PDF:",
        type=["pdf"],
        key="manual_pdf"
    )

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

                st.markdown("## Caso de Engenharia")

                col1, col2 = st.columns(2)

                with col1:
                    st.write(
                        f"**Evento:** {linha_evento['data_hora']}"
                    )

                    st.write(
                        f"**Categoria:** {linha_evento['categoria']}"
                    )

                    st.write(
                        f"**Causa provável:** {linha_evento['causa']}"
                    )

                with col2:
                    st.write(
                        f"**Confiança:** {linha_evento['confianca']}%"
                    )

                st.markdown("### Evidências observadas")

                for evidencia in linha_evento["evidencias"].split(" | "):
                    st.write(f"- {evidencia}")

                st.markdown("### Referência de Engenharia")

                st.write(
                    f"**Documento:** {manual_pdf.name}"
                )

                if contexto["resultados"]:

                    st.success(
                        "Contexto técnico encontrado no manual."
                    )

                    for numero, trecho in enumerate(
                        contexto["resultados"],
                        start=1
                    ):

                        with st.expander(
                            f"Referência técnica {numero}"
                        ):

                            st.text(trecho)

                else:

                    st.info(
                        "Nenhum contexto técnico encontrado "
                        "para esse diagnóstico."
                    )

        else:

            st.info(
                "Nenhum evento diagnosticado está disponível."
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