"""
adaptador_ia.py

Camada de abstração para interpretação assistida por IA no ProjetoIA.

Princípios:
- o motor determinístico continua sendo a fonte da verdade;
- a IA recebe somente o contexto estruturado da investigação;
- a IA não recalcula nem altera evidências;
- a IA não deve afirmar causalidade;
- a IA não deve recomendar alteração automática de controle/operação.

Primeiro provedor suportado: Ollama local.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict


OLLAMA_URL_PADRAO = "http://localhost:11434/api/chat"


def verificar_ollama(
    url_base: str = "http://localhost:11434",
    timeout: int = 3,
) -> Dict[str, Any]:
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
            dados = json.loads(
                resposta.read().decode("utf-8")
            )

        modelos = [
            item.get("name")
            for item in dados.get("models", [])
            if item.get("name")
        ]

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


def montar_prompt_engenharia(
    contexto_ia: Dict[str, Any],
) -> str:
    """Monta instruções rígidas para interpretação do estudo."""

    contexto_json = json.dumps(
        contexto_ia,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return f"""
Você é um assistente técnico para investigação de processos industriais.

O bloco CONTEXTO DETERMINÍSTICO abaixo foi produzido por motores de
engenharia e deve ser tratado como fonte da verdade desta análise.

REGRAS OBRIGATÓRIAS:
1. Não altere, recalcule ou invente valores do contexto.
2. Não afirme causa raiz.
3. Não transforme correlação ou precedência temporal em causalidade.
4. Não recomende alteração automática de setpoint, controle ou operação.
5. Diferencie claramente evidência, hipótese e verificação necessária.
6. Se houver poucos pares válidos ou baixa evidência, destaque a limitação.
7. Use linguagem técnica, objetiva e compreensível para um engenheiro.
8. Não invente informação de processo que não esteja no contexto.
9. Mecanismos físicos podem ser apresentados somente como possibilidades
   a verificar, nunca como fatos confirmados.

Produza a resposta exatamente com estas seções:

### Leitura técnica
Explique o que os resultados mostram.

### Hipótese principal
Explique a principal hipótese sem afirmar causalidade.

### Mecanismos a verificar
Liste mecanismos físicos ou operacionais plausíveis que devem ser
verificados pelo engenheiro.

### Próximas verificações
Liste verificações objetivas que aumentariam ou reduziriam a confiança.

### Limitações
Explique por que o resultado ainda não constitui causa confirmada.

CONTEXTO DETERMINÍSTICO:
{contexto_json}
""".strip()


def consultar_ollama(
    contexto_ia: Dict[str, Any],
    modelo: str,
    url: str = OLLAMA_URL_PADRAO,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Envia o contexto estruturado ao Ollama local."""

    prompt = montar_prompt_engenharia(
        contexto_ia
    )

    payload = {
        "model": modelo,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Você auxilia investigação de engenharia industrial. "
                    "Obedeça rigorosamente às restrições fornecidas."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "options": {
            "temperature": 0.2,
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
            retorno = json.loads(
                resposta.read().decode("utf-8")
            )

        texto = (
            retorno.get("message", {})
            .get("content", "")
            .strip()
        )

        if not texto:
            return {
                "ok": False,
                "provedor": "OLLAMA",
                "modelo": modelo,
                "resposta": "",
                "erro": "O Ollama respondeu sem conteúdo textual.",
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
    contexto_ia: Dict[str, Any],
    provedor: str = "OLLAMA",
    modelo: str | None = None,
) -> Dict[str, Any]:
    """
    Interface única para provedores de IA.

    Futuramente esta função poderá rotear para Copilot/API sem
    alterar o motor determinístico do Estudo de Processo.
    """

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

    return {
        "ok": False,
        "provedor": provedor_normalizado,
        "modelo": modelo,
        "resposta": "",
        "erro": (
            f"Provedor '{provedor_normalizado}' ainda não implementado."
        ),
    }
