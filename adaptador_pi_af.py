import sys
import clr
import pandas as pd


CAMINHO_AFSDK = (
    r"C:\Program Files (x86)"
    r"\PIPC\AF\PublicAssemblies\4.0"
)

sys.path.append(CAMINHO_AFSDK)

clr.AddReference("OSIsoft.AFSDK")

from OSIsoft.AF import PISystems


def conectar_af(
    servidor="CE-SRV11"
):

    sistemas = PISystems()

    sistema = sistemas[servidor]

    if sistema is None:
        raise ValueError(
            f"Servidor AF '{servidor}' não encontrado."
        )

    return sistema


def listar_databases(
    servidor="CE-SRV11"
):

    sistema = conectar_af(
        servidor
    )

    return [
        database.Name
        for database
        in sistema.Databases
    ]

def listar_elementos(
    servidor,
    database,
    caminho_elementos=None
):

    sistema = conectar_af(
        servidor
    )

    banco = sistema.Databases[
        database
    ]

    if banco is None:
        raise ValueError(
            f"Database '{database}' não encontrada."
        )

    elementos = banco.Elements

    if caminho_elementos:

        for nome_elemento in caminho_elementos:
            elemento = elementos[
                nome_elemento
            ]

            if elemento is None:
                raise ValueError(
                    f"Elemento '{nome_elemento}' "
                    f"não encontrado."
                )

            elementos = elemento.Elements

    return [
        elemento.Name
        for elemento in elementos
    ]

def listar_atributos(
    servidor,
    database,
    caminho_elementos
):

    sistema = conectar_af(
        servidor
    )

    banco = sistema.Databases[
        database
    ]

    if banco is None:
        raise ValueError(
            f"Database '{database}' não encontrada."
        )

    elementos = banco.Elements

    elemento_atual = None

    for nome_elemento in caminho_elementos:

        elemento_atual = elementos[
            nome_elemento
        ]

        if elemento_atual is None:
            raise ValueError(
                f"Elemento '{nome_elemento}' "
                f"não encontrado."
            )

        elementos = elemento_atual.Elements

    return [
        atributo.Name
        for atributo in elemento_atual.Attributes
    ]

def obter_valor_atual_atributo(
    servidor,
    database,
    caminho_elementos,
    nome_atributo
):

    sistema = conectar_af(
        servidor
    )

    banco = sistema.Databases[
        database
    ]

    if banco is None:
        raise ValueError(
            f"Database '{database}' não encontrada."
        )

    elementos = banco.Elements

    elemento_atual = None

    for nome_elemento in caminho_elementos:

        elemento_atual = elementos[
            nome_elemento
        ]

        if elemento_atual is None:
            raise ValueError(
                f"Elemento '{nome_elemento}' "
                f"não encontrado."
            )

        elementos = elemento_atual.Elements

    atributo = elemento_atual.Attributes[
        nome_atributo
    ]

    if atributo is None:
        raise ValueError(
            f"Atributo '{nome_atributo}' "
            f"não encontrado."
        )

    valor = atributo.GetValue()

    return {
        "atributo": nome_atributo,
        "valor": str(valor.Value),
        "timestamp": str(valor.Timestamp)
    }

from OSIsoft.AF.Time import AFTimeRange
from OSIsoft.AF.Data import AFBoundaryType

def carregar_historico_atributo(
    servidor,
    database,
    caminho_elementos,
    nome_atributo,
    inicio,
    fim
):

    sistema = conectar_af(
        servidor
    )

    banco = sistema.Databases[
        database
    ]

    if banco is None:
        raise ValueError(
            f"Database '{database}' não encontrada."
        )

    elementos = banco.Elements
    elemento_atual = None

    for nome_elemento in caminho_elementos:

        elemento_atual = elementos[
            nome_elemento
        ]

        if elemento_atual is None:
            raise ValueError(
                f"Elemento '{nome_elemento}' não encontrado."
            )

        elementos = elemento_atual.Elements

    atributo = elemento_atual.Attributes[
        nome_atributo
    ]

    if atributo is None:
        raise ValueError(
            f"Atributo '{nome_atributo}' não encontrado."
        )

    intervalo = AFTimeRange(
        inicio,
        fim
    )

    valores = atributo.Data.RecordedValues(
        intervalo,
        AFBoundaryType.Inside,
        atributo.DefaultUOM,
        "",
        False,
        0
    )

    registros = []

    for valor in valores:

        registros.append({
            "data_hora": str(valor.Timestamp),
            "valor": str(valor.Value)
        })

    df = pd.DataFrame(
        registros
    )

    if not df.empty:

        df["data_hora"] = pd.to_datetime(
            df["data_hora"],
            dayfirst=True,
            errors="coerce"
        )

    return df

