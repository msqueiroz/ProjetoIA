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
    """
    Monta o prompt técnico da investigação.

    A IA deve interpretar conjuntamente:
    - evidências determinísticas;
    - hipóteses calculadas;
    - conhecimento documental recuperado.

    O documento complementa a análise, mas não substitui os dados do PI
    nem transforma uma hipótese em causa confirmada.
    """

    contexto_json = json.dumps(
        contexto_ia,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return f"""
Você é MAR.IA, uma assistente técnica para investigação de processos
industriais.

Sua função NÃO é resumir o JSON recebido.
Sua função é produzir uma interpretação técnica de engenharia a partir
das evidências determinísticas e das referências documentais disponíveis.

O bloco CONTEXTO DETERMINÍSTICO foi produzido por motores de engenharia
do ProjetoIA e deve ser tratado como fonte da verdade numérica desta análise.

O contexto pode conter uma seção chamada "conhecimento_documental".
Quando ela existir, os campos "texto", "pagina", "documento",
"pontuacao_busca" e "termos_encontrados" representam trechos recuperados
de documentação técnica.

USE O CONHECIMENTO DOCUMENTAL DESTA FORMA:
- leia o conteúdo textual dos trechos;
- identifique informações de processo realmente relevantes para a hipótese;
- confronte essas informações com as evidências calculadas;
- cite o documento e a página quando usar uma referência;
- diferencie claramente valor calculado pelo motor de valor informado
  pelo documento;
- considere que documentos podem estar desatualizados, ser cópias não
  controladas ou ter aplicabilidade limitada;
- não trate uma referência documental como prova de causalidade.

NÃO faça uma resposta administrativa do tipo:
- "foram encontrados 3 documentos";
- "foram encontrados os termos...";
- "há 5 trechos relacionados...";
- "o JSON contém...".

Essas informações de estrutura podem ser ignoradas.
O foco deve ser a interpretação física e operacional do processo.

REGRAS OBRIGATÓRIAS:
1. Não altere, recalcule ou invente valores do contexto.
2. Não afirme causa raiz.
3. Não transforme correlação ou precedência temporal em causalidade.
4. Não recomende alteração automática de setpoint, controle ou operação.
5. Diferencie claramente:
   - evidência calculada;
   - referência documental;
   - hipótese;
   - verificação necessária.
6. Se houver poucos pares válidos ou baixa evidência, destaque a limitação.
7. Use linguagem técnica, objetiva e compreensível para um engenheiro.
8. Não invente informação de processo que não esteja no contexto.
9. Mecanismos físicos podem ser apresentados somente como possibilidades
   a verificar, nunca como fatos confirmados.
10. Quando houver tempo de detenção, vazão, volume, recirculação,
    oxigênio dissolvido, carga, aeradores ou outros parâmetros documentados,
    use-os para avaliar a plausibilidade física da hipótese.
11. Não diga que uma defasagem observada é "compatível" apenas porque ela
    é menor ou maior que um tempo de detenção documentado. Explique que
    essa comparação é apenas uma referência inicial e depende da posição
    dos instrumentos, dinâmica hidráulica, mistura, recirculação e caminho
    real entre os pontos.
12. Se o documento trouxer um valor operacional ou de projeto, apresente-o
    explicitamente como "referência documental", nunca como valor medido
    no período analisado.
13. Quando possível, transforme o resultado em um roteiro de investigação
    objetiva no PI, sem recomendar mudanças automáticas de operação.

Produza a resposta exatamente com estas seções:

### Leitura técnica
Explique o que as evidências calculadas mostram.
Use os valores do contexto e destaque força da evidência, quantidade de
pares e direção temporal quando disponíveis.

### Confronto com a documentação
Use somente referências documentais relevantes para a hipótese principal.
Informe documento e página.
Compare cuidadosamente a evidência temporal com referências físicas do
processo, como tempo de detenção, vazão, volume, aeração ou recirculação.
Se não houver referência documental útil, diga isso claramente.

### Hipótese principal
Formule a principal hipótese de engenharia sem afirmar causalidade.
Explique por que ela merece investigação.

### Mecanismos a verificar
Apresente mecanismos físicos ou operacionais plausíveis que possam explicar
a relação observada, mas somente quando houver suporte no contexto ou
na documentação.

### Próximas verificações
Liste verificações objetivas no PI ou na documentação que aumentariam
ou reduziriam a confiança.
Priorize variáveis e verificações diretamente relacionadas ao caso.

### Limitações
Explique por que a análise ainda não constitui causa confirmada.
Inclua limitações estatísticas, temporais, documentais e de processo
quando aplicáveis.

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
                    "Você é MAR.IA, assistente de investigação de "
                    "engenharia industrial. Interprete evidências "
                    "determinísticas e referências documentais sem "
                    "inventar valores, sem afirmar causalidade e sem "
                    "recomendar alterações automáticas de operação."
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
