"""Extração de conteúdo programático de editais em PDF via LLM.

Fluxo em duas fases:
  1. Identificação — a partir do texto do edital, a IA identifica os dados
     gerais do concurso e TODOS os cargos mencionados (um edital costuma
     descrever vários cargos, cada um com conteúdo programático próprio).
  2. Detalhamento — focada em UM cargo (escolhido pelo usuário dentre os
     identificados na fase 1), a IA extrai disciplinas/tópicos/pesos
     específicos daquele cargo.

Nada é persistido até a confirmação explícita do usuário — ver
`persistir_edital_processado`.
"""

import json
import logging
import time
from datetime import date

from django.conf import settings
from django.db import transaction
from pypdf import PdfReader

from .models import Cargo, Concurso, Disciplina, Edital, Topico

logger = logging.getLogger(__name__)

# Tetos defensivos: o texto enviado ao modelo e o volume que aceitamos gravar.
#
# Limites diferentes por fase, de propósito: os dados gerais do concurso e a
# lista de cargos quase sempre aparecem nas primeiras páginas do edital, mas
# o conteúdo programático detalhado de um cargo específico pode estar num
# anexo dezenas de páginas depois — um edital real de 71 páginas já chegou a
# 219 mil caracteres extraídos, bem além de um teto anterior de 120 mil.
# 500 mil caracteres (~125-150 mil tokens em português) ainda é uma fração
# pequena da janela de contexto de um modelo Flash, então o teto aqui é uma
# margem de segurança generosa, não o limite real do modelo — só entra em
# jogo para editais genuinamente enormes. Documentos menores (a maioria) não
# pagam custo nenhum por esse teto estar alto: só o volume real de texto de
# cada edital é enviado.
MAX_CARACTERES_IDENTIFICACAO = 20_000
MAX_CARACTERES_DETALHAMENTO = 500_000
MAX_CARGOS = 30
MAX_DISCIPLINAS = 60
MAX_TOPICOS_POR_DISCIPLINA = 300
PESO_PADRAO = 1.0
PESO_MINIMO = 0.1
PESO_MAXIMO = 10.0
VAGAS_PADRAO = 1

# Backoff exponencial só para 503/UNAVAILABLE — sobrecarga temporária do
# modelo no lado do Google, não um problema da nossa chave ou da requisição.
# 1 tentativa original + 1 retentativa por valor de espera aqui (3 valores =
# até 3 retentativas, 4 tentativas no total).
GEMINI_BACKOFF_SEGUNDOS = (2, 4, 8)


class ProcessamentoEditalError(Exception):
    """Falha esperada no processamento de um edital, segura para exibir ao usuário."""


class IAIndisponivelError(ProcessamentoEditalError):
    pass


class PDFInvalidoError(ProcessamentoEditalError):
    pass


class RespostaIAInvalidaError(ProcessamentoEditalError):
    pass


PROMPT_IDENTIFICACAO = """
Analise o texto a seguir, extraído de um edital de concurso público.
Identifique os dados gerais do concurso e TODOS os cargos ou funções
mencionados no edital — um edital costuma descrever vários cargos
diferentes, cada um com conteúdo programático próprio. Liste todos, mesmo
que o texto esteja incompleto.

Retorne ESTRITAMENTE um JSON válido no formato:
{{
  "concurso": {{"nome": "Nome do concurso", "orgao": "Sigla ou nome do órgão", "banca": "Nome da banca ou null"}},
  "ano": 2026,
  "data_prova": "AAAA-MM-DD ou null",
  "cargos": [
    {{"nome": "Nome do cargo", "vagas": 10}}
  ]
}}

Texto do Edital:
{texto}
"""

PROMPT_DETALHAMENTO = """
Analise o texto a seguir, extraído de um edital de concurso público.
Extraia o conteúdo programático (disciplinas, pesos e tópicos) referente
ao cargo indicado abaixo.

Cargo alvo: {cargo_nome}

A seção com o conteúdo programático nem sempre é identificada pelo nome
exato do cargo — bancas frequentemente nomeiam a seção pela área de
conhecimento correspondente (ex.: o cargo "Contador" pode estar sob uma
seção chamada "Conhecimentos Específicos de Contabilidade", sem a
palavra "Contador" no cabeçalho; "Fiscal de Tributos" pode aparecer sob
"Conhecimentos Específicos de Legislação Tributária"). Use o contexto do
edital como um todo — a área de atuação do cargo, os requisitos, outras
menções a ele — para localizar a seção correta, não apenas uma
correspondência literal de texto entre o nome do cargo e o título da
seção. Editais frequentemente têm conteúdo diferente por cargo — ignore
disciplinas que claramente pertençam a outro cargo. Preserve a ordem dos
tópicos como aparecem no edital.

Retorne ESTRITAMENTE um JSON válido no formato:
{{
  "disciplinas": [
    {{
      "nome": "Nome da Disciplina",
      "peso": 1.0,
      "topicos": ["Nome do Tópico 1", "Nome do Tópico 2"]
    }}
  ]
}}

Texto do Edital:
{texto}
"""