def inventariar_atributos(
    servidor,
    database,
    caminho_elementos
):

    sistema = conectar_af(
        servidor
    )

    banco = sistema.Databases[
        database
    ]

    if banco is None:
        raise ValueError(
            f"Database '{database}' não encontrada."
        )

    elementos = banco.Elements
    elemento_atual = None

    for nome_elemento in caminho_elementos:

        elemento_atual = elementos[
            nome_elemento
        ]

        if elemento_atual is None:
            raise ValueError(
                f"Elemento '{nome_elemento}' não encontrado."
            )

        elementos = elemento_atual.Elements

    registros = []

    for atributo in elemento_atual.Attributes:

        try:
            data_reference = str(
                atributo.DataReferencePlugIn.Name
            )
        except Exception:
            data_reference = ""

        try:
            uom = str(
                atributo.DefaultUOM
            )
        except Exception:
            uom = ""

        try:
            valor_af = atributo.GetValue()

            valor = str(
                valor_af.Value
            )

            timestamp = str(
                valor_af.Timestamp
            )

            status = "OK"

        except Exception as erro:

            valor = ""
            timestamp = ""
            status = f"ERRO: {erro}"

        registros.append({
            "servidor": servidor,
            "database": database,
            "elemento": elemento_atual.Name,
            "atributo": atributo.Name,
            "data_reference": data_reference,
            "uom": uom,
            "valor_atual": valor,
            "timestamp": timestamp,
            "status_leitura": status
        })

    return pd.DataFrame(
        registros
    )



def avaliar_qualidade_inventario(
    inventario
):

    resultado = inventario.copy()

    classificacoes = []
    observacoes = []

    for _, linha in resultado.iterrows():

        valor = str(
            linha["valor_atual"]
        ).strip()

        data_reference = str(
            linha["data_reference"]
        ).strip()

        uom = str(
            linha["uom"]
        ).strip()

        classificacao = "OK"
        observacao = ""
        try:
            float(valor.replace(",", "."))
            valor_numerico = True
        except ValueError:
            valor_numerico = False

        if (
            "Calc Failed"
            in valor
        ):
            classificacao = "ERRO"
            observacao = (
                "Cálculo do atributo falhou."
            )

        elif (
            "Pt Created"
            in valor
        ):
            classificacao = "ALERTA"
            observacao = (
                "PI Point aparentemente criado, "
                "mas sem valor operacional válido."
            )

        elif (
            valor == ""
        ):
            classificacao = "ALERTA"
            observacao = (
                "Valor atual vazio."
            )

        elif (
            data_reference == "PI Point"
            and valor_numerico
            and uom in ["", "None"]
        ):
            classificacao = "ALERTA"
            observacao = (
                "PI Point sem unidade de engenharia definida."
            )

        classificacoes.append(
            classificacao
        )

        observacoes.append(
            observacao
        )

    resultado[
        "classificacao_qualidade"
    ] = classificacoes

    resultado[
        "observacao_qualidade"
    ] = observacoes

    return resultado

