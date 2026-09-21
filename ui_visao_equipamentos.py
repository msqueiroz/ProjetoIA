import re
import time
import unicodedata

import pandas as pd
import streamlit as st

from adaptador_pi_af import (
    inventariar_familia_operacional,
    listar_databases,
    listar_elementos,
)
from unidades_engenharia import formatar_unidade_engenharia


ESTADOS = [
    "EM OPERAÇÃO",
    "DISPONÍVEL PARADO",
    "EM MANUTENÇÃO",
    "INDISPONÍVEL/FALHA",
    "PARADO — CONDIÇÃO NÃO CONFIRMADA",
    "NÃO DETERMINADO",
]


@st.cache_data(ttl=300, show_spinner=False)
def _listar_databases(servidor):
    return list(listar_databases(servidor))


@st.cache_data(ttl=300, show_spinner=False)
def _listar_areas(servidor, database):
    return list(listar_elementos(servidor, database, []))


def _normalizar(valor):
    texto_original = "" if valor is None else str(valor)
    texto = unicodedata.normalize("NFKD", texto_original)
    return "".join(
        caractere for caractere in texto
        if not unicodedata.combining(caractere)
    ).lower().strip()


def _numero(valor):
    texto = ("" if valor is None else str(valor)).strip().replace(",", ".")
    correspondencia = re.search(r"[-+]?\d+(?:\.\d+)?", texto)
    if not correspondencia:
        return None
    try:
        return float(correspondencia.group())
    except ValueError:
        return None


def _verdadeiro(valor):
    texto = _normalizar(valor)
    numero = _numero(valor)
    return (
        texto in {"true", "sim", "yes", "on", "ligado", "aberto", "ativo", "running"}
        or (numero is not None and numero > 0)
    )


def _falso(valor):
    texto = _normalizar(valor)
    numero = _numero(valor)
    return (
        texto in {"false", "nao", "no", "off", "desligado", "fechado", "parado", "stopped"}
        or numero == 0
    )


def _formatar_evidencia(linha):
    atributo = str(linha.get("atributo", ""))
    valor = linha.get("valor_atual", "")
    unidade = formatar_unidade_engenharia(linha.get("uom", ""))
    numero = _numero(valor)

    if numero is not None and unidade:
        valor_formatado = f"{numero:.2f}".replace(".", ",")
        return f"{atributo}={valor_formatado} {unidade}"

    return f"{atributo}={valor}"


def classificar_equipamento(grupo):
    sinais = []
    manutencao = []
    falha = []
    operacao = []
    pronto = []
    parada = []

    for _, linha in grupo.iterrows():
        atributo = _normalizar(linha.get("atributo"))
        valor = linha.get("valor_atual", "")
        leitura = _formatar_evidencia(linha)

        if str(linha.get("status_leitura", "")).upper() != "OK":
            continue

        if any(termo in atributo for termo in ("manut", "maintenance", "em reparo")):
            if _verdadeiro(valor):
                manutencao.append(leitura)
            continue

        if any(termo in atributo for termo in ("falha", "fault", "trip", "alarme", "defeito")):
            valor_normalizado = _normalizar(valor)
            if _verdadeiro(valor) or (
                not _falso(valor)
                and valor_normalizado not in {"", "normal", "ok", "sem falha"}
            ):
                falha.append(leitura)
            continue

        if any(termo in atributo for termo in ("dispon", "pronto", "ready", "liberad")):
            if _verdadeiro(valor):
                pronto.append(leitura)
            continue

        if any(termo in atributo for termo in ("ligado", "running", "rodando", "operacao", "estado", "status")):
            if _verdadeiro(valor):
                operacao.append(leitura)
            elif _falso(valor):
                parada.append(leitura)
            continue

        if any(termo in atributo for termo in ("corrente", "amper", "current", "rotacao", "velocidade", "speed")):
            numero = _numero(valor)
            if numero is not None and numero > 0.1:
                operacao.append(leitura)
            elif numero == 0:
                parada.append(leitura)

    if manutencao:
        estado, evidencias = "EM MANUTENÇÃO", manutencao
    elif falha:
        estado, evidencias = "INDISPONÍVEL/FALHA", falha
    elif operacao:
        estado, evidencias = "EM OPERAÇÃO", operacao
    elif pronto and parada:
        estado, evidencias = "DISPONÍVEL PARADO", pronto + parada
    elif parada:
        estado, evidencias = "PARADO — CONDIÇÃO NÃO CONFIRMADA", parada
    else:
        estado, evidencias = "NÃO DETERMINADO", sinais

    return estado, " | ".join(evidencias[:3]) or "Nenhum sinal operacional conclusivo"


def consolidar_equipamentos(inventario):
    if inventario.empty:
        return pd.DataFrame()

    caminhos = {
        str(caminho)
        for caminho in inventario["caminho_elemento"].dropna().unique()
    }
    agregadores = {
        caminho
        for caminho in caminhos
        if any(
            outro != caminho and outro.startswith(caminho + " > ")
            for outro in caminhos
        )
        or re.fullmatch(
            r"ta\s*-?\s*\d+",
            _normalizar(caminho.split(" > ")[-1]),
        )
    }

    registros = []
    for caminho, grupo in inventario.groupby("caminho_elemento", dropna=False):
        caminho = str(caminho)
        estado, evidencia = classificar_equipamento(grupo)
        leituras_validas = grupo[grupo["status_leitura"].astype(str).str.upper() == "OK"]
        timestamps = leituras_validas["timestamp"].dropna().astype(str)
        registros.append({
            "Área / equipamento": caminho,
            "Tipo de item": "ÁREA / AGRUPADOR" if caminho in agregadores else "EQUIPAMENTO",
            "Estado inferido": estado,
            "Evidência utilizada": evidencia,
            "Sinais encontrados": len(grupo),
            "Sinais válidos": len(leituras_validas),
            "Última referência temporal": timestamps.max() if not timestamps.empty else "",
        })

    return pd.DataFrame(registros).sort_values(
        ["Estado inferido", "Área / equipamento"]
    ).reset_index(drop=True)