def extrair_texto_pdf(pdf_file):
    """Extrai o texto de um PDF. Levanta PDFInvalidoError se não houver texto útil."""
    try:
        reader = PdfReader(pdf_file)
        partes = [pagina.extract_text() or '' for pagina in reader.pages]
    except Exception as exc:
        logger.warning('Falha ao ler PDF enviado: %s', exc)
        raise PDFInvalidoError('Não foi possível ler o PDF enviado.') from exc

    texto = '\n'.join(parte for parte in partes if parte.strip())

    if not texto.strip():
        raise PDFInvalidoError(
            'O PDF não contém texto selecionável (possivelmente é digitalizado). '
            'Envie a versão em texto do edital.'
        )

    logger.info(
        'Texto extraído do PDF: %d páginas, %d caracteres. Prévia: %r',
        len(reader.pages), len(texto), texto[:500],
    )
    return texto


def _erro_e_sobrecarga_temporaria(exc, genai_errors):
    """503/UNAVAILABLE: sobrecarga momentânea do modelo no lado do Google.

    Distinto de qualquer erro 4xx (403 permissão, 429 cota, request mal
    formado) — esses são ClientError e nunca entram aqui, porque tentar de
    novo não muda o resultado (ou piora um problema de cota).
    """
    return isinstance(exc, genai_errors.ServerError) and getattr(exc, 'code', None) == 503


def _chamar_gemini(prompt):
    """Chamada de baixo nível ao Gemini, comum às duas fases. Devolve o JSON bruto.

    Reoenta com backoff exponencial (2s, 4s, 8s) só quando o Google devolve
    503/UNAVAILABLE. Qualquer outro erro — chave inválida, sem permissão,
    cota estourada, request malformado — falha direto, sem retry.
    """
    if not settings.GEMINI_API_KEY:
        raise IAIndisponivelError('Integração com IA não configurada no servidor.')

    # Import tardio: mantém o app carregável mesmo sem a integração configurada.
    from google import genai
    from google.genai import errors as genai_errors
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    config = types.GenerateContentConfig(response_mime_type='application/json')
    total_tentativas = len(GEMINI_BACKOFF_SEGUNDOS) + 1

    response = None
    for tentativa in range(1, total_tentativas + 1):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            break
        except Exception as exc:
            sobrecarregado = _erro_e_sobrecarga_temporaria(exc, genai_errors)
            ultima_tentativa = tentativa == total_tentativas

            if not sobrecarregado or ultima_tentativa:
                logger.exception(
                    'Erro na chamada ao Gemini (tentativa %d/%d)', tentativa, total_tentativas,
                )
                if sobrecarregado:
                    raise IAIndisponivelError(
                        'O serviço de IA está temporariamente sobrecarregado. '
                        'Tente novamente em alguns minutos.'
                    ) from exc
                raise IAIndisponivelError('O serviço de IA está indisponível no momento.') from exc

            espera = GEMINI_BACKOFF_SEGUNDOS[tentativa - 1]
            logger.warning(
                'Gemini sobrecarregado (503/UNAVAILABLE) — tentativa %d/%d, nova tentativa em %ds',
                tentativa, total_tentativas, espera,
            )
            time.sleep(espera)

    logger.info('Resposta bruta do Gemini: %r', response.text)

    try:
        return json.loads(response.text)
    except (TypeError, ValueError) as exc:
        logger.error('Gemini devolveu conteúdo não-JSON: %r', getattr(response, 'text', None))
        raise RespostaIAInvalidaError('A IA devolveu uma resposta em formato inesperado.') from exc


def identificar_concurso_e_cargos(texto_edital):
    """Fase 1: identifica o concurso e todos os cargos mencionados no edital."""
    prompt = PROMPT_IDENTIFICACAO.format(texto=texto_edital[:MAX_CARACTERES_IDENTIFICACAO])
    dados = _chamar_gemini(prompt)
    return _validar_identificacao(dados)


def detalhar_disciplinas_do_cargo(texto_edital, cargo_nome):
    """Fase 2: extrai disciplinas/tópicos/pesos focados em UM cargo já identificado."""
    logger.info('Detalhando cargo — nome usado na busca: %r', cargo_nome)
    prompt = PROMPT_DETALHAMENTO.format(
        cargo_nome=cargo_nome,
        texto=texto_edital[:MAX_CARACTERES_DETALHAMENTO],
    )
    dados = _chamar_gemini(prompt)
    return _validar_detalhamento(dados)


def _texto_limpo(valor, tamanho_max):
    if not isinstance(valor, str):
        return ''
    return valor.strip()[:tamanho_max]


def _inteiro_positivo(valor, padrao):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return padrao
    return numero if numero > 0 else padrao


