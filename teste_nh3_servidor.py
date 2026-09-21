import sys

CAMINHO_AFSDK = (
    r"C:\Program Files (x86)"
    r"\PIPC\AF\PublicAssemblies\4.0"
)

sys.path.append(CAMINHO_AFSDK)

import clr

clr.AddReference("OSIsoft.AFSDK")

from OSIsoft.AF.PI import PIServers, PIPoint
from OSIsoft.AF.Time import AFTime
from OSIsoft.AF.Data import AFRetrievalMode


SERVIDOR_PI = "ce-srv09"
PI_POINT = "CARGA-NNH3-TA1-1.1"

DATAS_TESTE = [
    "2025-09-02 00:00:00",
    "2025-09-03 00:00:00",
    "2025-09-04 00:00:00",
]


def main():

    print()
    print("=" * 70)
    print("TESTE DIRETO - CARGA NH3")
    print("=" * 70)

    servidores = PIServers()

    print()
    print("Servidores PI disponíveis:")

    for servidor in servidores:
        print("-", servidor.Name)

    print()
    print("Tentando servidor:", SERVIDOR_PI)

    servidor = servidores[SERVIDOR_PI]

    if servidor is None:
        print()
        print(
            f"Servidor '{SERVIDOR_PI}' não encontrado "
            "na lista de PIServers."
        )
        return

    print("Servidor encontrado:", servidor.Name)

    print()
    print("Procurando PI Point:", PI_POINT)

    try:

        ponto = PIPoint.FindPIPoint(
            servidor,
            PI_POINT
        )

    except Exception as erro:

        print()
        print("ERRO AO LOCALIZAR PI POINT:")
        print(erro)
        return

    print()
    print("PI Point encontrada:", ponto.Name)
    print("Servidor:", ponto.Server.Name)

    print()
    print("=" * 70)
    print("VALORES")
    print("=" * 70)

    for data_texto in DATAS_TESTE:

        instante = AFTime(data_texto)

        print()
        print("Data:", data_texto)

        try:

            valor = ponto.RecordedValue(
                instante,
                AFRetrievalMode.AtOrBefore
            )

            print(
                "Valor:",
                valor.Value
            )

            print(
                "Bom:",
                valor.IsGood
            )

            print(
                "Timestamp:",
                valor.Timestamp
            )

        except Exception as erro:

            print(
                "ERRO:",
                erro
            )

    print()
    print("=" * 70)
    print("TESTE FINALIZADO")
    print("=" * 70)


if __name__ == "__main__":
    main()