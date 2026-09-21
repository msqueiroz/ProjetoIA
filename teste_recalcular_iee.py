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
# IMPORTS
# ============================================================

from OSIsoft.AF import PISystems
from OSIsoft.AF.PI import PIServers, PIPoint
from OSIsoft.AF.Time import AFTime
from OSIsoft.AF.Data import AFRetrievalMode


# ============================================================
# CONFIGURAÇÕES
# ============================================================

SERVIDOR_AF = "CE-SRV11"
SERVIDOR_PI_PADRAO = "ce-srv11"

DATABASE = "ETE"

CAMINHO_ELEMENTO = [
    "ETE",
    "TA-1",
]

# Atributos utilizados pela Analysis IEE-TA1-DQO
ATRIBUTOS_ENTRADA = [
    "TOT Energia TA1-1",
    "Carga DQO Ent TA1",
    "Carga NH3 Ent TA1",
]

# PI Point histórica que queremos validar
PI_POINT_RESULTADO = "IEE-TA1-DQO"

DATAS_TESTE = [
    "2025-09-02 00:00:00",
    "2025-09-03 00:00:00",
    "2025-09-04 00:00:00",
]


# ============================================================
# FUNÇÃO PARA MOSTRAR INFORMAÇÕES DO ATRIBUTO
# ============================================================

def mostrar_atributo(atributo):

    print()
    print("-" * 70)
    print("Atributo:", atributo.Name)

    try:
        print(
            "Data Reference:",
            atributo.DataReferencePlugIn.Name
        )
    except Exception:
        print("Data Reference: não identificado")

    try:
        print(
            "PIPoint:",
            atributo.PIPoint
        )
    except Exception:
        print("PIPoint: não disponível")

    try:
        print(
            "ConfigString:",
            atributo.ConfigString
        )
    except Exception:
        pass


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():

    print()
    print("=" * 70)
    print("TESTE - RECÁLCULO DO IEE-TA1-DQO")
    print("=" * 70)

    # ========================================================
    # CONECTA AO AF
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
            f"Database '{DATABASE}' não encontrada."
        )

    # ========================================================
    # LOCALIZA TA-1
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

    print(
        "Elemento encontrado:",
        elemento.Name
    )

    # ========================================================
    # MOSTRA AS FONTES DAS TRÊS ENTRADAS
    # ========================================================

    print()
    print("=" * 70)
    print("ENTRADAS DA ANALYSIS")
    print("=" * 70)

    atributos = {}

    for nome_atributo in ATRIBUTOS_ENTRADA:

        atributo = elemento.Attributes[nome_atributo]

        if atributo is None:
            print(
                f"Atributo não encontrado: {nome_atributo}"
            )
            continue

        atributos[nome_atributo] = atributo

        mostrar_atributo(
            atributo
        )

    # ========================================================
    # CONECTA AO PI DATA ARCHIVE
    # ========================================================

    print()
    print("=" * 70)
    print("PI POINT DE RESULTADO")
    print("=" * 70)

    servidores_pi = PIServers()

    servidor_resultado = servidores_pi[
        SERVIDOR_PI_PADRAO
    ]

    if servidor_resultado is None:
        raise ValueError(
            f"Servidor PI '{SERVIDOR_PI_PADRAO}' não encontrado."
        )

    ponto_resultado = PIPoint.FindPIPoint(
        servidor_resultado,
        PI_POINT_RESULTADO
    )

    print(
        "PI Point:",
        ponto_resultado.Name
    )

    print(
        "Servidor:",
        ponto_resultado.Server.Name
    )

    # ========================================================
    # TESTE NAS DATAS
    # ========================================================

    print()
    print("=" * 70)
    print("COMPARAÇÃO")
    print("=" * 70)

    for data_texto in DATAS_TESTE:

        print()
        print("=" * 70)
        print("Data:", data_texto)
        print("=" * 70)

        instante = AFTime(
            data_texto
        )

        valores = {}

        # ----------------------------------------------------
        # CONSULTA AS ENTRADAS PELO AF
        # ----------------------------------------------------

        for nome_atributo, atributo in atributos.items():

            try:

                valor = atributo.GetValue(
                    instante
                )

                print(
                    nome_atributo,
                    "=",
                    valor.Value,
                    "| bom:",
                    valor.IsGood,
                    "| horário:",
                    valor.Timestamp
                )

                if valor.IsGood:

                    try:
                        valores[nome_atributo] = float(
                            valor.Value
                        )
                    except Exception:
                        pass

            except Exception as erro:

                print(
                    nome_atributo,
                    "= ERRO:",
                    erro
                )

        # ----------------------------------------------------
        # VALOR HISTÓRICO DA PI POINT IEE
        # ----------------------------------------------------

        try:

            valor_pi = ponto_resultado.RecordedValue(
                instante,
                AFRetrievalMode.AtOrBefore
            )

            print()
            print(
                "PI IEE-TA1-DQO =",
                valor_pi.Value,
                "| bom:",
                valor_pi.IsGood,
                "| horário:",
                valor_pi.Timestamp
            )

            valor_pi_numerico = None

            if valor_pi.IsGood:

                try:
                    valor_pi_numerico = float(
                        valor_pi.Value
                    )
                except Exception:
                    pass

        except Exception as erro:

            print(
                "PI IEE-TA1-DQO = ERRO:",
                erro
            )

            valor_pi_numerico = None

        # ----------------------------------------------------
        # RECÁLCULO DA FÓRMULA
        # ----------------------------------------------------

        energia = valores.get(
            "TOT Energia TA1-1"
        )

        carga_dqo = valores.get(
            "Carga DQO Ent TA1"
        )

        carga_nh3 = valores.get(
            "Carga NH3 Ent TA1"
        )

        print()
        print("--- RECÁLCULO ---")

        if (
            energia is not None
            and carga_dqo is not None
            and carga_nh3 is not None
        ):

            denominador = (
                carga_dqo
                + 1.85 * carga_nh3
            )

            if denominador != 0:

                iee_calculado = (
                    energia / denominador
                )

                print(
                    "Energia:",
                    energia
                )

                print(
                    "Carga DQO:",
                    carga_dqo
                )

                print(
                    "Carga NH3:",
                    carga_nh3
                )

                print(
                    "Denominador:",
                    denominador
                )

                print(
                    "IEE recalculado:",
                    iee_calculado
                )

                if valor_pi_numerico is not None:

                    diferenca = abs(
                        iee_calculado
                        - valor_pi_numerico
                    )

                    print(
                        "IEE armazenado:",
                        valor_pi_numerico
                    )

                    print(
                        "Diferença absoluta:",
                        diferenca
                    )

                    if diferenca < 0.000001:

                        print()
                        print(
                            "RESULTADO: COINCIDÊNCIA EXATA"
                        )

                    elif diferenca < 0.001:

                        print()
                        print(
                            "RESULTADO: VALORES PRATICAMENTE IGUAIS"
                        )

                    elif diferenca < 0.01:

                        print()
                        print(
                            "RESULTADO: VALORES MUITO PRÓXIMOS"
                        )

                    else:

                        print()
                        print(
                            "RESULTADO: VALORES DIFERENTES"
                        )

            else:

                print(
                    "Não foi possível calcular: "
                    "denominador igual a zero."
                )

        else:

            print(
                "Não foi possível recalcular porque "
                "uma ou mais entradas não possuem "
                "valor numérico válido."
            )

    print()
    print("=" * 70)
    print("TESTE FINALIZADO")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()