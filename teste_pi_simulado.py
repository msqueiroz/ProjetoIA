from adaptador_pi import carregar_dados_pi_simulado
from adaptador_csv import aplicar_perfil_colunas
from normalizador import normalizar_dados
from qualidade_dados import gerar_relatorio_qualidade
from motor_diagnostico import diagnosticar_parada


dados_pi = [
    {
        "Timestamp": "2026-08-20 08:00:00",
        "Running": 1,
        "Voltage": 440,
        "Current": 18.2,
        "BearingTemperature": 65,
        "Vibration": 2.1,
        "Level": 70,
        "Alarm": "NORMAL"
    },
    {
        "Timestamp": "2026-08-20 08:30:00",
        "Running": 1,
        "Voltage": 440,
        "Current": 18.5,
        "BearingTemperature": 67,
        "Vibration": 2.4,
        "Level": 68,
        "Alarm": "NORMAL"
    },
    {
        "Timestamp": "2026-08-20 09:00:00",
        "Running": 1,
        "Voltage": 439,
        "Current": 18.7,
        "BearingTemperature": 72,
        "Vibration": 5.2,
        "Level": 67,
        "Alarm": "NORMAL"
    },
    {
        "Timestamp": "2026-08-20 09:15:00",
        "Running": 1,
        "Voltage": 440,
        "Current": 18.8,
        "BearingTemperature": 74,
        "Vibration": 8.2,
        "Level": 66,
        "Alarm": "TRIP_VIBRACAO"
    },
    {
        "Timestamp": "2026-08-20 09:25:00",
        "Running": 0,
        "Voltage": 440,
        "Current": 0.0,
        "BearingTemperature": 74,
        "Vibration": 8.2,
        "Level": 66,
        "Alarm": "BOMBA_PARADA"
    }
]


resultado = carregar_dados_pi_simulado(
    dados_pi
)

if not resultado["sucesso"]:
    print(resultado["erro"])
    exit()


dados = resultado["dados"]

dados = aplicar_perfil_colunas(
    dados,
    perfil="pi_simulado"
)

dados = normalizar_dados(
    dados,
    perfil="pi_simulado"
)

print("=== DADOS DO PI NORMALIZADOS ===")
print(dados)


relatorio = gerar_relatorio_qualidade(
    dados
)

print("\n=== QUALIDADE ===")
print(f"Completude: {relatorio['completude']:.1f}%")
print(f"Status: {relatorio['status']}")
print(
    f"Aptidão: "
    f"{relatorio['aptidao_diagnostico']}"
)


dados["status_anterior"] = (
    dados["status_bomba"].shift(1)
)

paradas = dados[
    (dados["status_anterior"] == 1) &
    (dados["status_bomba"] == 0)
]


print("\n=== PARADAS ===")

for indice, parada in paradas.iterrows():

    diagnostico = diagnosticar_parada(
        dados,
        indice
    )

    print(f"\nParada: {parada['data_hora']}")
    print(
        f"Categoria: "
        f"{diagnostico['categoria']}"
    )
    print(
        f"Causa: "
        f"{diagnostico['causa']}"
    )
    print(
        f"Confiança: "
        f"{diagnostico['confianca']}%"
    )