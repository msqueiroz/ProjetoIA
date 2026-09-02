"""
Gerenciador da Base de Conhecimento do ProjetoIA / MAR.IA.

Responsabilidades:
- Receber documentos técnicos.
- Extrair conteúdo textual.
- Dividir documentos em trechos pesquisáveis.
- Manter metadados e rastreabilidade.
- Preparar a base para futura busca contextual / RAG.

IMPORTANTE:
Este módulo não interpreta o processo.
Ele organiza o conhecimento documental.
"""

from pathlib import Path
from datetime import datetime
import hashlib
import json
import re
from pypdf import PdfReader


PASTA_BASE_CONHECIMENTO = Path("base_conhecimento")
ARQUIVO_INDICE = PASTA_BASE_CONHECIMENTO / "indice_documentos.json"


def inicializar_base_conhecimento():
    """
    Cria a estrutura mínima da base local de conhecimento.
    """

    PASTA_BASE_CONHECIMENTO.mkdir(parents=True, exist_ok=True)

    if not ARQUIVO_INDICE.exists():
        ARQUIVO_INDICE.write_text(
            json.dumps(
                {
                    "versao_base": 1,
                    "documentos": []
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def calcular_hash_arquivo(caminho_arquivo):
    """
    Calcula SHA-256 do documento.

    Isso permitirá identificar se exatamente o mesmo arquivo
    já foi processado anteriormente.
    """

    sha256 = hashlib.sha256()

    with open(caminho_arquivo, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            sha256.update(bloco)

    return sha256.hexdigest()


def limpar_texto(texto):
    """
    Faz apenas uma limpeza conservadora do texto extraído.

    Não altera valores, unidades ou conteúdo técnico.
    """

    if not texto:
        return ""

    texto = texto.replace("\x00", "")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()


def dividir_texto_em_trechos(
    texto,
    tamanho_maximo=1800,
    sobreposicao=250,
):
    """
    Divide um documento em blocos menores.

    A sobreposição ajuda a preservar contexto entre
    dois trechos consecutivos.
    """

    texto = limpar_texto(texto)

    if not texto:
        return []

    paragrafos = [
        p.strip()
        for p in texto.split("\n")
        if p.strip()
    ]

    trechos = []
    trecho_atual = ""

    for paragrafo in paragrafos:

        candidato = (
            f"{trecho_atual}\n{paragrafo}".strip()
            if trecho_atual
            else paragrafo
        )

        if len(candidato) <= tamanho_maximo:
            trecho_atual = candidato
            continue

        if trecho_atual:
            trechos.append(trecho_atual)

        if sobreposicao > 0 and trecho_atual:
            contexto = trecho_atual[-sobreposicao:]
            trecho_atual = f"{contexto}\n{paragrafo}".strip()
        else:
            trecho_atual = paragrafo

    if trecho_atual:
        trechos.append(trecho_atual)

    return [
        {
            "id_trecho": indice,
            "texto": trecho,
            "tamanho_caracteres": len(trecho),
        }
        for indice, trecho in enumerate(trechos, start=1)
    ]


def carregar_indice_documentos():
    """
    Retorna o índice atual da base.
    """

    inicializar_base_conhecimento()

    return json.loads(
        ARQUIVO_INDICE.read_text(encoding="utf-8")
    )


def salvar_indice_documentos(indice):
    """
    Salva o índice da base de conhecimento.
    """

    inicializar_base_conhecimento()

    ARQUIVO_INDICE.write_text(
        json.dumps(
            indice,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def documento_ja_processado(hash_documento):
    """
    Verifica se exatamente o mesmo documento
    já existe na base.
    """

    indice = carregar_indice_documentos()

    for documento in indice["documentos"]:
        if documento.get("hash_sha256") == hash_documento:
            return True, documento

    return False, None


def criar_metadados_documento(
    caminho_arquivo,
    titulo=None,
    codigo_documento=None,
    revisao=None,
):
    """
    Cria os metadados básicos do documento.

    Posteriormente poderemos tentar extrair automaticamente
    código, revisão, data e outras informações do próprio PDF.
    """

    caminho = Path(caminho_arquivo)

    return {
        "nome_arquivo": caminho.name,
        "titulo": titulo or caminho.stem,
        "codigo_documento": codigo_documento,
        "revisao": revisao,
        "hash_sha256": calcular_hash_arquivo(caminho),
        "data_processamento": datetime.now().isoformat(
            timespec="seconds"
        ),
    }

def criar_documento_conhecimento(
    nome,
    tipo,
    origem="LOCAL",
    caminho=None,
    codigo_documento=None,
    revisao=None,
    titulo=None,
    metadados_adicionais=None,
):
    """
    Cria uma representação genérica de um documento de conhecimento.

    A origem poderá futuramente ser:
    - LOCAL
    - SHAREPOINT
    - GOOGLE_DRIVE
    - OUTRA_FONTE

    O tipo poderá ser:
    - PDF
    - DOCX
    - XLSX
    - TXT
    - etc.
    """

    documento = {
        "nome": nome,
        "titulo": titulo or nome,
        "tipo": tipo.upper(),
        "origem": origem.upper(),
        "caminho": caminho,
        "codigo_documento": codigo_documento,
        "revisao": revisao,
        "metadados": metadados_adicionais or {},
    }

    return documento

def extrair_texto_pdf(caminho_pdf):
    """
    Extrai o conteúdo textual de um PDF página por página.

    Retorna uma lista contendo:
    - número da página
    - texto extraído
    - quantidade de caracteres

    A página é preservada para garantir rastreabilidade
    documental nas futuras respostas da MAR.IA.
    """

    caminho = Path(caminho_pdf)

    if not caminho.exists():
        raise FileNotFoundError(
            f"Documento não encontrado: {caminho}"
        )

    if caminho.suffix.lower() != ".pdf":
        raise ValueError(
            f"O arquivo informado não é PDF: {caminho.name}"
        )

    leitor = PdfReader(str(caminho))

    paginas = []

    for numero_pagina, pagina in enumerate(
        leitor.pages,
        start=1,
    ):
        try:
            texto = pagina.extract_text() or ""
            texto = limpar_texto(texto)

            paginas.append(
                {
                    "pagina": numero_pagina,
                    "texto": texto,
                    "tamanho_caracteres": len(texto),
                }
            )

        except Exception as erro:
            paginas.append(
                {
                    "pagina": numero_pagina,
                    "texto": "",
                    "tamanho_caracteres": 0,
                    "erro": str(erro),
                }
            )

    return paginas


def criar_trechos_pdf(
    caminho_pdf,
    tamanho_maximo=1800,
    sobreposicao=250,
):
    """
    Extrai o PDF e transforma seu conteúdo em trechos pesquisáveis.

    Cada trecho mantém a página de origem.
    """

    paginas = extrair_texto_pdf(caminho_pdf)

    trechos_documento = []
    id_global = 1

    for pagina in paginas:

        texto = pagina.get("texto", "")

        if not texto:
            continue

        trechos_pagina = dividir_texto_em_trechos(
            texto,
            tamanho_maximo=tamanho_maximo,
            sobreposicao=sobreposicao,
        )

        for trecho in trechos_pagina:

            trechos_documento.append(
                {
                    "id_trecho": id_global,
                    "pagina": pagina["pagina"],
                    "texto": trecho["texto"],
                    "tamanho_caracteres": trecho[
                        "tamanho_caracteres"
                    ],
                }
            )

            id_global += 1

    return trechos_documento


def obter_resumo_extracao_pdf(caminho_pdf):
    """
    Executa uma leitura inicial do PDF e retorna
    informações úteis para diagnóstico da extração.
    """

    paginas = extrair_texto_pdf(caminho_pdf)

    paginas_com_texto = [
        pagina
        for pagina in paginas
        if pagina["texto"]
    ]

    paginas_sem_texto = [
        pagina
        for pagina in paginas
        if not pagina["texto"]
    ]

    total_caracteres = sum(
        pagina["tamanho_caracteres"]
        for pagina in paginas
    )

    return {
        "arquivo": Path(caminho_pdf).name,
        "total_paginas": len(paginas),
        "paginas_com_texto": len(paginas_com_texto),
        "paginas_sem_texto": len(paginas_sem_texto),
        "total_caracteres_extraidos": total_caracteres,
    }

def normalizar_termo_busca(texto):
    """
    Normaliza texto para comparação simples.

    Mantém a busca independente de maiúsculas/minúsculas
    e reduz diferenças básicas de acentuação.
    """

    import unicodedata

    texto = texto.lower()

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    texto = re.sub(r"[^a-z0-9\s\-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def buscar_trechos(
    trechos,
    consulta,
    limite=5,
):
    """
    Faz busca textual simples nos trechos de conhecimento.

    A pontuação considera:
    - ocorrência dos termos da consulta;
    - presença da expressão completa;
    - quantidade de termos diferentes encontrados.

    Esta busca é propositalmente simples e auditável
    para o POC.
    """

    consulta_normalizada = normalizar_termo_busca(consulta)

    termos = [
        termo
        for termo in consulta_normalizada.split()
        if len(termo) >= 2
    ]

    resultados = []

    for trecho in trechos:

        texto_original = trecho.get("texto", "")
        texto_normalizado = normalizar_termo_busca(texto_original)

        if not texto_normalizado:
            continue

        pontuacao = 0
        termos_encontrados = []

        # Expressão completa recebe peso maior.
        if (
            consulta_normalizada
            and consulta_normalizada in texto_normalizado
        ):
            pontuacao += 10

        for termo in termos:

            quantidade = texto_normalizado.count(termo)

            if quantidade > 0:
                termos_encontrados.append(termo)

                # Limita repetição excessiva de uma mesma palavra.
                pontuacao += min(quantidade, 5) * 2

        # Bonificação quando vários termos diferentes
        # aparecem no mesmo trecho.
        pontuacao += len(set(termos_encontrados)) * 3

        if pontuacao > 0:
            resultado = dict(trecho)

            resultado["pontuacao_busca"] = pontuacao
            resultado["termos_encontrados"] = sorted(
                set(termos_encontrados)
            )

            resultados.append(resultado)

    resultados.sort(
        key=lambda item: item["pontuacao_busca"],
        reverse=True,
    )

    return resultados[:limite]