def inventariar_familia(
    servidor,
    database,
    caminho_pai
):

    sistema = conectar_af(
        servidor
    )

    banco = sistema.Databases[
        database
    ]

    if banco is None:
        raise ValueError(
            f"Database '{database}' não encontrada."
        )

    elementos = banco.Elements
    elemento_pai = None

    for nome_elemento in caminho_pai:

        elemento_pai = elementos[
            nome_elemento
        ]

        if elemento_pai is None:
            raise ValueError(
                f"Elemento '{nome_elemento}' não encontrado."
            )

        elementos = elemento_pai.Elements

    inventarios = []

    for elemento in elementos:

        caminho_filho = (
            caminho_pai
            + [elemento.Name]
        )

        try:

            inventario = inventariar_atributos(
                servidor=servidor,
                database=database,
                caminho_elementos=caminho_filho
            )

            inventarios.append(
                inventario
            )

        except Exception as erro:

            inventarios.append(
                pd.DataFrame([
                    {
                        "servidor": servidor,
                        "database": database,
                        "elemento": elemento.Name,
                        "atributo": "",
                        "data_reference": "",
                        "uom": "",
                        "valor_atual": "",
                        "timestamp": "",
                        "status_leitura": (
                            f"ERRO: {erro}"
                        )
                    }
                ])
            )

    if not inventarios:
        return pd.DataFrame()

    return pd.concat(
        inventarios,
        ignore_index=True
    )

def analisar_consistencia_familia(
    inventario
):

    atributos_por_elemento = {}

    for elemento, grupo in inventario.groupby(
        "elemento"
    ):

        atributos_por_elemento[elemento] = set(
            grupo["atributo"]
            .dropna()
            .astype(str)
        )

    if not atributos_por_elemento:
        return pd.DataFrame()

    todos_atributos = set().union(
        *atributos_por_elemento.values()
    )

    registros = []

    for elemento, atributos in (
        atributos_por_elemento.items()
    ):

        faltantes = sorted(
            todos_atributos - atributos
        )

        extras = sorted(
            atributos - set.intersection(
                *atributos_por_elemento.values()
            )
        )

        registros.append({
            "elemento": elemento,
            "quantidade_atributos": len(
                atributos
            ),
            "atributos_faltantes": (
                ", ".join(faltantes)
                if faltantes
                else ""
            ),
            "atributos_extras": (
                ", ".join(extras)
                if extras
                else ""
            ),
            "estrutura_consistente": (
                len(faltantes) == 0
                and len(extras) == 0
            )
        })

    return pd.DataFrame(
        registros
    )

def resumir_problemas_por_atributo(
    inventario_avaliado
):

    problemas = inventario_avaliado[
        inventario_avaliado[
            "classificacao_qualidade"
        ].isin(
            ["ALERTA", "ERRO"]
        )
    ].copy()

    if problemas.empty:
        return pd.DataFrame()

    resumo = (
        problemas
        .groupby(
            [
                "atributo",
                "classificacao_qualidade",
                "observacao_qualidade"
            ]
        )
        .agg(
            quantidade_ativos=(
                "elemento",
                "nunique"
            )
        )
        .reset_index()
        .sort_values(
            [
                "classificacao_qualidade",
                "quantidade_ativos"
            ],
            ascending=[
                True,
                False
            ]
        )
    )

    return resumo

def resumir_estrutura_familia(
    inventario
):

    if inventario.empty:
        return pd.DataFrame()

    resumo = (
        inventario
        .groupby(
            [
                "atributo",
                "data_reference",
                "uom"
            ],
            dropna=False
        )
        .agg(
            quantidade_ativos=(
                "elemento",
                "nunique"
            )
        )
        .reset_index()
        .sort_values(
            [
                "quantidade_ativos",
                "atributo"
            ],
            ascending=[
                False,
                True
            ]
        )
    )

    total_ativos = (
        inventario["elemento"]
        .nunique()
    )

    resumo[
        "cobertura_pct"
    ] = (
        resumo[
            "quantidade_ativos"
        ]
        / total_ativos
        * 100
    ).round(1)

    return resumo

REGRAS_SEMANTICAS = {
    "Diferencial R-S": "ELÉTRICA",
    "Diferencial R-T": "ELÉTRICA",
    "Diferencial S-T": "ELÉTRICA",
    "KPI Energia": "KPI",
    "Tempo de Vida": "CONDIÇÃO",
    "Nome": "METADADO",
    "Tendência Volume Mês": "PROCESSO"
}

