from pypdf import PdfReader

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