"""Regras de negócio de estudo: montagem do plano diário e registro de sessões."""

import logging

from django.db import transaction
from django.utils import timezone

from editais.models import Topico
from usuarios.models import Preparacao

from .models import ProgressoTopico, SessaoDeEstudo

logger = logging.getLogger(__name__)

BLOCO_PADRAO_MINUTOS = 50

PRIORIDADE_REVISAO = 1.0
PRIORIDADE_TEORIA = 0.5

MAPA_DIAS = {0: 'SEG', 1: 'TER', 2: 'QUA', 3: 'QUI', 4: 'SEX', 5: 'SAB', 6: 'DOM'}


class PreparacaoNaoConfiguradaError(Exception):
    """O usuário ainda não tem rotina suficiente para gerar um plano."""


def _item(topico, tipo_tarefa, prioridade):
    return {
        'topico_id': topico.id,
        'topico_nome': topico.nome,
        'disciplina_nome': topico.disciplina.nome,
        'tipo_tarefa': tipo_tarefa,
        'prioridade': prioridade,
        'tempo_sugerido_minutos': BLOCO_PADRAO_MINUTOS,
    }


def montar_plano_diario(usuario, hoje=None):
    """Monta o plano de estudos do dia respeitando a disponibilidade do usuário.

    Prioriza revisões vencidas; o tempo restante é preenchido com teoria nova.
    """
    hoje = hoje or timezone.localdate()

    preparacao = (
        Preparacao.objects
        .select_related('cargo__edital')
        .filter(usuario=usuario)
        .first()
    )
    if preparacao is None or preparacao.cargo is None:
        raise PreparacaoNaoConfiguradaError(
            'Configure sua rotina de estudos e selecione um cargo antes de gerar o plano.'
        )

    disponibilidade = preparacao.disponibilidades.filter(
        dia_semana=MAPA_DIAS[hoje.weekday()]
    ).first()
    minutos_disponiveis = int((disponibilidade.horas_disponiveis if disponibilidade else 0) * 60)

    # Quantos blocos cabem no dia. Define o LIMIT das consultas abaixo, em vez
    # de carregar todos os tópicos do cargo para descartar quase tudo no loop.
    max_blocos = minutos_disponiveis // BLOCO_PADRAO_MINUTOS

    if max_blocos == 0:
        return {
            'data': hoje,
            'minutos_disponiveis': minutos_disponiveis,
            'minutos_alocados': 0,
            'plano': [],
        }

    topicos_do_cargo = (
        Topico.objects
        .filter(disciplina__cargo=preparacao.cargo)
        .select_related('disciplina')
    )

    revisoes = topicos_do_cargo.filter(
        progressos__usuario=usuario,
        progressos__data_proxima_revisao__lte=hoje,
    ).order_by('progressos__data_proxima_revisao')[:max_blocos]

    plano = [_item(topico, 'REVISAO', PRIORIDADE_REVISAO) for topico in revisoes]

    blocos_restantes = max_blocos - len(plano)
    if blocos_restantes > 0:
        ja_no_plano = {item['topico_id'] for item in plano}

        novos = (
            topicos_do_cargo
            .exclude(id__in=ja_no_plano)
            .exclude(
                progressos__usuario=usuario,
                progressos__status=ProgressoTopico.Status.CONCLUIDO,
            )
            # Tópico com revisão marcada para o futuro não é "novo": já está em ciclo.
            .exclude(
                progressos__usuario=usuario,
                progressos__data_proxima_revisao__gt=hoje,
            )
            .order_by('disciplina__nome', 'ordem')[:blocos_restantes]
        )

        plano.extend(_item(topico, 'TEORIA', PRIORIDADE_TEORIA) for topico in novos)

    return {
        'data': hoje,
        'minutos_disponiveis': minutos_disponiveis,
        'minutos_alocados': len(plano) * BLOCO_PADRAO_MINUTOS,
        'plano': plano,
    }


@transaction.atomic
def registrar_sessao(usuario, topico, tempo_minutos, questoes_feitas=0,
                     questoes_acertadas=0, nivel_dominio=None, hoje=None):
    """Grava a sessão de estudo e reagenda a revisão do tópico na mesma transação."""
    hoje = hoje or timezone.localdate()

    sessao = SessaoDeEstudo.objects.create(
        usuario=usuario,
        topico=topico,
        tempo_minutos=tempo_minutos,
        questoes_feitas=questoes_feitas,
        questoes_acertadas=questoes_acertadas,
    )

    progresso, _ = ProgressoTopico.objects.get_or_create(usuario=usuario, topico=topico)

    if nivel_dominio is not None:
        data_prova = _data_prova_do_usuario(usuario)
        progresso.agendar_revisao(nivel_dominio, hoje=hoje, data_prova=data_prova)
        progresso.save()
    elif progresso.status == ProgressoTopico.Status.NAO_INICIADO:
        # Sessão sem autoavaliação apenas tira o tópico do estado inicial.
        progresso.status = ProgressoTopico.Status.TEORIA
        progresso.save(update_fields=['status', 'atualizado_em'])

    logger.info('Sessão registrada: usuário=%s tópico=%s', usuario.pk, topico.pk)
    return sessao


def _data_prova_do_usuario(usuario):
    preparacao = (
        Preparacao.objects
        .select_related('cargo__edital')
        .filter(usuario=usuario)
        .first()
    )
    if preparacao and preparacao.cargo:
        return preparacao.cargo.edital.data_prova
    return None
