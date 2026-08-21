def diagnosticar_parada(dados, indice):

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
        }
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
            f"Temperatura atingiu {ultimo['temp_mancal_c']} °C."
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
        hipoteses["SUBTENSÃO"]["score"] += 40

        hipoteses["SUBTENSÃO"]["evidencias"].append(
            f"Tensão mínima registrada: {menor_tensao} V."
        )

    if "TRIP_SUBTENSAO" in historico["alarme"].values:
        hipoteses["SUBTENSÃO"]["score"] += 45

        hipoteses["SUBTENSÃO"]["evidencias"].append(
            "TRIP_SUBTENSAO registrado."
        )

    # =========================
    # VIBRAÇÃO
    # =========================

    maior_vibracao = historico["vibracao_mm_s"].max()

    if maior_vibracao >= 7:
        hipoteses["VIBRAÇÃO ALTA"]["score"] += 40

        hipoteses["VIBRAÇÃO ALTA"]["evidencias"].append(
            f"Vibração máxima: {maior_vibracao} mm/s."
        )

    if "TRIP_VIBRACAO" in historico["alarme"].values:
        hipoteses["VIBRAÇÃO ALTA"]["score"] += 45

        hipoteses["VIBRAÇÃO ALTA"]["evidencias"].append(
            "TRIP_VIBRACAO registrado."
        )

    # =========================
    # NÍVEL BAIXO
    # =========================

    menor_nivel = historico["nivel_pct"].min()

    if menor_nivel <= 20:
        hipoteses["NÍVEL BAIXO"]["score"] += 40

        hipoteses["NÍVEL BAIXO"]["evidencias"].append(
            f"Nível mínimo: {menor_nivel}%."
        )

    if "TRIP_NIVEL_BAIXO" in historico["alarme"].values:
        hipoteses["NÍVEL BAIXO"]["score"] += 45

        hipoteses["NÍVEL BAIXO"]["evidencias"].append(
            "TRIP_NIVEL_BAIXO registrado."
        )

    # =========================
    # INSTRUMENTAÇÃO DE NÍVEL
    # =========================

    if (
        "nivel_pct" in historico.columns
        and "sinal_nivel_pct" in historico.columns
    ):

        nivel_real_min = historico[
            "nivel_pct"
        ].min()

        sinal_nivel_min = historico[
            "sinal_nivel_pct"
        ].min()

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

        if (
            "alarme" in historico.columns
            and "TRIP_SINAL_NIVEL"
            in historico["alarme"].values
        ):

            hipoteses[
                "FALHA DE INSTRUMENTAÇÃO DE NÍVEL"
            ]["score"] += 45

            hipoteses[
                "FALHA DE INSTRUMENTAÇÃO DE NÍVEL"
            ]["evidencias"].append(
                "TRIP_SINAL_NIVEL registrado."
            )
    # =========================
    # RANKING DAS HIPÓTESES
    # =========================

    ranking = sorted(
        hipoteses.items(),
        key=lambda item: item[1]["score"],
        reverse=True
    )

    causa_principal = ranking[0][0]

    confianca = min(
        ranking[0][1]["score"],
        100
    )

    evidencias = ranking[0][1]["evidencias"]

    categoria = categorias.get(
        causa_principal,
        "NÃO CLASSIFICADA"
    )

    # =========================
    # RETORNO DA FUNÇÃO
    # =========================

    return {
        "categoria": categoria,
        "causa": causa_principal,
        "confianca": confianca,
        "evidencias": evidencias,
        "ranking": ranking
    }