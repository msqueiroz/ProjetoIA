# O SDK do Copilot Studio e o MSAL expõem objetos dinâmicos sem tipagem completa.
# As regras abaixo evitam falsos positivos do Pylance sem ocultar erros de sintaxe.
# pyright: reportMissingTypeStubs=false, reportUnusedImport=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportCallIssue=false, reportArgumentType=false, reportAssignmentType=false, reportOperatorIssue=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportOptionalIterable=false, reportOptionalOperand=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportReturnType=false, reportPossiblyUnboundVariable=false
"""
adaptador_ia.py

Camada de abstração para interpretação assistida por IA no ProjetoIA.

Princípios:
- o motor determinístico continua sendo a fonte da verdade;
- a IA recebe somente o contexto estruturado da investigação;
- a IA não recalcula nem altera evidências;
- a IA não deve afirmar causalidade;
- a IA não deve recomendar alteração automática de controle/operação;
- o conhecimento documental deve ser usado como referência técnica,
  preservando sua origem, revisão e aplicabilidade.
"""

from __future__ import annotations

import asyncio
import ctypes
import importlib.util
import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


OLLAMA_URL_PADRAO = "http://localhost:11434/api/chat"
CAMINHO_CACHE_MARIA = (
    Path(__file__).resolve().parent
    / ".streamlit"
    / "maria_token_cache.bin"
)


