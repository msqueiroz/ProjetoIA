import pandas as pd

from qualidade_dados import gerar_relatorio_qualidade


dados = pd.read_csv("dadosMult.csv")

relatorio = gerar_relatorio_qualidade(dados)

print("=== QUALIDADE DOS DADOS ===")

print(f"Registros: {relatorio['total_linhas']}")
print(f"Colunas: {relatorio['total_colunas']}")
print(f"Valores ausentes: {relatorio['valores_ausentes']}")
print(f"Completude: {relatorio['completude']:.1f}%")

print(
    f"Variáveis presentes: "
    f"{relatorio['variaveis_presentes']}/"
    f"{relatorio['variaveis_esperadas']}"
)

print(f"Status geral: {relatorio['status']}")

print("\nVariáveis ausentes:")

if relatorio["variaveis_ausentes"]:
    for coluna in relatorio["variaveis_ausentes"]:
        print(f"- {coluna}")
else:
    print("- Nenhuma")

print("\nInconsistências:")

if relatorio["inconsistencias"]:
    for problema in relatorio["inconsistencias"]:
        print(f"- {problema}")
else:
    print("- Nenhuma")