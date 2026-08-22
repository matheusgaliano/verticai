"""Extração de conteúdo programático de editais em PDF via LLM."""

import json
import logging

from django.conf import settings
from django.db import transaction
from pypdf import PdfReader

from .models import Cargo, Disciplina, Topico

logger = logging.getLogger(__name__)

# Tetos defensivos: o texto enviado ao modelo e o volume que aceitamos gravar.
MAX_CARACTERES_PROMPT = 15_000
MAX_DISCIPLINAS = 60
MAX_TOPICOS_POR_DISCIPLINA = 300


class ProcessamentoEditalError(Exception):
    """Falha esperada no processamento de um edital, segura para exibir ao usuário."""


class IAIndisponivelError(ProcessamentoEditalError):
    pass


class PDFInvalidoError(ProcessamentoEditalError):
    pass


class RespostaIAInvalidaError(ProcessamentoEditalError):
    pass


PROMPT_TEMPLATE = """
Analise o texto a seguir extraído de um edital de concurso e estruture o conteúdo
programático das disciplinas e tópicos de estudo, preservando a ordem em que
aparecem no edital.

Retorne ESTRITAMENTE um JSON válido no formato:
{{
  "disciplinas": [
    {{
      "nome": "Nome da Disciplina",
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


def processar_edital_com_ia(texto_edital):
    """Envia o texto ao Gemini e devolve o JSON estruturado já validado."""
    if not settings.GEMINI_API_KEY:
        raise IAIndisponivelError('Integração com IA não configurada no servidor.')

    # Import tardio: mantém o app carregável mesmo sem a integração configurada.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = PROMPT_TEMPLATE.format(texto=texto_edital[:MAX_CARACTERES_PROMPT])

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
        dados = json.loads(response.text)
    except (TypeError, ValueError) as exc:
        logger.error('Gemini devolveu conteúdo não-JSON: %r', getattr(response, 'text', None))
        raise RespostaIAInvalidaError('A IA devolveu uma resposta em formato inesperado.') from exc

    return _validar_estrutura(dados)


def _validar_estrutura(dados):
    """Normaliza e valida o JSON da IA. Nunca confia no formato devolvido."""
    if not isinstance(dados, dict):
        raise RespostaIAInvalidaError('A IA devolveu uma resposta em formato inesperado.')

    disciplinas_brutas = dados.get('disciplinas')
    if not isinstance(disciplinas_brutas, list) or not disciplinas_brutas:
        raise RespostaIAInvalidaError(
            'Não foi possível identificar disciplinas no edital enviado.'
        )

    disciplinas = []
    for item in disciplinas_brutas[:MAX_DISCIPLINAS]:
        if not isinstance(item, dict):
            continue

        nome = (item.get('nome') or '').strip()[:150]
        if not nome:
            continue

        topicos_brutos = item.get('topicos')
        topicos = []
        if isinstance(topicos_brutos, list):
            for topico in topicos_brutos[:MAX_TOPICOS_POR_DISCIPLINA]:
                if not isinstance(topico, str):
                    continue
                topico = topico.strip()[:255]
                if topico:
                    topicos.append(topico)

        disciplinas.append({'nome': nome, 'topicos': topicos})

    if not disciplinas:
        raise RespostaIAInvalidaError(
            'Não foi possível identificar disciplinas no edital enviado.'
        )

    return {'disciplinas': disciplinas}


@transaction.atomic
def salvar_disciplinas_e_topicos(cargo, dados_json):
    """Persiste disciplinas e tópicos do cargo de forma idempotente.

    Reprocessar o mesmo edital atualiza a ordem dos tópicos existentes em vez
    de duplicá-los. Roda em transação: falha no meio não deixa dados parciais.
    """
    if not isinstance(cargo, Cargo):
        cargo = Cargo.objects.get(pk=cargo)

    resumo = []

    for item in dados_json['disciplinas']:
        disciplina, _ = Disciplina.objects.get_or_create(cargo=cargo, nome=item['nome'])

        for ordem, nome_topico in enumerate(item['topicos'], start=1):
            Topico.objects.update_or_create(
                disciplina=disciplina,
                nome=nome_topico,
                defaults={'ordem': ordem},
            )

        resumo.append({'disciplina': disciplina.nome, 'topicos': len(item['topicos'])})

    logger.info(
        'Edital processado para cargo %s: %d disciplinas', cargo.pk, len(resumo)
    )
    return resumo
