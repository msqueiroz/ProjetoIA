from adaptador_ia import consultar_ia


contexto_teste = {
    "variavel_principal": "NH3 ETF-1",

    "principal_hipotese": {
        "variavel": "TA-1 | COT EIC1",
        "defasagem": "+13 h 45 min",
        "melhor_correlacao": 0.391,
        "correlacao_sem_defasagem": 0.303,
        "ganho_abs_correlacao": 0.088,
        "pontos_validos": 127,
        "score_evidencia_temporal": 65,
        "classificacao_evidencia_temporal": "MODERADA",
    },

    "outras_hipoteses": [
        {
            "variavel": "TA-2 | Carga DQO Entrada",
            "defasagem": "+8 h",
            "melhor_correlacao": 0.916,
            "pontos_validos": 13,
            "score_evidencia_temporal": 58,
            "classificacao_evidencia_temporal": "BAIXA",
        }
    ],

    "cobertura_principal_pct": 99.8,
    "registros_principal": 253,

    "lacunas": [
        "A evidência temporal ainda não atingiu nível forte.",
        "A hipótese deve ser validada quanto à coerência física.",
    ],

    "proximos_passos": [
        "Verificar compatibilidade da defasagem com o tempo de retenção.",
        "Comparar carga, vazão, aeração e qualidade afluente.",
        "Repetir o estudo em outra janela temporal.",
    ],

    "regra_de_seguranca": (
        "Não afirmar causalidade nem recomendar controle automático "
        "com base apenas nestas evidências."
    ),
}


resultado = consultar_ia(
    contexto_ia=contexto_teste,
    provedor="OLLAMA",
    modelo="llama3.2:3b",
)


print("=" * 70)
print("RESULTADO")
print("=" * 70)

print("OK:", resultado["ok"])
print("Provedor:", resultado["provedor"])
print("Modelo:", resultado["modelo"])
print("Erro:", resultado["erro"])

print()
print("=" * 70)
print("INTERPRETAÇÃO DA IA")
print("=" * 70)

print(resultado["resposta"])