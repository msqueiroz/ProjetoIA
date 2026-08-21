from adaptador_csv import (
    carregar_csv,
    aplicar_perfil_colunas
)

from normalizador import normalizar_dados


resultado = carregar_csv(
    "dados_heterogeneos.csv"
)

if resultado["sucesso"]:

    dados = resultado["dados"]

    dados = aplicar_perfil_colunas(
    dados,
    perfil="heterogeneo"
    )


    dados = normalizar_dados(
        dados,
        perfil="heterogeneo"
    )

    print("=== DADOS NORMALIZADOS ===")

    print(
        dados[
            [
                "data_hora",
                "status_bomba",
                "tensao_v",
                "temp_mancal_c",
                "nivel_pct"
            ]
        ].head()
    )

else:

    print("Erro ao carregar CSV:")
    print(resultado["erro"])