import time
import re

from adaptador_pi_af import (
    conectar_af,
    carregar_historico_pi_point,
)


SERVIDOR_AF = "CE-SRV11"
SERVIDOR_PI = "ce-srv11"
DATABASE = "ETE"

CAMINHO = [
    "ETE",
    "TA-1",
]

ATRIBUTO = "Carga DQO Ent TA1"


inicio_total = time.perf_counter()


# ==========================================================
# LOCALIZA ATRIBUTO SEM USAR atributo.PIPoint
# ==========================================================

sistema = conectar_af(
    SERVIDOR_AF
)

banco = sistema.Databases[
    DATABASE
]

elementos = banco.Elements
elemento_atual = None

for nome_elemento in CAMINHO:

    elemento_atual = elementos[
        nome_elemento
    ]

    elementos = elemento_atual.Elements


atributo = elemento_atual.Attributes[
    ATRIBUTO
]


config_string = str(
    atributo.ConfigString
)


print("=" * 70)
print("CONFIGURAÇÃO AF")
print("=" * 70)

print(
    "ConfigString:",
    config_string
)


# ==========================================================
# EXTRAI SOMENTE NOME DA PI POINT
# ==========================================================

match = re.search(
    r"\\([^\\?]+)(?:\?\d+)?$",
    config_string
)

if not match:

    raise ValueError(
        "Não foi possível identificar "
        "o nome da PI Point na ConfigString."
    )


nome_pi_point = match.group(1)


print()
print(
    "PI Point extraída:",
    nome_pi_point
)


tempo_identificacao = (
    time.perf_counter()
    - inicio_total
)


print(
    "Tempo identificação:",
    round(
        tempo_identificacao,
        3
    ),
    "s"
)


# ==========================================================
# CONSULTA DIRETA NO SERVIDOR ATIVO
# ==========================================================

inicio_consulta = time.perf_counter()

dados = carregar_historico_pi_point(
    servidor_pi=SERVIDOR_PI,
    nome_pi_point=nome_pi_point,
    inicio="*-24h",
    fim="*",
)

tempo_consulta = (
    time.perf_counter()
    - inicio_consulta
)


print()
print("=" * 70)
print("CONSULTA DIRETA")
print("=" * 70)

print(
    "Servidor utilizado:",
    SERVIDOR_PI
)

print(
    "Tempo consulta:",
    round(
        tempo_consulta,
        3
    ),
    "s"
)

print(
    "Registros:",
    len(dados)
)

if not dados.empty:

    print()
    print(
        dados.head()
    )


tempo_total = (
    time.perf_counter()
    - inicio_total
)


print()
print(
    "TEMPO TOTAL:",
    round(
        tempo_total,
        3
    ),
    "s"
)