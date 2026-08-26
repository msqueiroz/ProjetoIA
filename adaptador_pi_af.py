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

#================================
#AREA DE TESTE LOCAL
#================================
if __name__ == "__main__":

    servidor = "CE-SRV11"

    print(
        f"Conectando ao AF Server: "
        f"{servidor}"
    )

    sistema = conectar_af(
        servidor
    )

    print(
        "Conexão AF realizada."
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

    print()
    print("Elementos dentro de ECB:")

    elementos_ecb = listar_elementos(
        servidor="CE-SRV11",
        database="Manutencao",
        caminho_elementos=["ECB"]
    )

    for elemento in elementos_ecb:

        print(
            f"- {elemento}"
        )

    print()
    print("Atributos do ECB-BC-01:")

    atributos = listar_atributos(
        servidor="CE-SRV11",
        database="Manutencao",
        caminho_elementos=[
            "ECB",
            "ECB-BC-01"
        ]
    )

    for atributo in atributos:

        print(
            f"- {atributo}"
        )        

    print()
    print("Valor atual de Status:")

    status = obter_valor_atual_atributo(
        servidor="CE-SRV11",
        database="Manutencao",
        caminho_elementos=[
            "ECB",
            "ECB-BC-01"
        ],
        nome_atributo="Status"
    )

    print(
        f"Valor: {status['valor']}"
    )

    print(
        f"Timestamp: {status['timestamp']}"
    )
    print()
    print("Histórico de Status:")

    historico_status = carregar_historico_atributo(
        servidor="CE-SRV11",
        database="Manutencao",
        caminho_elementos=[
            "ECB",
            "ECB-BC-01"
        ],
        nome_atributo="Status",
        inicio="*-2h",
        fim="*"
    )

    print(
        historico_status.head(20)
    )

    print()
    print(
        f"Registros encontrados: "
        f"{len(historico_status)}"
    )

    print()
    print("Inventário AF:")

    inventario = inventariar_atributos(
        servidor="CE-SRV11",
        database="Manutencao",
        caminho_elementos=[
            "ECB",
            "ECB-BC-01"
        ]
    )

    print(
        inventario.to_string(
            index=False
        )
    )

    print()
    print("Avaliação de qualidade:")

    inventario_avaliado = (
        avaliar_qualidade_inventario(
            inventario
        )
    )

    print(
        inventario_avaliado[
            [
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

    print()
    print(
        "Inventário da família ECB:"
    )

    inventario_ecb = inventariar_familia(
        servidor="CE-SRV11",
        database="Manutencao",
        caminho_pai=[
            "ECB"
        ]
    )

    inventario_ecb_avaliado = (
        avaliar_qualidade_inventario(
            inventario_ecb
        )
    )

    resumo_ecb = (
        inventario_ecb_avaliado
        .groupby(
            [
                "elemento",
                "classificacao_qualidade"
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
    )

    print(
        resumo_ecb.to_string()
    )    
    print()
    print(
        "Consistência estrutural da família ECB:"
    )

    consistencia_ecb = (
        analisar_consistencia_familia(
            inventario_ecb
        )
    )

    print(
        consistencia_ecb.to_string(
            index=False
        )
    )  

    print()
    print(
        "Inventário da família CAPTAÇÃO - UTA:"
    )

    inventario_captacao = inventariar_familia(
        servidor="CE-SRV11",
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

    resumo_captacao = (
        inventario_captacao_avaliado
        .groupby(
            [
                "elemento",
                "classificacao_qualidade"
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
    )

    print(
        resumo_captacao.to_string()
    )

    print()
    print(
        "Consistência estrutural da CAPTAÇÃO:"
    )

    consistencia_captacao = (
        analisar_consistencia_familia(
            inventario_captacao
        )
    )

    print(
        consistencia_captacao.to_string(
            index=False
        )
    )

print()
print(
    "Problemas encontrados na CAPTAÇÃO:"
)

problemas_captacao = (
    resumir_problemas_por_atributo(
        inventario_captacao_avaliado
    )
)

print(
    problemas_captacao.to_string(
        index=False
    )
) 
print()

print()
print(
    "Matriz resumida da CAPTAÇÃO:"
)

matriz_captacao = (
    resumir_estrutura_familia(
        inventario_captacao
    )
)

print(
    matriz_captacao.to_string(
        index=False
    )
)

print()
print(
    "Classificação de engenharia da CAPTAÇÃO:"
)

matriz_classificada = (
    classificar_atributos_engenharia(
        matriz_captacao
    )
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

print()
print(
    "Resumo por categoria de engenharia - CAPTAÇÃO:"
)

resumo_categorias_captacao = (
    resumir_cobertura_por_categoria(
        matriz_classificada
    )
)

print(
    resumo_categorias_captacao.to_string(
        index=False
    )
)

print()
print(
    "Índice de prontidão por categoria - CAPTAÇÃO:"
)

prontidao_captacao = (
    calcular_prontidao_por_categoria(
        inventario_captacao_avaliado,
        matriz_classificada
    )
)

print(
    prontidao_captacao.to_string(
        index=False
    )
)