def classificar_atributos_engenharia(
    matriz
):

    resultado = matriz.copy()

    categorias = []

    for atributo in resultado["atributo"]:

        nome = atributo.lower()

        if atributo in REGRAS_SEMANTICAS:

            categorias.append(
            REGRAS_SEMANTICAS[atributo]
            )   

            continue

        if any(
            termo in nome
            for termo in [
                "corrente",
                "tensão",
                "potência",
                "energia"
            ]
        ):
            categoria = "ELÉTRICA"

        elif any(
            termo in nome
            for termo in [
                "nível",
                "pressão",
                "vazão",
                "totalizador"
            ]
        ):
            categoria = "PROCESSO"

        elif any(
            termo in nome
            for termo in [
                "temperatura",
                "vibração"
            ]
        ):
            categoria = "CONDIÇÃO"

        elif "status" in nome:
            categoria = "STATUS"

        elif any(
            termo in nome
            for termo in [
                "kpi",
                "disponibilidade",
                "produtividade",
                "taxa perda"
            ]
        ):
            categoria = "KPI"

        elif any(
            termo in nome
            for termo in [
                "modelo",
                "número",
                "operação",
                "limite",
                "data"
            ]
        ):
            categoria = "METADADO"

        categorias.append(
            categoria
        )

    resultado[
        "categoria_engenharia"
    ] = categorias

    return resultado

def resumir_cobertura_por_categoria(
    matriz_classificada
):

    if matriz_classificada.empty:
        return pd.DataFrame()

    resumo = (
        matriz_classificada
        .groupby(
            "categoria_engenharia"
        )
        .agg(
            quantidade_variaveis=(
                "atributo",
                "nunique"
            ),
            cobertura_media_pct=(
                "cobertura_pct",
                "mean"
            )
        )
        .reset_index()
    )

    resumo[
        "cobertura_media_pct"
    ] = resumo[
        "cobertura_media_pct"
    ].round(1)

    return resumo.sort_values(
        "categoria_engenharia"
    )

def calcular_prontidao_por_categoria(
    inventario_avaliado,
    matriz_classificada
):

    mapa_categoria = dict(
        zip(
            matriz_classificada["atributo"],
            matriz_classificada["categoria_engenharia"]
        )
    )

    dados = inventario_avaliado.copy()

    dados["categoria_engenharia"] = (
        dados["atributo"].map(
            mapa_categoria
        )
    )

    pesos = {
        "OK": 1.0,
        "ALERTA": 0.5,
        "ERRO": 0.0
    }

    dados["peso_qualidade"] = (
        dados["classificacao_qualidade"]
        .map(pesos)
        .fillna(0)
    )

    resumo = (
        dados
        .groupby(
            "categoria_engenharia"
        )
        .agg(
            quantidade_registros=(
                "atributo",
                "count"
            ),
            prontidao_pct=(
                "peso_qualidade",
                "mean"
            )
        )
        .reset_index()
    )

    resumo["prontidao_pct"] = (
        resumo["prontidao_pct"]
        * 100
    ).round(1)

    return resumo.sort_values(
        "categoria_engenharia"
    )

def calcular_score_global_prontidao(
    inventario_avaliado,
    consistencia_familia,
    matriz_classificada
):

    pesos_qualidade = {
        "OK": 1.0,
        "ALERTA": 0.5,
        "ERRO": 0.0
    }

    registros = []

    elementos = (
        inventario_avaliado["elemento"]
        .unique()
    )

    for elemento in elementos:

        dados_elemento = inventario_avaliado[
            inventario_avaliado["elemento"]
            == elemento
        ]

        qualidade = (
            dados_elemento[
                "classificacao_qualidade"
            ]
            .map(
                pesos_qualidade
            )
            .fillna(0)
            .mean()
            * 100
        )

        linha_consistencia = (
            consistencia_familia[
                consistencia_familia["elemento"]
                == elemento
            ]
        )

        if (
            not linha_consistencia.empty
            and linha_consistencia.iloc[0][
                "estrutura_consistente"
            ]
        ):
            estrutura = 100.0
        else:
            estrutura = 0.0

        cobertura = (
            matriz_classificada[
                "cobertura_pct"
            ].mean()
        )

        score_global = (
            estrutura * 0.30
            + qualidade * 0.50
            + cobertura * 0.20
        )

        if score_global >= 90:
            classificacao = "PRONTO"

        elif score_global >= 75:
            classificacao = "ATENÇÃO"

        else:
            classificacao = "CRÍTICO"

        registros.append({
            "elemento": elemento,
            "estrutura_pct": round(
                estrutura,
                1
            ),
            "qualidade_pct": round(
                qualidade,
                1
            ),
            "cobertura_pct": round(
                cobertura,
                1
            ),
            "score_global_pct": round(
                score_global,
                1
            ),
            "classificacao": classificacao
        })

    return pd.DataFrame(
        registros
    )

