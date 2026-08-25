import json
import os


PASTA_PERFIS = "perfis"


def salvar_perfil(nome_arquivo, perfil):

    os.makedirs(
        PASTA_PERFIS,
        exist_ok=True
    )

    caminho = os.path.join(
        PASTA_PERFIS,
        f"{nome_arquivo}.json"
    )

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            perfil,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    return caminho