class _DataBlob(ctypes.Structure):
    """Estrutura binária usada pela proteção de dados do Windows."""

    _fields_ = [
        ("cbData", ctypes.c_ulong),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _proteger_cache_windows(conteudo: str) -> bytes:
    """Criptografa o cache para o usuário atual do Windows."""

    dados = conteudo.encode("utf-8")
    buffer_entrada = ctypes.create_string_buffer(dados)
    entrada = _DataBlob(
        len(dados),
        ctypes.cast(buffer_entrada, ctypes.POINTER(ctypes.c_ubyte)),
    )
    saida = _DataBlob()
    sucesso = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(entrada),
        "ProjetoIA MAR.IA",
        None,
        None,
        None,
        0x01,
        ctypes.byref(saida),
    )
    if not sucesso:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(saida.pbData, saida.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(saida.pbData)


def _desproteger_cache_windows(conteudo: bytes) -> str:
    """Descriptografa o cache pertencente ao usuário atual."""

    buffer_entrada = ctypes.create_string_buffer(conteudo)
    entrada = _DataBlob(
        len(conteudo),
        ctypes.cast(buffer_entrada, ctypes.POINTER(ctypes.c_ubyte)),
    )
    saida = _DataBlob()
    sucesso = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(entrada),
        None,
        None,
        None,
        None,
        0x01,
        ctypes.byref(saida),
    )
    if not sucesso:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(saida.pbData, saida.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(saida.pbData)


def _carregar_cache_maria() -> str:
    """Carrega o cache persistente, ignorando arquivos inválidos."""

    if os.name != "nt" or not CAMINHO_CACHE_MARIA.exists():
        return ""
    try:
        return _desproteger_cache_windows(CAMINHO_CACHE_MARIA.read_bytes())
    except Exception:
        return ""


def _salvar_cache_maria(conteudo: str) -> None:
    """Salva o cache criptografado e restrito ao usuário do Windows."""

    if os.name != "nt" or not conteudo:
        return
    CAMINHO_CACHE_MARIA.parent.mkdir(parents=True, exist_ok=True)
    CAMINHO_CACHE_MARIA.write_bytes(_proteger_cache_windows(conteudo))


def verificar_maria() -> dict[str, Any]:
    """Verifica a configuração local necessária para usar a MAR.IA."""
    nomes = ("MARIA_CLIENT_ID", "MARIA_TENANT_ID", "MARIA_ENVIRONMENT_ID", "MARIA_SCHEMA_NAME")
    ausentes = [nome for nome in nomes if not os.getenv(nome, "").strip()]
    try:
        dependencias_ok = (
            importlib.util.find_spec("msal") is not None
            and importlib.util.find_spec(
                "microsoft_agents.copilotstudio.client"
            ) is not None
        )
    except (ImportError, ModuleNotFoundError):
        dependencias_ok = False

    if not dependencias_ok:
        return {
            "disponivel": False,
            "ausentes": ausentes,
            "erro": "Dependências da MAR.IA não instaladas.",
        }
    return {"disponivel": not ausentes, "ausentes": ausentes, "erro": None}


def _aplicativo_maria(cache_serializado: str = "") -> tuple[Any, Any, str]:
    """Cria o cliente MSAL e restaura seu cache de autenticação."""
    from msal import PublicClientApplication, SerializableTokenCache
    from microsoft_agents.copilotstudio.client import ConnectionSettings, CopilotClient

    cache = SerializableTokenCache()

    # O cache protegido do Windows é a fonte persistente. Ele tem
    # prioridade sobre um estado vazio ou antigo mantido pelo navegador.
    cache_persistente = _carregar_cache_maria()
    if cache_persistente:
        cache_serializado = cache_persistente

    if cache_serializado:
        cache.deserialize(cache_serializado)
    settings = ConnectionSettings(
        environment_id=os.environ["MARIA_ENVIRONMENT_ID"].strip(),
        agent_identifier=os.environ["MARIA_SCHEMA_NAME"].strip(),
    )
    scope = CopilotClient.scope_from_settings(settings)
    aplicativo = PublicClientApplication(
        client_id=os.environ["MARIA_CLIENT_ID"].strip(),
        authority="https://login.microsoftonline.com/" + os.environ["MARIA_TENANT_ID"].strip(),
        token_cache=cache,
    )
    return aplicativo, cache, scope


def obter_token_maria_silencioso(cache_serializado: str = "") -> dict[str, Any]:
    """Tenta reutilizar uma sessão Microsoft já autenticada."""
    try:
        aplicativo, cache, scope = _aplicativo_maria(cache_serializado)
        contas = aplicativo.get_accounts()
        resultado = aplicativo.acquire_token_silent([scope], account=contas[0]) if contas else None
        token = resultado.get("access_token") if resultado else None
        cache_atual = cache.serialize()
        _salvar_cache_maria(cache_atual)
        return {"ok": bool(token), "token": str(token or ""), "cache": cache_atual, "erro": None}
    except Exception as erro:
        return {"ok": False, "token": "", "cache": cache_serializado, "erro": str(erro)}


def iniciar_login_maria(cache_serializado: str = "") -> dict[str, Any]:
    """Inicia o login Microsoft por código de dispositivo."""
    try:
        aplicativo, cache, scope = _aplicativo_maria(cache_serializado)
        fluxo = aplicativo.initiate_device_flow(scopes=[scope])
        if "user_code" not in fluxo:
            raise RuntimeError(fluxo.get("error_description", "falha não informada"))
        return {"ok": True, "fluxo": fluxo, "cache": cache.serialize(), "erro": None}
    except Exception as erro:
        return {"ok": False, "erro": str(erro)}


def concluir_login_maria(fluxo: Mapping[str, Any], cache_serializado: str = "") -> dict[str, Any]:
    """Conclui um login previamente iniciado pelo usuário."""
    try:
        aplicativo, cache, _ = _aplicativo_maria(cache_serializado)
        resultado = aplicativo.acquire_token_by_device_flow(dict(fluxo))
        token = resultado.get("access_token")
        if not token:
            raise RuntimeError(resultado.get("error_description", "login não concluído"))
        cache_atual = cache.serialize()
        _salvar_cache_maria(cache_atual)
        return {"ok": True, "token": str(token), "cache": cache_atual, "erro": None}
    except Exception as erro:
        return {"ok": False, "token": "", "cache": cache_serializado, "erro": str(erro)}


def verificar_ollama(
    url_base: str = "http://localhost:11434",
    timeout: int = 3,
) -> dict[str, Any]:
    """Verifica se o serviço local do Ollama está acessível."""

    url = f"{url_base.rstrip('/')}/api/tags"

    try:
        requisicao = urllib.request.Request(
            url,
            method="GET",
        )

        with urllib.request.urlopen(
            requisicao,
            timeout=timeout,
        ) as resposta:
            dados_brutos: Any = json.loads(
                resposta.read().decode("utf-8")
            )

        dados: dict[str, Any] = (
            dados_brutos
            if isinstance(dados_brutos, dict)
            else {}
        )

        modelos: list[str] = []
        modelos_brutos: Any = dados.get("models", [])

        if isinstance(modelos_brutos, list):
            for item in modelos_brutos:
                if not isinstance(item, dict):
                    continue

                nome: Any = item.get("name")

                if isinstance(nome, str) and nome:
                    modelos.append(nome)

        return {
            "disponivel": True,
            "modelos": modelos,
            "erro": None,
        }

    except Exception as erro:
        return {
            "disponivel": False,
            "modelos": [],
            "erro": str(erro),
        }


def _primeiro_valor(
    dados: Mapping[str, Any],
    chaves: Sequence[str],
    padrao: Any = None,
) -> Any:
    """Retorna o primeiro valor existente entre chaves alternativas."""

    for chave in chaves:
        valor: Any = dados.get(chave)

        if valor is not None and valor != "":
            return valor

    return padrao


def _formatar_numero(
    valor: float | int | str | None,
    casas: int = 3,
) -> str:
    """Formata números sem alterar o valor recebido do motor."""

    if valor is None:
        return "não informado"

    try:
        return f"{float(valor):.{casas}f}"
    except (TypeError, ValueError):
        return str(valor)


def _formatar_lag(
    hipotese: Mapping[str, Any],
) -> str:
    """Obtém a representação textual da defasagem sem recalculá-la."""

    valor = _primeiro_valor(
        hipotese,
        [
            "defasagem",
            "lag_formatado",
            "defasagem_formatada",
            "lag_texto",
            "defasagem_texto",
            "melhor_lag_formatado",
            "melhor_defasagem_formatada",
        ],
    )

    if valor is not None:
        return str(valor)

    valor = _primeiro_valor(
        hipotese,
        [
            "lag_horas",
            "defasagem_horas",
            "melhor_lag_horas",
        ],
    )

    if valor is not None:
        return f"{valor} h"

    valor = _primeiro_valor(
        hipotese,
        [
            "lag_minutos",
            "defasagem_minutos",
            "melhor_lag_minutos",
        ],
    )

    if valor is not None:
        return f"{valor} min"

    return "não informado"


def _normalizar_lista_dict(
    valor: Any,
) -> list[dict[str, Any]]:
    """Normaliza qualquer entrada compatível para lista de dicionários."""

    if isinstance(valor, dict):
        return [valor]

    if not isinstance(valor, list):
        return []

    resultado: list[dict[str, Any]] = []

    for item in valor:
        if isinstance(item, dict):
            resultado.append(item)

    return resultado


def _compactar_hipotese(
    item: Mapping[str, Any],
) -> dict[str, Any]:
    """Mantém somente os campos necessários para a interpretação."""

    return {
        "variavel": _primeiro_valor(
            item,
            [
                "variavel",
                "variavel_comparacao",
                "nome_variavel",
            ],
            "não informada",
        ),
        "lag": _formatar_lag(item),
        "correlacao_com_lag": _primeiro_valor(
            item,
            [
                "melhor_correlacao",
                "correlacao_com_lag",
                "correlacao_defasada",
                "correlacao",
            ],
        ),
        "correlacao_sem_lag": _primeiro_valor(
            item,
            [
                "correlacao_sem_defasagem",
                "correlacao_sem_lag",
                "correlacao_base",
                "correlacao_zero",
                "correlacao_lag_zero",
            ],
        ),
        "ganho_correlacao": _primeiro_valor(
            item,
            [
                "ganho_abs_correlacao",
                "ganho_correlacao",
                "ganho",
                "ganho_vs_zero",
            ],
        ),
        "pares_validos": _primeiro_valor(
            item,
            [
                "pontos_validos",
                "pares_validos",
                "quantidade_pares",
            ],
        ),
        "score_evidencia": _primeiro_valor(
            item,
            [
                "score_evidencia_temporal",
                "score_evidencia",
                "score_temporal",
            ],
        ),
        "classe_evidencia": _primeiro_valor(
            item,
            [
                "classificacao_evidencia_temporal",
                "classe_evidencia",
                "classificacao_temporal",
                "nivel_evidencia",
            ],
        ),
    }


def compactar_contexto_engenharia(
    contexto_ia: Mapping[str, Any],
    limite_hipoteses: int = 3,
    limite_documentos: int = 3,
    limite_caracteres_trecho: int = 900,
) -> dict[str, Any]:
    """
    Compacta o contexto para o LLM.

    Suporta o esquema atual:
    - principal_hipotese
    - outras_hipoteses

    Mantém também compatibilidade com esquemas anteriores.
    """

    contexto: Mapping[str, Any] = contexto_ia or {}

    objetivo_estudo = _primeiro_valor(
        contexto,
        [
            "objetivo_estudo",
            "objetivo",
            "pergunta_estudo",
            "pergunta",
            "questao_investigacao",
        ],
    )

    alvo = _primeiro_valor(
        contexto,
        [
            "variavel_principal",
            "variavel_alvo",
            "alvo",
            "target",
        ],
        "não informada",
    )

    cobertura = _primeiro_valor(
        contexto,
        [
            "cobertura_principal_pct",
            "cobertura_pct",
            "cobertura_percentual",
        ],
    )

    registros = _primeiro_valor(
        contexto,
        [
            "registros_principal",
            "registros_validos",
            "total_registros",
        ],
    )

    hipoteses_origem: list[dict[str, Any]] = []

    principal_bruta: Any = contexto.get("principal_hipotese")

    if isinstance(principal_bruta, dict):
        hipoteses_origem.append(principal_bruta)

        outras = _normalizar_lista_dict(
            contexto.get("outras_hipoteses", [])
        )
        hipoteses_origem.extend(outras)

    else:
        hipoteses_antigas = _primeiro_valor(
            contexto,
            [
                "hipoteses",
                "hipoteses_temporais",
                "evidencias",
                "evidencias_temporais",
            ],
            [],
        )

        hipoteses_origem = _normalizar_lista_dict(
            hipoteses_antigas
        )

    hipoteses_compactas: list[dict[str, Any]] = [
        _compactar_hipotese(item)
        for item in hipoteses_origem[:limite_hipoteses]
    ]

    documentos_origem = _normalizar_lista_dict(
        contexto.get("conhecimento_documental", [])
    )

    documentos_compactos: list[dict[str, Any]] = []

    for item in documentos_origem[:limite_documentos]:
        texto_trecho = str(
            item.get("texto", "")
        ).strip()

        if len(texto_trecho) > limite_caracteres_trecho:
            texto_trecho = (
                texto_trecho[:limite_caracteres_trecho].rstrip()
                + "..."
            )

        documentos_compactos.append(
            {
                "documento": str(
                    item.get(
                        "documento",
                        "Documento técnico",
                    )
                ),
                "pagina": item.get("pagina"),
                "texto": texto_trecho,
            }
        )

    return {
        "objetivo_estudo": objetivo_estudo,
        "variavel_alvo": alvo,
        "cobertura_pct": cobertura,
        "registros_validos": registros,
        "evidencias": hipoteses_compactas,
        "documentacao": documentos_compactos,
        "modo_assistido_sem_correlacao": bool(
            contexto.get("modo_assistido_sem_correlacao", False)
        ),
        "resumo_variavel_alvo": contexto.get("resumo_variavel_alvo", {}),
        "contexto_fisico_conhecido": contexto.get(
            "contexto_fisico_conhecido",
            {},
        ),
        "consideracoes_dados": contexto.get("consideracoes_dados", []),
        "lacunas_documentais": contexto.get("lacunas_documentais", []),
    }


def montar_prompt_engenharia(
    contexto_ia: Mapping[str, Any],
) -> str:
    """Monta o contrato da MAR.IA como intérprete técnico."""

    contexto = compactar_contexto_engenharia(
        contexto_ia
    )

    linhas: list[str] = []

    objetivo_estudo: Any = contexto.get(
        "objetivo_estudo"
    )

    if objetivo_estudo:
        linhas.append("OBJETIVO DO ESTUDO:")
        linhas.append(str(objetivo_estudo))
        linhas.append("")

    linhas.append("VARIÁVEL ALVO:")
    linhas.append(
        str(
            contexto.get(
                "variavel_alvo",
                "não informada",
            )
        )
    )

    cobertura: Any = contexto.get("cobertura_pct")
    registros: Any = contexto.get("registros_validos")

    if cobertura is not None or registros is not None:
        linhas.append("")
        linhas.append("QUALIDADE DA JANELA:")

        if cobertura is not None:
            linhas.append(
                f"Cobertura: {_formatar_numero(cobertura, 1)}%"
            )

        if registros is not None:
            linhas.append(
                f"Registros válidos: {registros}"
            )

    evidencias = _normalizar_lista_dict(
        contexto.get("evidencias", [])
    )

    if evidencias:
        linhas.append("")
        linhas.append(
            "HIPÓTESE PRIORIZADA PELO MOTOR DETERMINÍSTICO:"
        )

        principal = evidencias[0]

        linhas.append(
            f"Variável antecedente: {principal.get('variavel')}"
        )
        linhas.append(
            f"Defasagem: {principal.get('lag')}"
        )

        correlacao_com_lag: Any = principal.get(
            "correlacao_com_lag"
        )
        correlacao_sem_lag: Any = principal.get(
            "correlacao_sem_lag"
        )
        ganho_correlacao: Any = principal.get(
            "ganho_correlacao"
        )
        pares_validos: Any = principal.get(
            "pares_validos"
        )
        score: Any = principal.get(
            "score_evidencia"
        )
        classe: Any = principal.get(
            "classe_evidencia"
        )

        if correlacao_com_lag is not None:
            linhas.append(
                "Correlação com defasagem: "
                + _formatar_numero(correlacao_com_lag)
            )

        if correlacao_sem_lag is not None:
            linhas.append(
                "Correlação sem defasagem: "
                + _formatar_numero(correlacao_sem_lag)
            )

        if ganho_correlacao is not None:
            linhas.append(
                "Ganho absoluto de correlação: "
                + _formatar_numero(ganho_correlacao)
            )

        if pares_validos is not None:
            linhas.append(
                f"Pares válidos: {pares_validos}"
            )

        if score is not None:
            texto_score = (
                f"Score de evidência temporal: {score}/100"
            )

            if classe:
                texto_score += f" — {classe}"

            linhas.append(texto_score)

        if len(evidencias) > 1:
            linhas.append("")
            linhas.append(
                "OUTRAS EVIDÊNCIAS DO MOTOR "
                "(apoio, não substituem a principal):"
            )

            for evidencia in evidencias[1:]:
                resumo = (
                    f"- {evidencia.get('variavel')} | "
                    f"defasagem {evidencia.get('lag')}"
                )

                correlacao_aux: Any = evidencia.get(
                    "correlacao_com_lag"
                )
                pares_aux: Any = evidencia.get(
                    "pares_validos"
                )
                score_aux: Any = evidencia.get(
                    "score_evidencia"
                )

                if correlacao_aux is not None:
                    resumo += (
                        " | correlação "
                        + _formatar_numero(correlacao_aux)
                    )

                if pares_aux is not None:
                    resumo += f" | {pares_aux} pares"

                if score_aux is not None:
                    resumo += f" | score {score_aux}/100"

                linhas.append(resumo)

    documentos = _normalizar_lista_dict(
        contexto.get("documentacao", [])
    )

    if documentos:
        linhas.append("")
        linhas.append(
            "REFERÊNCIAS DOCUMENTAIS RECUPERADAS:"
        )

        for indice, documento in enumerate(
            documentos,
            start=1,
        ):
            origem = str(
                documento.get(
                    "documento",
                    "Documento técnico",
                )
            )
            pagina: Any = documento.get("pagina")

            if pagina is not None:
                origem = f"{origem} | pág. {pagina}"

            linhas.append(
                f"{indice}. [{origem}]"
            )
            linhas.append(
                str(
                    documento.get(
                        "texto",
                        "",
                    )
                )
            )

    caso = "\n".join(linhas)

    if contexto.get("modo_assistido_sem_correlacao"):
        return f"""
Você é MAR.IA, assistente técnica de apoio à engenharia de processo.

Este caso NÃO possui variáveis candidatas suficientes para correlação.
Não invente correlações, defasagens, valores ou causa raiz. Faça uma análise
assistida usando somente: o comportamento descritivo da variável alvo, o
contexto físico confirmado, os trechos documentais fornecidos e conhecimento
geral apresentado explicitamente como possibilidade a verificar.

OBJETIVO: {contexto.get('objetivo_estudo')}
VARIÁVEL ALVO: {contexto.get('variavel_alvo')}
RESUMO DESCRITIVO: {contexto.get('resumo_variavel_alvo')}
CONTEXTO FÍSICO CONHECIDO: {contexto.get('contexto_fisico_conhecido')}
CONSIDERAÇÕES SOBRE OS DADOS: {contexto.get('consideracoes_dados')}
LACUNAS DOCUMENTAIS: {contexto.get('lacunas_documentais')}

REFERÊNCIAS DOCUMENTAIS:
{contexto.get('documentacao')}

Responda somente nestas seções:

### 🔎 Leitura disponível
Explique o que os dados da variável alvo permitem observar e o que não pode
ser concluído sem variáveis de comparação.

### 🏭 Possíveis contextos de processo
Apresente mecanismos possíveis apenas como caminhos de investigação. Use a
topologia conhecida, mas não apresente conhecimento geral como fato da planta.

### 🗂️ Melhorias recomendadas nos dados
Separe problemas de associação, identificação, contexto e qualidade dos dados.

### 📚 Melhorias recomendadas na documentação
Se o manual não tratar o indicador ou seu mecanismo, registre explicitamente
essa lacuna e sugira o conteúdo que deveria ser documentado.

### 🧭 Próximas verificações
Liste verificações objetivas para permitir uma futura análise determinística.
""".strip()

    return f"""
Você é MAR.IA, assistente técnica com perfil de ENGENHEIRO DE PROCESSO
especializado em tratamento biológico de efluentes industriais,
especialmente sistemas de lodos ativados.

CONHECIMENTO DE DOMÍNIO QUE VOCÊ PODE USAR PARA RACIOCINAR:
- DQO, DBO, COT e carga orgânica;
- nitrogênio amoniacal, remoção de NH3 e nitrificação;
- oxigênio dissolvido e demanda de oxigênio;
- aeração e estado/quantidade de aeradores;
- vazão e carga aplicada;
- tempo de detenção hidráulica;
- idade do lodo, sólidos e recirculação;
- pH e temperatura;
- relações entre desempenho do tratamento e consumo energético.

CONTRATO DE CONFIANÇA:
1. O OBJETIVO DO ESTUDO é a pergunta do engenheiro e deve orientar
   toda a resposta.
2. Os valores operacionais e estatísticos vêm do motor determinístico.
   Não recalcule, altere ou invente esses valores.
3. A HIPÓTESE PRINCIPAL já foi priorizada pelo motor. Não crie outra
   hipótese concorrente.
4. Use conhecimento geral apenas para explicar mecanismos plausíveis
   e indicar verificações.
5. Valores específicos da planta devem vir da documentação fornecida.
6. O manual é referência técnica, não medição operacional.
7. Correlação e precedência temporal não comprovam causalidade.
8. Não afirme causa raiz.
9. Não recomende alteração automática de setpoint, controle ou operação.
10. Quando usar informação documental específica, cite documento e página.
11. Seja objetivo e mantenha foco na pergunta do engenheiro.

RESPONDA SOMENTE NESTAS QUATRO SEÇÕES:

### 🔎 Leitura técnica
Comece respondendo diretamente ao OBJETIVO DO ESTUDO.
Mantenha explicitamente a variável antecedente e a variável alvo.

### ⚙️ Interpretação de processo
Explique de 1 a 3 mecanismos fisicamente plausíveis compatíveis com
a hipótese do motor. Apresente-os como possibilidades a verificar.

### 📚 Confronto com a documentação
Use apenas referências pertinentes à hipótese principal. Compare TDH,
vazão, volume, aeração ou recirculação como plausibilidade física.
Não use o manual para provar a correlação.

### 🧭 Próximas verificações
Indique de 2 a 4 verificações objetivas no PI ou na documentação que
possam fortalecer ou enfraquecer a hipótese principal.

CASO:
{caso}
""".strip()


def consultar_ollama(
    contexto_ia: Mapping[str, Any],
    modelo: str,
    url: str = OLLAMA_URL_PADRAO,
    timeout: int = 300,
) -> dict[str, Any]:
    """Envia o contexto estruturado ao Ollama local."""

    prompt = montar_prompt_engenharia(
        contexto_ia
    )

    payload: dict[str, Any] = {
        "model": modelo,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Você é MAR.IA, assistente de investigação de "
                    "engenharia de processo. Interprete as evidências "
                    "do motor sem inventar valores ou causalidade."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "options": {
            "temperature": 0.15,
        },
    }

    dados_envio = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    requisicao = urllib.request.Request(
        url,
        data=dados_envio,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            requisicao,
            timeout=timeout,
        ) as resposta:
            retorno_bruto: Any = json.loads(
                resposta.read().decode("utf-8")
            )

        retorno: dict[str, Any] = (
            retorno_bruto
            if isinstance(retorno_bruto, dict)
            else {}
        )

        mensagem_bruta: Any = retorno.get(
            "message",
            {},
        )

        mensagem: dict[str, Any] = (
            mensagem_bruta
            if isinstance(mensagem_bruta, dict)
            else {}
        )

        texto = str(
            mensagem.get(
                "content",
                "",
            )
        ).strip()

        if not texto:
            return {
                "ok": False,
                "provedor": "OLLAMA",
                "modelo": modelo,
                "resposta": "",
                "erro": (
                    "O Ollama respondeu sem conteúdo textual."
                ),
            }

        return {
            "ok": True,
            "provedor": "OLLAMA",
            "modelo": modelo,
            "resposta": texto,
            "erro": None,
        }

    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode(
            "utf-8",
            errors="replace",
        )

        return {
            "ok": False,
            "provedor": "OLLAMA",
            "modelo": modelo,
            "resposta": "",
            "erro": f"HTTP {erro.code}: {detalhe}",
        }

    except Exception as erro:
        return {
            "ok": False,
            "provedor": "OLLAMA",
            "modelo": modelo,
            "resposta": "",
            "erro": str(erro),
        }


def consultar_ia(
    contexto_ia: Mapping[str, Any],
    provedor: str = "OLLAMA",
    modelo: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Interface única para os provedores de IA."""

    provedor_normalizado = (
        str(provedor)
        .strip()
        .upper()
    )

    if provedor_normalizado == "OLLAMA":
        if not modelo:
            return {
                "ok": False,
                "provedor": "OLLAMA",
                "modelo": None,
                "resposta": "",
                "erro": "Informe um modelo Ollama.",
            }

        return consultar_ollama(
            contexto_ia=contexto_ia,
            modelo=modelo,
        )

    if provedor_normalizado in {"MAR.IA", "MARIA", "COPILOT STUDIO"}:
        if not token:
            return {"ok": False, "provedor": "MAR.IA", "modelo": "Microsoft Copilot Studio", "resposta": "", "erro": "Entre com sua conta Microsoft antes de consultar a MAR.IA."}
        return consultar_maria(contexto_ia=contexto_ia, token=token)

    return {
        "ok": False,
        "provedor": provedor_normalizado,
        "modelo": modelo,
        "resposta": "",
        "erro": (
            f"Provedor '{provedor_normalizado}' ainda não implementado."
        ),
    }


async def _consultar_maria_assincrono(prompt: str, token: str) -> str:
    """Executa uma conversa no cliente oficial e consolida o streaming."""
    from microsoft_agents.copilotstudio.client import ConnectionSettings, CopilotClient

    settings = ConnectionSettings(
        environment_id=os.environ["MARIA_ENVIRONMENT_ID"].strip(),
        agent_identifier=os.environ["MARIA_SCHEMA_NAME"].strip(),
    )
    cliente = CopilotClient(settings, token)
    async for _ in cliente.start_conversation():
        pass
    textos: list[str] = []
    async for atividade in cliente.ask_question(prompt):
        texto = str(atividade.text or "").strip()
        if texto and texto not in textos:
            textos.append(texto)
    if not textos:
        raise RuntimeError("A MAR.IA não retornou conteúdo textual.")
    return max(textos, key=len)


def consultar_maria(contexto_ia: Mapping[str, Any], token: str) -> dict[str, Any]:
    """Envia a evidência determinística à MAR.IA autenticada."""
    try:
        texto = asyncio.run(_consultar_maria_assincrono(montar_prompt_engenharia(contexto_ia), token))
        return {"ok": True, "provedor": "MAR.IA", "modelo": "Microsoft Copilot Studio", "resposta": texto, "erro": None}
    except Exception as erro:
        return {"ok": False, "provedor": "MAR.IA", "modelo": "Microsoft Copilot Studio", "resposta": "", "erro": str(erro)}
