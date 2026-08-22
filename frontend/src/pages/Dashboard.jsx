import React, { useEffect, useState } from 'react';
import api from '../services/api';

const TAREFA_META = {
    REVISAO: { label: 'Revisão', pillClass: 'pill--accent' },
    TEORIA: { label: 'Teoria', pillClass: 'pill--muted' },
};

export default function Dashboard({ onNavegarAssinatura }) {
    const [plano, setPlano] = useState([]);
    const [minutosDisponiveis, setMinutosDisponiveis] = useState(0);
    const [erroAssinatura, setErroAssinatura] = useState(null);

    useEffect(() => {
        setErroAssinatura(null);
        api.get('/estudos/plano-diario/')
            .then((res) => {
                setPlano(res.data.plano || []);
                setMinutosDisponiveis(res.data.minutos_disponiveis || 0);
            })
            .catch((err) => {
                if (err.response?.status === 403) {
                    setErroAssinatura(
                        err.response.data?.detail ||
                        'É necessário ter uma assinatura ativa para acessar este recurso.'
                    );
                    return;
                }
                // Erro inesperado (500, falha de rede, etc.) — sem tratamento dedicado ainda.
                alert('Erro ao carregar o plano de hoje.');
            });
    }, []);

    if (erroAssinatura) {
        return (
            <div className="page">
                <div className="page-header">
                    <span className="kicker">Hoje</span>
                    <h2>Plano de Estudos</h2>
                </div>
                <div className="alert alert--warning">
                    <p className="alert__title">Acesso restrito a assinantes</p>
                    <p className="alert__body">{erroAssinatura}</p>
                    <button className="btn btn-accent" onClick={onNavegarAssinatura}>
                        Assinar agora
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="page">
            <div className="page-header">
                <span className="kicker">Hoje</span>
                <h2>Plano de Estudos</h2>
            </div>

            <div className="card">
                <div className="card__head">
                    <p className="card__title">Plano de Estudos de Hoje</p>
                    <div className="plan-stat">
                        {minutosDisponiveis}
                        <small>min disponíveis</small>
                    </div>
                </div>

                {plano.length === 0 ? (
                    <p className="empty-state">
                        Nenhuma meta agendada para hoje ou disponibilidade não configurada.
                    </p>
                ) : (
                    <ul className="plan-list">
                        {plano.map((item) => {
                            const tarefa = TAREFA_META[item.tipo_tarefa] || {
                                label: item.tipo_tarefa,
                                pillClass: 'pill--muted',
                            };
                            return (
                                <li className="plan-row" key={item.topico_id}>
                                    <span className={`pill ${tarefa.pillClass}`}>{tarefa.label}</span>
                                    <span>
                                        <span className="plan-row__topic">{item.topico_nome}</span>
                                        <span className="plan-row__disc">{item.disciplina_nome}</span>
                                    </span>
                                    <span className="plan-row__time">{item.tempo_sugerido_minutos} min</span>
                                </li>
                            );
                        })}
                    </ul>
                )}
            </div>
        </div>
    );
}
