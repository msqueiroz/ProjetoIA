from adaptador_csv import (
    carregar_csv,
    mapear_colunas,
    MAPA_PADRAO,
    MAPA_OUTRO_SISTEMA
)


##resultado = carregar_csv("dadosMult.csv")
resultado = carregar_csv("dados_outro_sistema.csv")

if resultado["sucesso"]:

    dados = resultado["dados"]


    dados = mapear_colunas(
    dados,
    ##MAPA_PADRAO
    MAPA_OUTRO_SISTEMA
)

    print("=== CSV CARREGADO COM SUCESSO ===")
    print(f"Linhas: {len(dados)}")
    print(f"Colunas: {len(dados.columns)}")

    print("\nColunas encontradas:")

    for coluna in dados.columns:
        print(f"- {coluna}")

else:

    print("Erro ao carregar CSV:")
    print(resultado["erro"])