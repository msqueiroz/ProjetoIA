from adaptador_csv import (
    carregar_csv,
    aplicar_perfil_colunas
)

from adaptador_pi import (
    carregar_dados_pi_simulado
)

from normalizador import (
    normalizar_dados
)


def carregar_e_preparar_fonte(
        
    fonte_selecionada,
    dados_pi=None
):

    pipeline = {
        "fonte_carregada": False,
        "perfil_identificado": False,
        "mapeamento_concluido": False,
        "normalizacao_concluida": False,
        "qualidade_analisada": False,
        "diagnostico_executado": False
    }


    if fonte_selecionada == "PI System - Simulado":

        origem = "PI System"
        perfil = "pi_simulado"

        resultado = carregar_dados_pi_simulado(
            dados_pi
        )

        nome_fonte = "PI System - Simulado"

    else:

        origem = "CSV"

        arquivo = fonte_selecionada.replace(
            "CSV - ",
            ""
        )

        if arquivo == "dados_heterogeneos.csv":
            perfil = "heterogeneo"
        else:
            perfil = "padrao"

        resultado = carregar_csv(
            arquivo
        )

        nome_fonte = arquivo

    if not resultado["sucesso"]:

        return {
            "sucesso": False,
            "dados": None,
            "erro": resultado["erro"]
        }
    pipeline["fonte_carregada"] = True
    pipeline["perfil_identificado"] = True

    dados = resultado["dados"]

    dados = aplicar_perfil_colunas(
        dados,
        perfil=perfil
    )

    pipeline["mapeamento_concluido"] = True

    dados = normalizar_dados(
        dados,
        perfil=perfil
    )

    pipeline["normalizacao_concluida"] = True

    return {
        "sucesso": True,
        "dados": dados,
        "erro": None,
        "origem": origem,
        "perfil": perfil,
        "nome_fonte": nome_fonte,
        "pipeline": pipeline
    }

    