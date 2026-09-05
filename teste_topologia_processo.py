from topologia_processo import (
    avaliar_contexto_dados,
    avaliar_elegibilidade_fisica,
    construir_resolucao_tag,
    identificar_rota,
    ranquear_tags_para_objetivo,
    resolver_objetivo_estudo,
    sugerir_termos_busca_objetivo,
)


def test_rotas_confirmadas():
    assert identificar_rota("TA-1 | Carga DQO Entrada") == "ROTA_ETF1"
    assert identificar_rota("TA-04 | Oxigenio dissolvido") == "ROTA_ETF2"
    assert identificar_rota("TUT-DS2") == "ROTA_ETF2"
    assert identificar_rota("TUT-DS1") == "ROTA_ETF1"


def test_grupos_ds_da_tela_pi_vision():
    for numero in range(1, 7):
        assert identificar_rota(f"DS-{numero}") == "ROTA_ETF1"
    for numero in range(7, 13):
        assert identificar_rota(f"DS-{numero}") == "ROTA_ETF2"


def test_etf_consolidado_nao_e_forcado_para_uma_linha():
    assert identificar_rota("ETF") is None
    assert identificar_rota("EIC") is None


def test_ta1_nao_e_elegivel_para_tut_ds2():
    resultado = avaliar_elegibilidade_fisica(
        "TUT-DS2",
        "TA-1 | Carga DQO Entrada",
    )
    assert resultado["elegivel"] is False
    assert resultado["classificacao_topologica"] == "INCOMPATIVEL"


def test_ta3_e_elegivel_para_tut_ds2():
    resultado = avaliar_elegibilidade_fisica(
        "TUT-DS2",
        "TA-3 | Carga DQO Entrada",
    )
    assert resultado["elegivel"] is True
    assert resultado["classificacao_topologica"] == "ROTA DIRETA"


def test_metadado_af_tem_prioridade():
    resultado = avaliar_elegibilidade_fisica(
        "Nome generico",
        "Outro nome generico",
        {"CTX_Grupo_Rota_Recebido": "ROTA_ETF2"},
        {"CTX_Grupo_Rota": "ROTA_ETF1"},
    )
    assert resultado["elegivel"] is False


def test_sem_rota_permanece_com_ressalva():
    resultado = avaliar_elegibilidade_fisica("TUT-DS2", "Temperatura ambiente")
    assert resultado["elegivel"] is True
    assert resultado["classificacao_topologica"] == "SEM ROTA CONHECIDA"


def test_rota_pode_ser_obtida_do_caminho_af():
    assert identificar_rota(
        "Turbidez",
        {"caminho_af": "ETE > Tratamento > ETF-2 > Saida"},
    ) == "ROTA_ETF2"


def test_consideracao_de_dados_e_separada_do_processo():
    avaliacao = avaliar_contexto_dados(
        "Turbidez",
        {
            "pi_point": "TUT-DS2",
            "caminho_af": "ETE > ETF-2 > Saida",
            "fonte_dados": "PI_DATA_ARCHIVE_DIRETO",
        },
    )
    assert avaliacao["contexto_confirmado"] is True
    assert avaliacao["observacoes_dados"] == []


def test_conflito_entre_tag_e_af_bloqueia_relacao():
    metadados = {
        "pi_point": "TUT-DS2",
        "caminho_af": "ETE > ETF-1 > Saida",
    }
    avaliacao = avaliar_contexto_dados("Turbidez", metadados)
    assert avaliacao["contexto_confirmado"] is False
    resultado = avaliar_elegibilidade_fisica(
        "Turbidez",
        "TA-3 | Carga",
        metadados,
        {"caminho_af": "ETE > TA-3"},
    )
    assert resultado["elegivel"] is False
    assert resultado["classificacao_topologica"] == "CONTEXTO AMBIGUO"


def test_objetivo_identifica_turbidez_etf2_sem_informar_tag():
    resultado = resolver_objetivo_estudo(
        "Por que houve piora da turbidez do ETF-2?"
    )
    assert resultado is not None
    assert resultado["tag_principal"] == "TUT-DS2"
    assert resultado["rota"] == "ROTA_ETF2"
    assert resultado["origens_elegiveis"] == ["TA-3", "TA-4"]


def test_objetivo_com_tag_explicita_identifica_rota():
    resultado = resolver_objetivo_estudo(
        "Investigar a turbidez TUT-DS1"
    )
    assert resultado is not None
    assert resultado["tag_principal"] == "TUT-DS1"
    assert resultado["rota"] == "ROTA_ETF1"
    assert resultado["requer_confirmacao"] is False


def test_objetivo_identifica_amonia_etf1_sem_modo_avancado():
    resultado = resolver_objetivo_estudo(
        "Por que existe aumento de NNH3 na saída da ETF-1?"
    )
    assert resultado is not None
    assert resultado["indicador"] == "Amônia"
    assert resultado["tag_principal"] == "NNH3 ETF-1"
    assert resultado["rota"] == "ROTA_ETF1"
    assert resultado["requer_confirmacao"] is True
    assert resultado["origens_elegiveis"] == ["TA-1", "TA-2"]
    assert resultado["decantadores_elegiveis"] == [
        "DS-1", "DS-2", "DS-3", "DS-4", "DS-5", "DS-6"
    ]


def test_objetivo_identifica_sinonimo_amonia_etf2():
    resultado = resolver_objetivo_estudo(
        "Investigar nitrogênio amoniacal no ETF 2"
    )
    assert resultado is not None
    assert resultado["tag_principal"] == "NNH3 ETF-2"
    assert resultado["rota"] == "ROTA_ETF2"


def test_objetivo_sem_destino_nao_inventa_rota():
    assert resolver_objetivo_estudo("Investigar aumento de amônia") is None


def test_descoberta_generica_extrai_indicador_sem_fixar_catalogo():
    termos = sugerir_termos_busca_objetivo(
        "Por que houve aumento da corrente do soprador no TA-3?"
    )
    assert "CORRENTE" in termos
    assert "SOPRADOR" in termos


def test_ranking_generico_respeita_rota_do_objetivo():
    ranking = ranquear_tags_para_objetivo(
        "Analisar corrente do soprador no TA-3",
        ["CORRENTE-SOPRADOR-TA1", "CORRENTE-SOPRADOR-TA3"],
    )
    assert [item["tag_principal"] for item in ranking] == [
        "CORRENTE-SOPRADOR-TA3"
    ]


def test_tag_generica_confirmada_herda_topologia_sem_nova_regra():
    resultado = construir_resolucao_tag(
        "Analisar corrente do soprador no TA-3",
        "CORRENTE-SOPRADOR-TA3",
    )
    assert resultado is not None
    assert resultado["rota"] == "ROTA_ETF2"
    assert resultado["origens_elegiveis"] == ["TA-3", "TA-4"]
