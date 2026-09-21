import sys

CAMINHO_AFSDK = (
    r"C:\Program Files (x86)"
    r"\PIPC\AF\PublicAssemblies\4.0"
)

sys.path.append(CAMINHO_AFSDK)

import clr

clr.AddReference("OSIsoft.AFSDK")

from OSIsoft.AF import PISystems


SERVIDOR_AF = "CE-SRV11"
DATABASE = "ETE"

CAMINHO_ELEMENTO = [
    "ETE",
    "TA-1",
]

NOME_ANALYSIS = "IEE-TA1-DQO"


def main():

    # ---------------------------------------------------------
    # CONEXÃO COM AF
    # ---------------------------------------------------------

    sistemas = PISystems()
    sistema = sistemas[SERVIDOR_AF]
    banco = sistema.Databases[DATABASE]

    elementos = banco.Elements
    elemento_atual = None

    for nome in CAMINHO_ELEMENTO:

        elemento_atual = elementos[nome]

        if elemento_atual is None:
            raise ValueError(
                f"Elemento '{nome}' não encontrado."
            )

        elementos = elemento_atual.Elements

    # ---------------------------------------------------------
    # LOCALIZA A ANALYSIS
    # ---------------------------------------------------------

    analysis = elemento_atual.Analyses[NOME_ANALYSIS]

    if analysis is None:
        raise ValueError(
            f"Analysis '{NOME_ANALYSIS}' não encontrada."
        )

    print()
    print("Analysis:", analysis.Name)

    print(
        "Regra:",
        analysis.AnalysisRulePlugIn.Name
    )

    print(
        "ConfigString:",
        analysis.AnalysisRule.ConfigString
    )

    print(
        "VariableMapping:",
        analysis.AnalysisRule.VariableMapping
    )

    print(
        "SimplifiedVariableMapping:",
        analysis.AnalysisRule.SimplifiedVariableMapping
    )

    # ---------------------------------------------------------
    # TESTE DOS OUTPUTS
    # ---------------------------------------------------------

    print()
    print("=== OUTPUTS DA ANALYSIS ===")

    try:

        outputs = analysis.AnalysisRule.GetOutputs()

        print(
            "Tipo retornado:",
            outputs.GetType().FullName
        )

        print(
            "Quantidade:",
            outputs.Count
        )

        for output in outputs:

            print()
            print("=" * 60)

            print(
                "Output:",
                output
            )

            print(
                "Tipo:",
                output.GetType().FullName
            )

            print()
            print("--- Propriedades ---")

            for propriedade in output.GetType().GetProperties():

                nome = propriedade.Name

                try:

                    valor = propriedade.GetValue(
                        output,
                        None
                    )

                    print(
                        f"{nome}: {valor}"
                    )

                except Exception:
                    pass

    except Exception as erro:

        print(
            "Erro ao obter outputs:",
            erro
        )


if __name__ == "__main__":
    main()