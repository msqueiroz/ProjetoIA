import pandas as pd
import requests
from manual import buscar_no_manual

# =========================
# CONFIGURAÇÕES
# =========================

ARQUIVO_CSV = "dadosMult.csv"
MODELO_OLLAMA = "gemma3:1b"
URL_OLLAMA = "http://localhost:11434/api/generate"


# =========================
# FUNÇÃO PARA CONSULTAR O OLLAMA
# =========================

def consultar_ollama(categoria, causa, confianca, evidencias, horario, trecho_manual):

    evidencias_texto = "\n".join(
        f"- {evidencia}" for evidencia in evidencias
    )
    if trecho_manual:
        contexto_manual = trecho_manual
    else:
        contexto_manual = "Nenhuma informação correspondente encontrada no manual."

    prompt = f"""
Você é uma interface de texto para um sistema de diagnóstico industrial.

REGRAS OBRIGATÓRIAS:
- Não faça diagnóstico próprio.
- Não invente causas.
- Não invente recomendações.
- Use somente os dados calculados pelo sistema e o trecho do manual fornecido.
- Diferencie claramente o que veio dos dados e o que veio do manual.
- Não altere nomes técnicos.
- Não acrescente informações que não estejam nas fontes abaixo.
- O diagnóstico calculado pelo sistema tem prioridade.
- A ausência de informação no manual não significa ausência de falha.
- O manual deve ser utilizado apenas para contextualizar ou validar
  documentalmente o diagnóstico já calculado.

DADOS DO EVENTO:

Horário da parada:
{horario}

Categoria:
{categoria}

Causa calculada:
{causa}

Confiança:
{confianca}%

Evidências:
{evidencias_texto}

TRECHO DO MANUAL OPERACIONAL:
{contexto_manual}

Responda em português claro e objetivo.

Use este formato:

Parada:
[horário]

Diagnóstico:
[causa e confiança]

Evidências dos dados:
[resuma somente as evidências fornecidas]

Referência do manual:
[explique somente o que o trecho do manual informa]

Conclusão:
[Apresente a conclusão calculada pelo sistema com base na causa,
confiança e evidências fornecidas.

Se houver referência no manual, informe se o diagnóstico é coerente
com o que está documentado.

Se NÃO houver referência no manual, mantenha o diagnóstico calculado
pelos dados e informe apenas que não foi possível validá-lo ou
contextualizá-lo com o manual operacional.

A ausência de informação no manual NÃO invalida o diagnóstico
calculado pelo sistema.]
"""

    payload = {
        "model": MODELO_OLLAMA,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0
        }   
    }

    try:
        resposta = requests.post(
            URL_OLLAMA,
            json=payload,
            timeout=120
        )

        resposta.raise_for_status()

        resultado = resposta.json()

        return resultado["response"]

    except Exception as erro:
        return f"Erro ao consultar Ollama: {erro}"


# =========================
# CARREGAR DADOS
# =========================

dados = pd.read_csv(ARQUIVO_CSV)

dados["data_hora"] = pd.to_datetime(
    dados["data_hora"]
)

dados["status_anterior"] = (
    dados["status_bomba"].shift(1)
)


# =========================
# DETECTAR PARADAS
# =========================

paradas = dados[
    (dados["status_anterior"] == 1) &
    (dados["status_bomba"] == 0)
]

print("=== DIAGNÓSTICO DE PARADAS ===")


# =========================
# ANALISAR PARADAS
# =========================

