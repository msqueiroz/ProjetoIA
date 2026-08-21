import pandas as pd
from motor_diagnostico import diagnosticar_parada

dados = pd.read_csv("dadosMult.csv")
dados["data_hora"] = pd.to_datetime(dados["data_hora"])

dados["status_anterior"] = dados["status_bomba"].shift(1)

paradas = dados[
    (dados["status_anterior"] == 1) &
    (dados["status_bomba"] == 0)
]

for indice, parada in paradas.iterrows():

    resultado = diagnosticar_parada(
        dados,
        indice
    )

    print("\n============================")
    print(f"Parada: {parada['data_hora']}")
    print(f"Categoria: {resultado['categoria']}")
    print(f"Causa: {resultado['causa']}")
    print(f"Confiança: {resultado['confianca']}%")

    print("Evidências:")

    for evidencia in resultado["evidencias"]:
        print(f"- {evidencia}")