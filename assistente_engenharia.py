def montar_resumo_engenharia(
    evento,
    categoria,
    causa,
    confianca,
    evidencias,
    documento,
    referencias
):

    return {
        "evento": evento,
        "categoria": categoria,
        "causa": causa,
        "confianca": confianca,
        "evidencias": evidencias,
        "documento": documento,
        "referencias": referencias
    }