for indice, parada in paradas.iterrows():

    horario_parada = parada["data_hora"]

    inicio = max(0, indice - 4)
    historico = dados.iloc[inicio:indice]

    ultimo = historico.iloc[-1]

    hipoteses = {

        "ALTA TEMPERATURA DE MANCAL": {
            "score": 0,
            "evidencias": []
        },

        "SUBTENSÃO": {
            "score": 0,
            "evidencias": []
        },

        "VIBRAÇÃO ALTA": {
            "score": 0,
            "evidencias": []
        },

        "NÍVEL BAIXO": {
            "score": 0,
            "evidencias": []
        },
        "FALHA DE INSTRUMENTAÇÃO DE NÍVEL": {
            "score": 0,
            "evidencias": []
},
    }

    categorias = {
        "ALTA TEMPERATURA DE MANCAL": "MECÂNICA",
        "VIBRAÇÃO ALTA": "MECÂNICA",
        "SUBTENSÃO": "ELÉTRICA",
        "NÍVEL BAIXO": "OPERACIONAL / PROCESSO",
        "FALHA DE INSTRUMENTAÇÃO DE NÍVEL": "INSTRUMENTAÇÃO"
    }


    # =========================
    # TEMPERATURA
    # =========================

    if ultimo["temp_mancal_c"] >= 90:

        hipoteses[
            "ALTA TEMPERATURA DE MANCAL"
        ]["score"] += 40

        hipoteses[
            "ALTA TEMPERATURA DE MANCAL"
        ]["evidencias"].append(
            f"Temperatura atingiu "
            f"{ultimo['temp_mancal_c']} °C."
        )

    if "TRIP_TEMP_MANCAL" in historico["alarme"].values:

        hipoteses[
            "ALTA TEMPERATURA DE MANCAL"
        ]["score"] += 45

        hipoteses[
            "ALTA TEMPERATURA DE MANCAL"
        ]["evidencias"].append(
            "TRIP_TEMP_MANCAL registrado."
        )


    # =========================
    # SUBTENSÃO
    # =========================

    menor_tensao = historico["tensao_v"].min()

    if menor_tensao < 400:

        hipoteses[
            "SUBTENSÃO"
        ]["score"] += 40

        hipoteses[
            "SUBTENSÃO"
        ]["evidencias"].append(
            f"Tensão mínima registrada: "
            f"{menor_tensao} V."
        )

    if "TRIP_SUBTENSAO" in historico["alarme"].values:

        hipoteses[
            "SUBTENSÃO"
        ]["score"] += 45

        hipoteses[
            "SUBTENSÃO"
        ]["evidencias"].append(
            "TRIP_SUBTENSAO registrado."
        )


    # =========================
    # VIBRAÇÃO
    # =========================

    maior_vibracao = historico["vibracao_mm_s"].max()

    if maior_vibracao >= 7:

        hipoteses[
            "VIBRAÇÃO ALTA"
        ]["score"] += 40

        hipoteses[
            "VIBRAÇÃO ALTA"
        ]["evidencias"].append(
            f"Vibração máxima: "
            f"{maior_vibracao} mm/s."
        )

    if "TRIP_VIBRACAO" in historico["alarme"].values:

        hipoteses[
            "VIBRAÇÃO ALTA"
        ]["score"] += 45

        hipoteses[
            "VIBRAÇÃO ALTA"
        ]["evidencias"].append(
            "TRIP_VIBRACAO registrado."
        )


    # =========================
    # NÍVEL
    # =========================

    menor_nivel = historico["nivel_pct"].min()

    if menor_nivel <= 20:

        hipoteses[
            "NÍVEL BAIXO"
        ]["score"] += 40

        hipoteses[
            "NÍVEL BAIXO"
        ]["evidencias"].append(
            f"Nível mínimo: {menor_nivel}%."
        )

    if "TRIP_NIVEL_BAIXO" in historico["alarme"].values:

        hipoteses[
            "NÍVEL BAIXO"
        ]["score"] += 45

        hipoteses[
            "NÍVEL BAIXO"
        ]["evidencias"].append(
            "TRIP_NIVEL_BAIXO registrado."
        )
    # =========================
    # INSTRUMENTAÇÃO DE NÍVEL
    # =========================

    nivel_real_min = historico["nivel_pct"].min()
    sinal_nivel_min = historico["sinal_nivel_pct"].min()

    diferenca_nivel = abs(
        nivel_real_min - sinal_nivel_min
    )

    if diferenca_nivel >= 30:

        hipoteses[
            "FALHA DE INSTRUMENTAÇÃO DE NÍVEL"
        ]["score"] += 40

        hipoteses[
            "FALHA DE INSTRUMENTAÇÃO DE NÍVEL"
        ]["evidencias"].append(
            f"Inconsistência entre nível de processo "
            f"({nivel_real_min}%) e sinal do instrumento "
            f"({sinal_nivel_min}%)."
        )

    if "TRIP_SINAL_NIVEL" in historico["alarme"].values:

        hipoteses[
            "FALHA DE INSTRUMENTAÇÃO DE NÍVEL"
        ]["score"] += 45

        hipoteses[
            "FALHA DE INSTRUMENTAÇÃO DE NÍVEL"
        ]["evidencias"].append(
            "TRIP_SINAL_NIVEL registrado."
        )


    # =========================
    # RANKING
    # =========================

    ranking = sorted(
        hipoteses.items(),
        key=lambda item: item[1]["score"],
        reverse=True
    )

    print(f"\nBomba parou em: {horario_parada}")

    print("\n=== RANKING DE HIPÓTESES ===")

    for posicao, (causa, dados_causa) in enumerate(
        ranking,
        start=1
    ):

        score = min(
            dados_causa["score"],
            100
        )

        print(
            f"\n{posicao}. "
            f"{causa} - {score}%"
        )

        for evidencia in dados_causa["evidencias"]:
            print(f"   - {evidencia}")


    # =========================
    # CAUSA PRINCIPAL
    # =========================

    causa_principal = ranking[0][0]

    confianca_principal = min(
        ranking[0][1]["score"],
        100
    )

    evidencias_principais = (
        ranking[0][1]["evidencias"]
    )

    categoria = categorias.get(
        causa_principal,
        "NÃO CLASSIFICADA"
    )


    # =========================
    # CONCLUSÃO
    # =========================

    print("\n=== CONCLUSÃO ===")
    print(f"Categoria: {categoria}")
    print(f"Causa mais provável: {causa_principal}")
    print(f"Confiança: {confianca_principal}%")

    print("\nEvidências:")

    for evidencia in evidencias_principais:
        print(f"- {evidencia}")


    # =========================
    # MAPA DO MANUAL
    # =========================

    mapa_manual = {
        "ALTA TEMPERATURA DE MANCAL": "Alta temperatura de mancal",
        "SUBTENSÃO": "Subtensão",
        "VIBRAÇÃO ALTA": "Vibração alta",
        "NÍVEL BAIXO": "Nível baixo",
        "FALHA DE INSTRUMENTAÇÃO DE NÍVEL": "Instrumentação"
    }

    termo_manual = mapa_manual.get(
        causa_principal
    )

    trechos_manual = []

    if termo_manual:
        trechos_manual = buscar_no_manual(
            termo_manual
        )


    # =========================
    # CONSULTA AO MANUAL
    # =========================

    print("\n=== CONSULTA AO MANUAL ===")

    if trechos_manual:
        print(trechos_manual[0])

    else:
        print(
            "Nenhuma informação correspondente "
            "encontrada no manual."
        )

    trecho_para_ia = ""

    if trechos_manual:
        trecho_para_ia = trechos_manual[0]

    # =========================
    # CONSULTAR OLLAMA
    # =========================

    print("\nConsultando IA local...")

    explicacao = consultar_ollama(
    categoria,
    causa_principal,
    confianca_principal,
    evidencias_principais,
    horario_parada,
    trecho_para_ia
    )

    print("\n=== RESPOSTA DA IA ===")
    print(explicacao)

    print("\n\n" + "=" * 60)