import time

from adaptador_pi_af import (
    identificar_fonte_historico_atributo,
    carregar_historico_inteligente,
)


SERVIDOR = "CE-SRV11"
DATABASE = "ETE"

CAMINHO = [
    "ETE",
    "TA-1",
]

ATRIBUTO = "Carga DQO Ent TA1"


print("=" * 70)
print("1. IDENTIFICAÇÃO DA FONTE")
print("=" * 70)

inicio = time.perf_counter()

fonte = identificar_fonte_historico_atributo(
    servidor=SERVIDOR,
    database=DATABASE,
    caminho_elementos=CAMINHO,
    nome_atributo=ATRIBUTO,
)

tempo_fonte = time.perf_counter() - inicio

for chave, valor in fonte.items():
    print(f"{chave}: {valor}")

print()
print(
    "Tempo para identificar fonte:",
    round(tempo_fonte, 3),
    "s",
)


print()
print("=" * 70)
print("2. CARREGAMENTO INTELIGENTE")
print("=" * 70)

inicio = time.perf_counter()

resultado = carregar_historico_inteligente(
    servidor=SERVIDOR,
    database=DATABASE,
    caminho_elementos=CAMINHO,
    nome_atributo=ATRIBUTO,
    inicio="*-24h",
    fim="*",
)

tempo_historico = time.perf_counter() - inicio

print("Estratégia:", resultado["estrategia"])
print("Status:", resultado["status"])
print("Detalhe:", resultado["detalhe"])
print(
    "Tempo total:",
    round(tempo_historico, 3),
    "s",
)

dados = resultado["dados"]

print("Registros:", len(dados))

if not dados.empty:
    print()
    print(dados.head())
    print()
    print(dados.tail())
    