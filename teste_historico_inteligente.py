import time

from adaptador_pi_af import carregar_historico_inteligente


def testar(nome_atributo):

    print()
    print("=" * 70)
    print("ATRIBUTO:", nome_atributo)
    print("=" * 70)

    inicio_teste = time.perf_counter()

    resultado = carregar_historico_inteligente(
        servidor="CE-SRV11",
        database="ETE",
        caminho_elementos=[
            "ETE",
            "TA-1",
        ],
        nome_atributo=nome_atributo,
        inicio="*-30d",
        fim="*",
    )

    tempo = (
        time.perf_counter()
        - inicio_teste
    )

    print("Estratégia:", resultado["estrategia"])
    print("Status:", resultado["status"])
    print("Detalhe:", resultado["detalhe"])
    print("Tempo:", round(tempo, 3), "s")

    fonte = resultado["fonte"]

    print("Tipo fonte:", fonte["tipo_fonte"])
    print("Servidor PI:", fonte["servidor_pi"])
    print("PI Point:", fonte["pi_point"])

    dados = resultado["dados"]

    print("Registros:", len(dados))

    if not dados.empty:

        print()
        print(dados.head())

        print()
        print(dados.tail())


testar(
    "OD-TA1-1"
)

testar(
    "IEE-TA1-DQO"
)
