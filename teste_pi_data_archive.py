import sys
import pandas as pd

CAMINHO_AFSDK = (
    r"C:\Program Files (x86)"
    r"\PIPC\AF\PublicAssemblies\4.0"
)

sys.path.append(CAMINHO_AFSDK)

import clr

clr.AddReference("OSIsoft.AFSDK")

from OSIsoft.AF.PI import PIServers, PIPoint
from OSIsoft.AF.Time import AFTimeRange
from OSIsoft.AF.Data import AFBoundaryType


SERVIDOR_PI = "ce-srv11"
TAG = "IEE-TA1-DQO"


def main():

    print("Conectando ao PI Data Archive...")

    servidores = PIServers()

    servidor = servidores[SERVIDOR_PI]

    if servidor is None:
        raise ValueError(
            f"Servidor PI '{SERVIDOR_PI}' não encontrado."
        )

    print(
        f"Servidor encontrado: {servidor.Name}"
    )

    print(
        f"Procurando PI Point: {TAG}"
    )

    ponto = PIPoint.FindPIPoint(
        servidor,
        TAG
    )

    print(
        f"PI Point encontrada: {ponto.Name}"
    )

    intervalo = AFTimeRange(
        "*-365d",
        "*"
    )

    print(
        "Consultando histórico direto no Data Archive..."
    )

    valores = ponto.RecordedValues(
        intervalo,
        AFBoundaryType.Inside,
        None,
        False
    )

    registros = []

    for valor in valores:

        registros.append({
            "data_hora":
                str(valor.Timestamp),

            "valor":
                str(valor.Value),

            "bom":
                bool(valor.IsGood),
        })

    df = pd.DataFrame(
        registros
    )

    print()
    print(
        f"Quantidade de eventos: {len(df)}"
    )

    print()
    print(
        df.head(20)
    )


if __name__ == "__main__":
    main()