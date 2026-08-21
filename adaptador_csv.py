import pandas as pd
from perfis_normalizacao import PERFIS_NORMALIZACAO


def carregar_csv(caminho_arquivo):

    try:
        dados = pd.read_csv(caminho_arquivo)

        return {
            "sucesso": True,
            "dados": dados,
            "erro": None
        }

    except Exception as erro:

        return {
            "sucesso": False,
            "dados": None,
            "erro": str(erro)
        }


def mapear_colunas(dados, mapa_colunas):

    dados_mapeados = dados.rename(
        columns=mapa_colunas
    )

    return dados_mapeados

def aplicar_perfil_colunas(dados, perfil="padrao"):

    configuracao = PERFIS_NORMALIZACAO.get(
        perfil
    )

    if configuracao is None:
        raise ValueError(
            f"Perfil '{perfil}' não encontrado."
        )

    mapa_colunas = configuracao[
        "mapa_colunas"
    ]

    dados_mapeados = dados.rename(
        columns=mapa_colunas
    )

    return dados_mapeados