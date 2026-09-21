import sys

# ============================================================
# CONFIGURAÇÃO DO AF SDK
# ============================================================

CAMINHO_AFSDK = (
    r"C:\Program Files (x86)"
    r"\PIPC\AF\PublicAssemblies\4.0"
)

sys.path.append(CAMINHO_AFSDK)

import clr

clr.AddReference("OSIsoft.AFSDK")

# ============================================================
# IMPORTS AF SDK
# ============================================================

from OSIsoft.AF import PISystems
from OSIsoft.AF.PI import PIServers, PIPoint
from OSIsoft.AF.Time import AFTime
from OSIsoft.AF.Data import AFRetrievalMode


# ============================================================
# CONFIGURAÇÕES DO TESTE
# ============================================================

SERVIDOR_AF = "CE-SRV11"
SERVIDOR_PI = "ce-srv11"

DATABASE = "ETE"

CAMINHO_ELEMENTO = [
    "ETE",
    "TA-1",
]

ATRIBUTO_AF = "IEE-TA1-DQO"

PI_POINT = "IEE-TA1-DQO"


# Datas onde já vimos valores válidos na PI Point
DATAS_TESTE = [
    "2025-09-02 00:00:00",
    "2025-09-03 00:00:00",
    "2025-09-04 00:00:00",
]


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():

    print()
    print("=" * 70)
    print("TESTE - COMPARAÇÃO AF ANALYSIS x PI POINT")
    print("=" * 70)

    # ========================================================
    # CONEXÃO COM AF
    # ========================================================

    print()
    print("Conectando ao AF...")

    sistemas = PISystems()

    sistema = sistemas[SERVIDOR_AF]

    if sistema is None:
        raise ValueError(
            f"Servidor AF '{SERVIDOR_AF}' não encontrado."
        )

    banco = sistema.Databases[DATABASE]

    if banco is None:
        raise ValueError(
            f"Database AF '{DATABASE}' não encontrada."
        )

    # ========================================================
    # LOCALIZA O ELEMENTO
    # ========================================================

    elementos = banco.Elements

    elemento = None

    for nome_elemento in CAMINHO_ELEMENTO:

        elemento = elementos[nome_elemento]

        if elemento is None:
            raise ValueError(
                f"Elemento '{nome_elemento}' não encontrado."
            )

        elementos = elemento.Elements

    # ========================================================
    # LOCALIZA O ATRIBUTO AF
    # ========================================================

    atributo = elemento.Attributes[ATRIBUTO_AF]

    if atributo is None:
        raise ValueError(
            f"Atributo '{ATRIBUTO_AF}' não encontrado."
        )

    # ========================================================
    # CONEXÃO COM PI DATA ARCHIVE
    # ========================================================

    print("Conectando ao PI Data Archive...")

    servidores_pi = PIServers()

    servidor_pi = servidores_pi[SERVIDOR_PI]

    if servidor_pi is None:
        raise ValueError(
            f"Servidor PI '{SERVIDOR_PI}' não encontrado."
        )

    ponto = PIPoint.FindPIPoint(
        servidor_pi,
        PI_POINT
    )

    if ponto is None:
        raise ValueError(
            f"PI Point '{PI_POINT}' não encontrada."
        )

    # ========================================================
    # INFORMAÇÕES ENCONTRADAS
    # ========================================================

    print()
    print("-" * 70)

    print(
        "AF Attribute:",
        atributo.Name
    )

    try:

        print(
            "AF Data Reference:",
            atributo.DataReferencePlugIn.Name
        )

    except Exception:

        print(
            "AF Data Reference: não identificado"
        )

    try:

        print(
            "AF PIPoint:",
            atributo.PIPoint
        )

    except Exception:

        print(
            "AF PIPoint: não disponível"
        )

    print()

    print(
        "PI Point direta:",
        ponto.Name
    )

    print(
        "Servidor PI:",
        ponto.Server.Name
    )

    print("-" * 70)

    # ========================================================
    # COMPARAÇÃO DOS VALORES
    # ========================================================

    print()
    print("INICIANDO COMPARAÇÃO...")
    print()

    for data_texto in DATAS_TESTE:

        print("=" * 70)

        print(
            "Data:",
            data_texto
        )

        print("-" * 70)

        instante = AFTime(
            data_texto
        )

        # ----------------------------------------------------
        # VALOR PELO AF / ANALYSIS
        # ----------------------------------------------------

        valor_af_num = None

        try:

            valor_af = atributo.GetValue(
                instante
            )

            valor_af_num = valor_af.Value

            print(
                "AF Analysis:",
                valor_af.Value,
                "| bom:",
                valor_af.IsGood,
                "| horário:",
                valor_af.Timestamp
            )

        except Exception as erro:

            print(
                "AF Analysis: ERRO -",
                erro
            )

        # ----------------------------------------------------
        # VALOR DIRETO DA PI POINT
        # ----------------------------------------------------

        valor_pi_num = None

        try:

            valor_pi = ponto.RecordedValue(
                instante,
                AFRetrievalMode.AtOrBefore
            )

            valor_pi_num = valor_pi.Value

            print(
                "PI direta:",
                valor_pi.Value,
                "| bom:",
                valor_pi.IsGood,
                "| horário:",
                valor_pi.Timestamp
            )

        except Exception as erro:

            print(
                "PI direta: ERRO -",
                erro
            )

        # ----------------------------------------------------
        # COMPARAÇÃO NUMÉRICA
        # ----------------------------------------------------

        print()

        try:

            numero_af = float(
                valor_af_num
            )

            numero_pi = float(
                valor_pi_num
            )

            diferenca = abs(
                numero_af - numero_pi
            )

            print(
                "Diferença absoluta:",
                diferenca
            )

            if diferenca < 0.000001:

                print(
                    "RESULTADO: VALORES PRATICAMENTE IGUAIS"
                )

            elif diferenca < 0.01:

                print(
                    "RESULTADO: VALORES MUITO PRÓXIMOS"
                )

            else:

                print(
                    "RESULTADO: VALORES DIFERENTES"
                )

        except Exception:

            print(
                "Comparação numérica não foi possível."
            )

        print()

    # ========================================================
    # FINAL
    # ========================================================

    print("=" * 70)
    print("TESTE FINALIZADO")
    print("=" * 70)
    print()


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()