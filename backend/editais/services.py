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
from datetime import date

from django.conf import settings
from django.db import transaction
from pypdf import PdfReader

from .models import Cargo, Concurso, Disciplina, Edital, Topico

logger = logging.getLogger(__name__)

# Tetos defensivos: o texto enviado ao modelo e o volume que aceitamos gravar.
MAX_CARACTERES_PROMPT = 15_000
MAX_CARGOS = 30
MAX_DISCIPLINAS = 60
MAX_TOPICOS_POR_DISCIPLINA = 300
PESO_PADRAO = 1.0
PESO_MINIMO = 0.1
PESO_MAXIMO = 10.0
VAGAS_PADRAO = 1


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
Extraia o conteúdo programático (disciplinas, pesos e tópicos) APENAS para
o cargo indicado abaixo. Editais frequentemente têm conteúdo diferente por
cargo — ignore disciplinas de outros cargos que não sejam o indicado.
Preserve a ordem dos tópicos como aparecem no edital.

Cargo alvo: {cargo_nome}

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

    return texto


def _chamar_gemini(prompt):
    """Chamada de baixo nível ao Gemini, comum às duas fases. Devolve o JSON bruto."""
    if not settings.GEMINI_API_KEY:
        raise IAIndisponivelError('Integração com IA não configurada no servidor.')

    # Import tardio: mantém o app carregável mesmo sem a integração configurada.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json'),
        )
    except Exception as exc:
        logger.exception('Erro na chamada ao Gemini')
        raise IAIndisponivelError('O serviço de IA está indisponível no momento.') from exc

    try:
        return json.loads(response.text)
    except (TypeError, ValueError) as exc:
        logger.error('Gemini devolveu conteúdo não-JSON: %r', getattr(response, 'text', None))
        raise RespostaIAInvalidaError('A IA devolveu uma resposta em formato inesperado.') from exc


def identificar_concurso_e_cargos(texto_edital):
    """Fase 1: identifica o concurso e todos os cargos mencionados no edital."""
    prompt = PROMPT_IDENTIFICACAO.format(texto=texto_edital[:MAX_CARACTERES_PROMPT])
    dados = _chamar_gemini(prompt)
    return _validar_identificacao(dados)


def detalhar_disciplinas_do_cargo(texto_edital, cargo_nome):
    """Fase 2: extrai disciplinas/tópicos/pesos focados em UM cargo já identificado."""
    prompt = PROMPT_DETALHAMENTO.format(
        cargo_nome=cargo_nome,
        texto=texto_edital[:MAX_CARACTERES_PROMPT],
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
