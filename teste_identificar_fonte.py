from adaptador_pi_af import identificar_fonte_historico_atributo


TESTES = [
    {
        "nome": "OD-TA1-1",
        "caminho": [
            "ETE",
            "TA-1",
        ],
    },
    {
        "nome": "IEE-TA1-DQO",
        "caminho": [
            "ETE",
            "TA-1",
        ],
    },
]


for teste in TESTES:

    print()
    print("=" * 70)
    print("ATRIBUTO:", teste["nome"])
    print("=" * 70)

    resultado = identificar_fonte_historico_atributo(
        servidor="CE-SRV11",
        database="ETE",
        caminho_elementos=teste["caminho"],
        nome_atributo=teste["nome"],
    )

    for chave, valor in resultado.items():
        print(f"{chave}: {valor}")