CRITICIDADE_ATRIBUTOS = {
    "Status do PA": "CRÍTICA",
    "Corrente Média": "CRÍTICA",
    "Tensão": "CRÍTICA",
    "Temperatura": "CRÍTICA",
    "Nível": "CRÍTICA",
    "Pressão": "CRÍTICA",
    "Vazão": "CRÍTICA",

    "Corrente R": "IMPORTANTE",
    "Corrente S": "IMPORTANTE",
    "Corrente T": "IMPORTANTE",
    "Potência": "IMPORTANTE",
    "Disponibilidade Operacional": "IMPORTANTE",
    "Totalizador": "IMPORTANTE",

    "Nome": "APOIO",
    "Número do Poço": "APOIO",
    "Data última troca de bomba": "APOIO"
}

def aplicar_criticidade_atributos(
    inventario_avaliado
):

    resultado = inventario_avaliado.copy()

    criticidades = []

    for atributo in resultado["atributo"]:

        criticidade = CRITICIDADE_ATRIBUTOS.get(
            atributo,
            "APOIO"
        )

        criticidades.append(
            criticidade
        )

    resultado[
        "criticidade"
    ] = criticidades

    return resultado


def calcular_qualidade_ponderada(
    inventario_avaliado
):

    df = inventario_avaliado.copy()

    pesos_criticidade = {
        "CRÍTICA": 5,
        "IMPORTANTE": 3,
        "APOIO": 1
    }

    fatores_qualidade = {
        "OK": 1.0,
        "ALERTA": 0.5,
        "ERRO": 0.0
    }

    df = aplicar_criticidade_atributos(
        df
    )

    df["peso_criticidade"] = (
        df["criticidade"]
        .map(pesos_criticidade)
        .fillna(1)
    )

    df["fator_qualidade"] = (
        df["classificacao_qualidade"]
        .map(fatores_qualidade)
        .fillna(0)
    )

    df["pontos_obtidos"] = (
        df["peso_criticidade"]
        * df["fator_qualidade"]
    )

    resultado = (
        df.groupby("elemento")
        .agg(
            pontos_obtidos=(
                "pontos_obtidos",
                "sum"
            ),
            pontos_possiveis=(
                "peso_criticidade",
                "sum"
            )
        )
        .reset_index()
    )

    resultado["qualidade_ponderada_pct"] = (
        resultado["pontos_obtidos"]
        / resultado["pontos_possiveis"]
        * 100
    ).round(1)

    return resultado

def avaliar_bloqueios_criticidade(
    inventario_avaliado
):

    df = inventario_avaliado.copy()

    # Garante que cada atributo tenha criticidade
    df = aplicar_criticidade_atributos(
        df
    )

    # Indicadores de bloqueio
    df["erro_critico"] = (
        (df["criticidade"] == "CRÍTICA")
        & (df["classificacao_qualidade"] == "ERRO")
    ).astype(int)

    df["alerta_critico"] = (
        (df["criticidade"] == "CRÍTICA")
        & (df["classificacao_qualidade"] == "ALERTA")
    ).astype(int)

    df["erro_importante"] = (
        (df["criticidade"] == "IMPORTANTE")
        & (df["classificacao_qualidade"] == "ERRO")
    ).astype(int)

    df["alerta_importante"] = (
        (df["criticidade"] == "IMPORTANTE")
        & (df["classificacao_qualidade"] == "ALERTA")
    ).astype(int)

    resultado = (
        df.groupby("elemento")
        .agg(
            erros_criticos=(
                "erro_critico",
                "sum"
            ),
            alertas_criticos=(
                "alerta_critico",
                "sum"
            ),
            erros_importantes=(
                "erro_importante",
                "sum"
            ),
            alertas_importantes=(
                "alerta_importante",
                "sum"
            )
        )
        .reset_index()
    )

    # ========================================
    # CLASSIFICAÇÃO DO BLOQUEIO
    # ========================================

    def classificar_bloqueio(linha):

        if linha["erros_criticos"] > 0:
            return "BLOQUEIO CRÍTICO"

        if linha["alertas_criticos"] > 0:
            return "REVISÃO CRÍTICA"

        if linha["erros_importantes"] > 0:
            return "REVISÃO IMPORTANTE"

        if linha["alertas_importantes"] > 0:
            return "ATENÇÃO"

        return "SEM BLOQUEIO"

    resultado["status_criticidade"] = (
        resultado.apply(
            classificar_bloqueio,
            axis=1
        )
    )

    return resultado

