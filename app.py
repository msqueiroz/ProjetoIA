import streamlit as st
import pandas as pd

from motor_diagnostico import diagnosticar_parada
from qualidade_dados import gerar_relatorio_qualidade
from adaptador_fontes import carregar_e_preparar_fonte


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

aba1, aba2, aba3 = st.tabs([
    "Visão Operacional",
    "Qualidade dos Dados",
    "Assistente"
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

    st.info(
        "Aqui vamos fazer perguntas sobre eventos "
        "e consultar o manual."
    )