from pypdf import PdfReader
import re

ARQUIVO_PDF = "Manual_Oper_EEF.pdf"


def carregar_manual(arquivo_pdf=None):

    if arquivo_pdf is None:
        leitor = PdfReader(ARQUIVO_PDF)
    else:
        leitor = PdfReader(arquivo_pdf)

    texto_completo = ""

    for pagina in leitor.pages:
        texto = pagina.extract_text()

        if texto:
            texto_completo += texto + "\n"

    return texto_completo

def carregar_manual_por_paginas(arquivo_pdf=None):


    if arquivo_pdf is None:
        leitor = PdfReader(ARQUIVO_PDF)
    else:
        leitor = PdfReader(arquivo_pdf)

    paginas = []

    for numero_pagina, pagina in enumerate(
        leitor.pages,
        start=1
    ):

        texto = pagina.extract_text()

        if texto:
            paginas.append({
                "pagina": numero_pagina,
                "texto": texto
            })

    return paginas

def buscar_no_manual_por_paginas(
    termo,
    arquivo_pdf=None
):

    paginas = carregar_manual_por_paginas(
        arquivo_pdf
    )

    resultados = []

    for pagina in paginas:

        texto = pagina["texto"]

        secao = extrair_secao_da_pagina(
            texto,
            termo
        )

        if secao:

            resultados.append({
                "pagina": pagina["pagina"],
                "titulo": secao["titulo"],
                "texto": secao["texto"]
            })

    return resultados

def extrair_secao_da_pagina(
    texto_pagina,
    termo
):

    linhas = texto_pagina.splitlines()

    indice_encontrado = None

    for indice, linha in enumerate(linhas):

        if termo.lower() in linha.lower():
            indice_encontrado = indice
            break

    if indice_encontrado is None:
        return None

    # Procurar o início da seção
    inicio = indice_encontrado

    for indice in range(
        indice_encontrado,
        -1,
        -1
    ):

        linha = linhas[indice].strip()

        if re.match(
            r"^\d+\.\s+",
            linha
        ):
            inicio = indice
            break

    # Procurar o início da próxima seção
    fim = len(linhas)

    for indice in range(
        inicio + 1,
        len(linhas)
    ):

        linha = linhas[indice].strip()

        if re.match(
            r"^\d+\.\s+",
            linha
        ):
            fim = indice
            break

    trecho = "\n".join(
        linhas[inicio:fim]
    ).strip()

    titulo = linhas[inicio].strip()

    return {
        "titulo": titulo,
        "texto": trecho
    }

def buscar_no_manual(termo, arquivo_pdf=None):

    texto = carregar_manual(arquivo_pdf)
    linhas = texto.splitlines()

    resultados = []

    for i, linha in enumerate(linhas):

        if termo.lower() in linha.lower():

            inicio = i

            # procura o início da próxima seção numerada
            fim = len(linhas)

            for j in range(i + 1, len(linhas)):

                linha_seguinte = linhas[j].strip()

                if (
                    linha_seguinte.startswith("1.") or
                    linha_seguinte.startswith("2.") or
                    linha_seguinte.startswith("3.") or
                    linha_seguinte.startswith("4.") or
                    linha_seguinte.startswith("5.")
                ):
                    fim = j
                    break

            trecho = "\n".join(
                linhas[inicio:fim]
            )

            resultados.append(trecho)

    return resultados

def buscar_contexto_diagnostico(
    causa,
    arquivo_pdf=None
):

    termos_por_causa = {
        "VIBRAÇÃO ALTA": "vibração",
        "SUBTENSÃO": "subtensão",
        "NÍVEL BAIXO": "nível baixo",
        "ALTA TEMPERATURA DE MANCAL": "temperatura",
        "FALHA DE INSTRUMENTAÇÃO DE NÍVEL": "instrumentação"
    }

    termo_busca = termos_por_causa.get(
        causa,
        causa
    )

    resultados = buscar_no_manual_por_paginas(
        termo_busca,
        arquivo_pdf
    )

    return {
        "causa": causa,
        "termo_busca": termo_busca,
        "resultados": resultados
    }


# Este trecho só executa quando rodarmos manual.py diretamente
if __name__ == "__main__":

    print("=== TESTE DE CONSULTA AO MANUAL ===")

    termo = "Nível baixo"

    resultados = buscar_no_manual(termo)

    if resultados:

        for resultado in resultados:
            print("\n--- TRECHO ENCONTRADO ---")
            print(resultado)

    else:
        print("Nenhuma informação encontrada.")