import time

from adaptador_pi_af import conectar_af


SERVIDOR = "CE-SRV11"
DATABASE = "ETE"

CAMINHO = [
    "ETE",
    "TA-1",
]

ATRIBUTO = "Carga DQO Ent TA1"


inicio = time.perf_counter()

sistema = conectar_af(SERVIDOR)
banco = sistema.Databases[DATABASE]

elementos = banco.Elements
elemento_atual = None

for nome_elemento in CAMINHO:
    elemento_atual = elementos[nome_elemento]
    elementos = elemento_atual.Elements

atributo = elemento_atual.Attributes[ATRIBUTO]

tempo_localizar = time.perf_counter() - inicio


print("=" * 70)
print("ATRIBUTO")
print("=" * 70)

print("Nome:", atributo.Name)

print(
    "Data Reference:",
    atributo.DataReferencePlugIn.Name
)

print(
    "ConfigString:",
    atributo.ConfigString
)

print()
print(
    "Tempo sem acessar atributo.PIPoint:",
    round(tempo_localizar, 3),
    "s"
)