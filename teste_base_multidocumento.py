from gerenciador_conhecimento import (
    carregar_base_documental,
    obter_resumo_base_documental,
    buscar_base_documental,
)

base = carregar_base_documental("Documentos")

resumo = obter_resumo_base_documental(base)

print("\n=== RESUMO DA BASE ===")
print(resumo)

print("\n=== BUSCA ===")

resultados = buscar_base_documental(
    base,
    consulta="tempo de detenção tanque de aeração NH3",
    limite=5,
)

for indice, resultado in enumerate(resultados, start=1):
    print(f"\n--- Resultado {indice} ---")
    print("Documento:", resultado.get("documento"))
    print("Página:", resultado.get("pagina"))
    print("Score:", resultado.get("pontuacao_busca"))
    print("Termos:", resultado.get("termos_encontrados"))
    print("Texto:", resultado.get("texto", "")[:800])