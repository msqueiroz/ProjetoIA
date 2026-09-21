from gerenciador_conhecimento import (
    obter_resumo_extracao_pdf,
    criar_trechos_pdf,
    buscar_trechos,
)


CAMINHO_PDF = (
    r"C:\Users\mariosilva\Documents\ProjetoIA"
    r"\documentos\MO-ETE-001.pdf"
)


def mostrar_resultados(titulo, resultados):
    print("\n" + "=" * 90)
    print(titulo)
    print("=" * 90)

    if not resultados:
        print("Nenhum resultado encontrado.")
        return

    for resultado in resultados:
        print("\n" + "-" * 90)
        print(f"ID trecho: {resultado['id_trecho']}")
        print(f"Página: {resultado['pagina']}")
        print(f"Pontuação: {resultado['pontuacao_busca']}")
        print(
            "Termos encontrados: "
            + ", ".join(resultado["termos_encontrados"])
        )
        print()

        texto = resultado["texto"]

        if len(texto) > 1200:
            texto = texto[:1200] + "\n[...]"

        print(texto)


def main():
    print("\n=== TESTE DA BASE DE CONHECIMENTO ===\n")

    resumo = obter_resumo_extracao_pdf(CAMINHO_PDF)

    print("Resumo da extração:")
    print(f"Arquivo: {resumo['arquivo']}")
    print(f"Total de páginas: {resumo['total_paginas']}")
    print(f"Páginas com texto: {resumo['paginas_com_texto']}")
    print(f"Páginas sem texto: {resumo['paginas_sem_texto']}")
    print(
        "Caracteres extraídos: "
        f"{resumo['total_caracteres_extraidos']}"
    )

    print("\nCriando trechos...")

    trechos = criar_trechos_pdf(CAMINHO_PDF)

    print(f"Total de trechos criados: {len(trechos)}")

    # ---------------------------------------------------------
    # TESTE 1
    # ---------------------------------------------------------

    consulta_1 = (
        "NH3 oxigênio dissolvido tanque de aeração"
    )

    resultados_1 = buscar_trechos(
        trechos,
        consulta_1,
        limite=5,
    )

    mostrar_resultados(
        f"BUSCA 1: {consulta_1}",
        resultados_1,
    )

    # ---------------------------------------------------------
    # TESTE 2
    # ---------------------------------------------------------

    consulta_2 = (
        "tempo de detenção TA-1 TA-2 TA-3"
    )

    resultados_2 = buscar_trechos(
        trechos,
        consulta_2,
        limite=5,
    )

    mostrar_resultados(
        f"BUSCA 2: {consulta_2}",
        resultados_2,
    )

    # ---------------------------------------------------------
    # TESTE 3
    # ---------------------------------------------------------

    consulta_3 = (
        "COT carga orgânica TCO equalização"
    )

    resultados_3 = buscar_trechos(
        trechos,
        consulta_3,
        limite=5,
    )

    mostrar_resultados(
        f"BUSCA 3: {consulta_3}",
        resultados_3,
    )


if __name__ == "__main__":
    main()