def consolidar_prontidao_final(
    qualidade_ponderada,
    bloqueios
):

    resultado = qualidade_ponderada.merge(
        bloqueios,
        on="elemento",
        how="left"
    )

    classificacoes = []

    for _, linha in resultado.iterrows():

        qualidade = linha[
            "qualidade_ponderada_pct"
        ]

        status_criticidade = linha[
            "status_criticidade"
        ]

        if status_criticidade == "BLOQUEIO CRÍTICO":
            classificacao = "CRÍTICO"

        elif status_criticidade == "REVISÃO CRÍTICA":
            classificacao = "REVISÃO"

        elif qualidade < 75:
            classificacao = "CRÍTICO"

        elif qualidade < 90:
            classificacao = "ATENÇÃO"

        else:
            classificacao = "PRONTO"

        classificacoes.append(
            classificacao
        )

    resultado[
        "classificacao_final"
    ] = classificacoes

    return resultado

# =================================================================================================================
# ÁREA DE TESTE LOCAL
# ==================================================================================================================

if __name__ == "__main__":

    RELATORIOS = [
    
         "prontidao_final"
    ]


    servidor = "CE-SRV11"

    # ========================================
    # COLETA BASE - CAPTAÇÃO / UTA
    # ========================================

    inventario_captacao = inventariar_familia(
        servidor=servidor,
        database="UTA",
        caminho_pai=[
            "CAPTAÇÃO"
        ]
    )

    inventario_captacao_avaliado = (
        avaliar_qualidade_inventario(
            inventario_captacao
        )
    )

    consistencia_captacao = (
        analisar_consistencia_familia(
            inventario_captacao
        )
    )

    qualidade_ponderada_captacao = (
        calcular_qualidade_ponderada(
            inventario_captacao_avaliado
        )
    )

    bloqueios_captacao = (
        avaliar_bloqueios_criticidade(
            inventario_captacao_avaliado
        )
    )

    prontidao_final_captacao = (
        consolidar_prontidao_final(
            qualidade_ponderada_captacao,
            bloqueios_captacao
        )
    )

    matriz_captacao = (
        resumir_estrutura_familia(
            inventario_captacao
        )
    )

    matriz_classificada = (
        classificar_atributos_engenharia(
            matriz_captacao
        )
    )

    prontidao_captacao = (
        calcular_prontidao_por_categoria(
            inventario_captacao_avaliado,
            matriz_classificada
        )
    )

    score_captacao = (
        calcular_score_global_prontidao(
            inventario_captacao_avaliado,
            consistencia_captacao,
            matriz_classificada
        )
    )

    inventario_com_criticidade = (
        aplicar_criticidade_atributos(
            inventario_captacao_avaliado
        )
    )

    resumo_criticidade = (
        inventario_com_criticidade
        .groupby(
            [
                "atributo",
                "criticidade"
            ]
        )
        .size()
        .reset_index(
            name="quantidade_registros"
        )
    )

    problemas_captacao = (
        resumir_problemas_por_atributo(
            inventario_captacao_avaliado
        )
    )

    resumo_categorias_captacao = (
        resumir_cobertura_por_categoria(
            matriz_classificada
        )
    )

    # ========================================
    # RELATÓRIO - CONEXÃO
    # ========================================

    if (
        "conexao" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            f"Servidor AF: {servidor}"
        )

        print(
            "Databases disponíveis:"
        )

        for database in listar_databases(
            servidor
        ):

            print(
                f"- {database}"
            )

    # ========================================
    # RELATÓRIO - INVENTÁRIO
    # ========================================

    if (
        "inventario" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Inventário da família CAPTAÇÃO - UTA:"
        )

        print(
            inventario_captacao.to_string(
                index=False
            )
        )

    # ========================================
    # RELATÓRIO - QUALIDADE
    # ========================================

    if (
        "qualidade" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Avaliação de qualidade - CAPTAÇÃO:"
        )

        print(
            inventario_captacao_avaliado[
                [
                    "elemento",
                    "atributo",
                    "data_reference",
                    "uom",
                    "valor_atual",
                    "classificacao_qualidade",
                    "observacao_qualidade"
                ]
            ].to_string(
                index=False
            )
        )

    # ========================================
    # RELATÓRIO - ESTRUTURA
    # ========================================

    if (
        "estrutura" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Consistência estrutural da CAPTAÇÃO:"
        )

        print(
            consistencia_captacao.to_string(
                index=False
            )
        )

    # ========================================
    # RELATÓRIO - PROBLEMAS
    # ========================================

    if (
        "problemas" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Problemas encontrados na CAPTAÇÃO:"
        )

        print(
            problemas_captacao.to_string(
                index=False
            )
        )

    # ========================================
    # RELATÓRIO - MATRIZ
    # ========================================

    if (
        "matriz" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Matriz resumida da CAPTAÇÃO:"
        )

        print(
            matriz_captacao.to_string(
                index=False
            )
        )

    # ========================================
    # RELATÓRIO - CLASSIFICAÇÃO
    # ========================================

    if (
        "classificacao" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Classificação de engenharia da CAPTAÇÃO:"
        )

        print(
            matriz_classificada[
                [
                    "atributo",
                    "categoria_engenharia",
                    "data_reference",
                    "uom",
                    "cobertura_pct"
                ]
            ].to_string(
                index=False
            )
        )

    # ========================================
    # RELATÓRIO - CATEGORIAS
    # ========================================

    if (
        "categorias" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Resumo por categoria de engenharia - CAPTAÇÃO:"
        )

        print(
            resumo_categorias_captacao.to_string(
                index=False
            )
        )

    # ========================================
    # RELATÓRIO - PRONTIDÃO
    # ========================================

    if (
        "prontidao" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Índice de prontidão por categoria - CAPTAÇÃO:"
        )

        print(
            prontidao_captacao.to_string(
                index=False
            )
        )

    # ========================================
    # RELATÓRIO - SCORE
    # ========================================

    if (
        "score" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Score global de prontidão - CAPTAÇÃO:"
        )

        print(
            score_captacao.to_string(
                index=False
            )
        )

    # ========================================
    # RELATÓRIO - CRITICIDADE
    # ========================================

    if (
        "criticidade" in RELATORIOS
        or "todos" in RELATORIOS
    ):

        print()
        print(
            "Criticidade dos atributos - CAPTAÇÃO:"
        )

        print(
            resumo_criticidade.to_string(
                index=False
            )
        )

# ========================================
# RELATÓRIO - QUALIDADE PONDERADA
# ========================================

if (
    "qualidade_ponderada" in RELATORIOS
    or "todos" in RELATORIOS
):

    print()
    print(
        "Qualidade ponderada por criticidade - CAPTAÇÃO:"
    )

    print(
        qualidade_ponderada_captacao.to_string(
            index=False
        )
    )

# ========================================
# RELATÓRIO - BLOQUEIOS DE CRITICIDADE
# ========================================

if (
    "bloqueios" in RELATORIOS
    or "todos" in RELATORIOS
):

    print()
    print(
        "Bloqueios por criticidade - CAPTAÇÃO:"
    )

    print(
        bloqueios_captacao.to_string(
            index=False
        )
    )

# ========================================
# RELATÓRIO - PRONTIDÃO FINAL
# ========================================


if (
    "prontidao_final" in RELATORIOS
    or "todos" in RELATORIOS
):

    print()
    print(
        "Prontidão final - CAPTAÇÃO:"
    )

    print(
        prontidao_final_captacao[
            [
                "elemento",
                "qualidade_ponderada_pct",
                "status_criticidade",
                "classificacao_final"
            ]
        ].to_string(
            index=False
        )
    )