def renderizar_visao_equipamentos():
    st.subheader("Visão de Equipamentos")
    st.caption(
        "Painel piloto em somente leitura. Os estados são inferidos dos sinais "
        "existentes no PI/AF e sempre apresentam sua evidência."
    )

    servidor = st.text_input(
        "Servidor PI/AF",
        value="CE-SRV11",
        key="equipamentos_servidor",
    )

    try:
        databases = _listar_databases(servidor)
    except Exception as erro:
        st.error(f"Não foi possível consultar o servidor PI/AF: {erro}")
        return

    if not databases:
        st.warning("Nenhuma base AF foi encontrada.")
        return

    indice_ete = databases.index("ETE") if "ETE" in databases else 0
    database = st.selectbox(
        "Base operacional",
        databases,
        index=indice_ete,
        key="equipamentos_database",
    )

    try:
        areas = _listar_areas(servidor, database)
    except Exception as erro:
        st.error(f"Não foi possível listar as áreas da base: {erro}")
        return

    if not areas:
        st.warning("A base selecionada não possui áreas cadastradas no primeiro nível.")
        return

    area = st.selectbox(
        "Área para visão operacional",
        areas,
        key="equipamentos_area",
    )

    if st.button("🔄 Atualizar estados pelo PI", key="equipamentos_atualizar", type="primary"):
        with st.spinner("Consultando a estrutura e os valores atuais do PI/AF..."):
            try:
                inicio = time.perf_counter()
                inventario = inventariar_familia_operacional(
                    servidor=servidor,
                    database=database,
                    caminho_pai=[area],
                )
                st.session_state["equipamentos_resultado"] = consolidar_equipamentos(inventario)
                st.session_state["equipamentos_contexto"] = (servidor, database, area)
                st.session_state["equipamentos_desempenho"] = {
                    "tempo_s": time.perf_counter() - inicio,
                    "sinais_lidos": int((inventario["status_leitura"] == "OK").sum()),
                }
            except Exception as erro:
                st.error(f"Não foi possível montar a visão da área: {erro}")
                return

    contexto = st.session_state.get("equipamentos_contexto")
    painel = st.session_state.get("equipamentos_resultado")
    if contexto != (servidor, database, area) or painel is None:
        st.info("Selecione a área e clique em Atualizar estados pelo PI.")
        return
    if "Tipo de item" not in painel.columns:
        st.info("A regra de contagem foi atualizada. Clique novamente em Atualizar estados pelo PI.")
        return

    desempenho = st.session_state.get("equipamentos_desempenho", {})
    if desempenho:
        st.success(
            f"Atualização concluída em {desempenho.get('tempo_s', 0):.1f} s — "
            f"{desempenho.get('sinais_lidos', 0)} sinais operacionais lidos."
        )

    equipamentos = painel[painel["Tipo de item"] == "EQUIPAMENTO"].copy()
    agregadores = painel[painel["Tipo de item"] == "ÁREA / AGRUPADOR"].copy()

    contagens = equipamentos["Estado inferido"].value_counts()
    colunas = st.columns(5)
    indicadores = [
        ("Em operação", "EM OPERAÇÃO"),
        ("Disponíveis parados", "DISPONÍVEL PARADO"),
        ("Em manutenção", "EM MANUTENÇÃO"),
        ("Falha/indisponíveis", "INDISPONÍVEL/FALHA"),
        ("A confirmar", "NÃO DETERMINADO"),
    ]
    for coluna, (rotulo, estado) in zip(colunas, indicadores):
        coluna.metric(rotulo, int(contagens.get(estado, 0)))

    parados_incerto = int(contagens.get("PARADO — CONDIÇÃO NÃO CONFIRMADA", 0))
    if parados_incerto:
        st.warning(
            f"{parados_incerto} equipamento(s) aparece(m) parado(s), mas o PI/AF não "
            "forneceu evidência suficiente para afirmar disponibilidade ou manutenção."
        )

    filtro = st.multiselect(
        "Filtrar estados",
        ESTADOS,
        default=ESTADOS,
        key="equipamentos_filtro_estado",
    )
    st.dataframe(
        equipamentos[equipamentos["Estado inferido"].isin(filtro)],
        width="stretch",
        hide_index=True,
    )

    if not agregadores.empty:
        st.caption(
            f"{len(agregadores)} área(s) ou agrupador(es) foram excluídos da "
            "contagem de equipamentos."
        )
        with st.expander("Ver indicadores agregados das áreas"):
            st.dataframe(
                agregadores,
                width="stretch",
                hide_index=True,
            )

    st.caption(
        "O painel não transforma automaticamente equipamento desligado em disponível. "
        "Para essa confirmação, o cadastro precisa conter sinais de pronto/liberado, "
        "falha e manutenção."
    )
