from adaptador_csv import (
    carregar_csv,
    aplicar_perfil_colunas
)

from normalizador import normalizar_dados

from qualidade_dados import gerar_relatorio_qualidade

from motor_diagnostico import diagnosticar_parada


# =========================
# 1. CARREGAR CSV
# =========================

resultado = carregar_csv(
    "dados_heterogeneos.csv"
)

if not resultado["sucesso"]:

    print("Erro ao carregar CSV:")
    print(resultado["erro"])

    exit()


dados = resultado["dados"]


# =========================
# 2. MAPEAR COLUNAS
# =========================

dados = aplicar_perfil_colunas(
    dados,
    perfil="heterogeneo"
)


# =========================
# 3. NORMALIZAR DADOS
# =========================

dados = normalizar_dados(
    dados,
    perfil="heterogeneo"
)


# =========================
# 4. QUALIDADE DOS DADOS
# =========================

relatorio = gerar_relatorio_qualidade(
    dados
)

print("=== QUALIDADE DOS DADOS ===")

print(
    f"Completude: "
    f"{relatorio['completude']:.1f}%"
)

print(
    f"Status geral: "
    f"{relatorio['status']}"
)

print(
    f"Aptidão para diagnóstico: "
    f"{relatorio['aptidao_diagnostico']}"
)


# =========================
# 5. DETECTAR PARADAS
# =========================

dados["status_anterior"] = (
    dados["status_bomba"].shift(1)
)

paradas = dados[
    (dados["status_anterior"] == 1) &
    (dados["status_bomba"] == 0)
]


print("\n=== PARADAS DETECTADAS ===")

print(
    f"Quantidade: {len(paradas)}"
)


# =========================
# 6. DIAGNOSTICAR PARADAS
# =========================

for indice, parada in paradas.iterrows():

    resultado_diagnostico = diagnosticar_parada(
        dados,
        indice
    )

    print("\n============================")

    print(
        f"Parada: "
        f"{parada['data_hora']}"
    )

    print(
        f"Categoria: "
        f"{resultado_diagnostico['categoria']}"
    )

    print(
        f"Causa: "
        f"{resultado_diagnostico['causa']}"
    )

    print(
        f"Confiança: "
        f"{resultado_diagnostico['confianca']}%"
    )

    print("Evidências:")

    for evidencia in resultado_diagnostico[
        "evidencias"
    ]:

        print(
            f"- {evidencia}"
        )