def _validar_identificacao(dados):
    """Normaliza e valida o JSON da fase 1. Nunca confia no formato devolvido."""
    if not isinstance(dados, dict):
        raise RespostaIAInvalidaError('A IA devolveu uma resposta em formato inesperado.')

    concurso_bruto = dados.get('concurso') or {}
    nome_concurso = _texto_limpo(concurso_bruto.get('nome'), 200)
    orgao = _texto_limpo(concurso_bruto.get('orgao'), 100)
    banca = _texto_limpo(concurso_bruto.get('banca'), 100) or None

    if not nome_concurso or not orgao:
        raise RespostaIAInvalidaError(
            'Não foi possível identificar o concurso e o órgão neste edital.'
        )

    ano = _inteiro_positivo(dados.get('ano'), None)

    data_prova = None
    data_prova_bruta = _texto_limpo(dados.get('data_prova'), 10)
    if data_prova_bruta:
        try:
            data_prova = date.fromisoformat(data_prova_bruta)
        except ValueError:
            data_prova = None

    cargos_brutos = dados.get('cargos')
    cargos = []
    if isinstance(cargos_brutos, list):
        for item in cargos_brutos[:MAX_CARGOS]:
            if not isinstance(item, dict):
                continue
            nome_cargo = _texto_limpo(item.get('nome'), 150)
            if not nome_cargo:
                continue
            cargos.append({
                'nome': nome_cargo,
                'vagas': _inteiro_positivo(item.get('vagas'), VAGAS_PADRAO),
            })

    if not cargos:
        raise RespostaIAInvalidaError(
            'Não foi possível identificar nenhum cargo neste edital.'
        )

    return {
        'concurso': {'nome': nome_concurso, 'orgao': orgao, 'banca': banca},
        'ano': ano,
        'data_prova': data_prova,
        'cargos': cargos,
    }


def _validar_detalhamento(dados):
    """Normaliza e valida o JSON da fase 2. Nunca confia no formato devolvido."""
    if not isinstance(dados, dict):
        raise RespostaIAInvalidaError('A IA devolveu uma resposta em formato inesperado.')

    disciplinas_brutas = dados.get('disciplinas')
    if not isinstance(disciplinas_brutas, list) or not disciplinas_brutas:
        raise RespostaIAInvalidaError(
            'Não foi possível identificar disciplinas para o cargo escolhido.'
        )

    disciplinas = []
    for item in disciplinas_brutas[:MAX_DISCIPLINAS]:
        if not isinstance(item, dict):
            continue

        nome = _texto_limpo(item.get('nome'), 150)
        if not nome:
            continue

        try:
            peso = round(float(item.get('peso', PESO_PADRAO)), 2)
        except (TypeError, ValueError):
            peso = PESO_PADRAO
        peso = min(max(peso, PESO_MINIMO), PESO_MAXIMO)

        topicos_brutos = item.get('topicos')
        topicos = []
        if isinstance(topicos_brutos, list):
            for topico in topicos_brutos[:MAX_TOPICOS_POR_DISCIPLINA]:
                topico_limpo = _texto_limpo(topico, 255)
                if topico_limpo:
                    topicos.append(topico_limpo)

        disciplinas.append({'nome': nome, 'peso': peso, 'topicos': topicos})

    if not disciplinas:
        raise RespostaIAInvalidaError(
            'Não foi possível identificar disciplinas para o cargo escolhido.'
        )

    return {'disciplinas': disciplinas}


@transaction.atomic
def persistir_edital_processado(concurso_dados, ano, data_prova, cargo_nome, vagas,
                                 disciplinas, pdf_file=None):
    """Grava de fato Concurso/Edital/Cargo/Disciplina/Tópico.

    Idempotente: reprocessar o mesmo edital/cargo reaproveita os registros
    existentes (por nome) e atualiza disciplinas/tópicos em vez de duplicar.
    """
    concurso, _ = Concurso.objects.get_or_create(
        orgao=concurso_dados['orgao'],
        nome=concurso_dados['nome'],
        defaults={'banca': concurso_dados.get('banca')},
    )

    edital, _ = Edital.objects.get_or_create(
        concurso=concurso,
        ano=ano,
        defaults={'data_prova': data_prova},
    )

    if pdf_file is not None and not edital.arquivo_pdf:
        pdf_file.seek(0)
        edital.arquivo_pdf.save(pdf_file.name, pdf_file, save=True)

    cargo, _ = Cargo.objects.update_or_create(
        edital=edital,
        nome=cargo_nome,
        defaults={'vagas': vagas or VAGAS_PADRAO},
    )

    resumo = []
    for item in disciplinas:
        disciplina, _ = Disciplina.objects.update_or_create(
            cargo=cargo,
            nome=item['nome'],
            defaults={'peso': item.get('peso', PESO_PADRAO)},
        )

        for ordem, nome_topico in enumerate(item['topicos'], start=1):
            Topico.objects.update_or_create(
                disciplina=disciplina,
                nome=nome_topico,
                defaults={'ordem': ordem},
            )

        resumo.append({'disciplina': disciplina.nome, 'topicos': len(item['topicos'])})

    logger.info(
        'Edital confirmado: cargo=%s (%d disciplinas)', cargo.pk, len(resumo)
    )
    return {'cargo': cargo, 'disciplinas': resumo}
