"""
Base estruturada de conhecimento técnico da ETE.

Objetivo:
- Representar conhecimento documental de engenharia de forma estruturada.
- Manter rastreabilidade da origem de cada informação.
- Fornecer contexto técnico para o Motor de Engenharia e para a MAR.IA.

Fonte inicial:
MO-ETE-001 - Manual de Operação da ETE
Rev. 3 - 09/01/2025
"""


FONTE_MO_ETE_001 = {
    "documento": "MO-ETE-001",
    "titulo": "Manual de Operação da ETE",
    "revisao": "3",
    "data_revisao": "09/01/2025",
}


ESTRUTURA_PROCESSO_ETE = {
    "nome": "Estação de Tratamento de Efluentes - ETE",

    "objetivo_processo": (
        "Tratamento biológico aeróbio, por processo de lodos ativados, "
        "dos efluentes orgânicos recebidos pela ETE."
    ),

    "origem_afluente": {
        "origem": "E.E. Atlântica",
        "destino": "ETE",
        "fonte": FONTE_MO_ETE_001,
        "secao": "Introdução / Descrição do Processo de Tratamento de Efluentes",
    },

    "destino_efluente_tratado": {
        "destino": "E.E. Capivara",
        "destino_final": "Sistema de Disposição Oceânica - SDO",
        "fonte": FONTE_MO_ETE_001,
        "secao": "Introdução / Descrição do Processo de Tratamento de Efluentes",
    },

    "etapas_principais": [
        {
            "ordem": 1,
            "codigo": "BEQ",
            "nome": "Bacia de Equalização",
            "tipo": "Equalização",

            "funcao": (
                "Amenizar variações de vazão, pH, temperatura, toxicidade "
                "e carga orgânica do afluente antes do tratamento biológico."
            ),

            "variaveis_relevantes": [
                "Vazão",
                "pH",
                "Temperatura",
                "Toxicidade",
                "Carga orgânica",
                "COT",
                "TCO",
            ],

            "volume_util_m3": 58000,

            "fonte": FONTE_MO_ETE_001,
            "secao": "1.1 Processo de Equalização / 1.1.1 Bacia de Equalização",
        },

        {
            "ordem": 2,
            "codigo": "TA-1",
            "nome": "Tanque de Aeração 1",
            "tipo": "Lodos Ativados",

            "configuracao": "Mistura completa",

            "volume_util_m3": 35100,
            "vazao_maxima_m3_h": 1320,
            "tempo_detencao_projeto_h": 26.6,
            "numero_aeradores": 15,

            "variaveis_relevantes": [
                "Oxigênio dissolvido",
                "Sólidos suspensos",
                "Idade de lodo",
                "COT",
                "NH3",
                "TCO",
                "Fator de carga",
                "Vazão",
                "Recirculação de lodo",
                "Estado dos aeradores",
                "Energia",
            ],

            "fonte": FONTE_MO_ETE_001,
            "secao": "1.2.1 Tanques de Aeração / Tanque de Aeração 1",
        },

        {
            "ordem": 2,
            "codigo": "TA-2",
            "nome": "Tanque de Aeração 2",
            "tipo": "Lodos Ativados",

            "configuracao": "Valo de Fluxo Orbital - Carrossel",

            "volume_util_m3": 39600,
            "vazao_maxima_m3_h": 1452,
            "tempo_detencao_projeto_h": 27.3,
            "numero_aeradores": 10,

            "variaveis_relevantes": [
                "Oxigênio dissolvido",
                "Sólidos suspensos",
                "Idade de lodo",
                "COT",
                "NH3",
                "TCO",
                "Fator de carga",
                "Vazão",
                "Recirculação de lodo",
                "Estado dos aeradores",
                "Energia",
            ],

            "fonte": FONTE_MO_ETE_001,
            "secao": "1.2.1 Tanques de Aeração / Tanque de Aeração 2",
        },

        {
            "ordem": 2,
            "codigo": "TA-3",
            "nome": "Tanque de Aeração 3",
            "tipo": "Lodos Ativados",

            "configuracao": "Mistura completa",

            "volume_util_m3": 52000,
            "vazao_maxima_m3_h": 2000,
            "tempo_detencao_projeto_h": 27.2,
            "numero_aeradores": 20,

            "variaveis_relevantes": [
                "Oxigênio dissolvido",
                "Sólidos suspensos",
                "Idade de lodo",
                "COT",
                "NH3",
                "TCO",
                "Fator de carga",
                "Vazão",
                "Recirculação de lodo",
                "Estado dos aeradores",
                "Energia",
            ],

            "fonte": FONTE_MO_ETE_001,
            "secao": "1.3.1 Tanques de Aeração / Tanque de Aeração 3",
        },

        {
            "ordem": 2,
            "codigo": "TA-4",
            "nome": "Tanque de Aeração 4",
            "tipo": "Lodos Ativados",

            "configuracao": "Valo de Fluxo Orbital - Carrossel",

            "volume_util_m3": 52000,
            "vazao_maxima_m3_h": 1914,
            "numero_aeradores_superficiais": 14,
            "numero_misturadores_instalados": 8,

            "variaveis_relevantes": [
                "Oxigênio dissolvido",
                "Sólidos suspensos",
                "Idade de lodo",
                "COT",
                "NH3",
                "TCO",
                "Fator de carga",
                "Vazão",
                "Recirculação de lodo",
                "Estado dos aeradores",
                "Energia",
            ],

            "fonte": FONTE_MO_ETE_001,
            "secao": "1.3.1 Tanques de Aeração / Tanque de Aeração 4",
        },
    ],

    "distribuicao_apos_beq": {
        "origem": "BEQ",
        "divisor": "CDV-6",

        "destinos": [
            "TA-1 e TA-2",
            "TA-3",
            "TA-4",
        ],

        "observacao": (
            "Após a equalização, o fluxo é dividido e encaminhado "
            "independentemente aos diferentes tanques de aeração."
        ),

        "fonte": FONTE_MO_ETE_001,
        "secao": "1.1 Processo de Equalização",
    },
}


def obter_estrutura_processo_ete():
    """
    Retorna a estrutura documental conhecida da ETE.
    """
    return ESTRUTURA_PROCESSO_ETE