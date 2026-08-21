import pandas as pd


def carregar_dados_pi_simulado(dados_pi):

    try:

        dados = pd.DataFrame(
            dados_pi
        )

        return {
            "sucesso": True,
            "dados": dados,
            "erro": None,
            "origem": "PI System"
        }

    except Exception as erro:

        return {
            "sucesso": False,
            "dados": None,
            "erro": str(erro),
            "origem": "PI System"
        }