import React, { useEffect, useState } from 'react';
import api from '../services/api';

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
            <div style={{ maxWidth: '800px', margin: '30px auto' }}>
                <h2>Plano de Estudos de Hoje</h2>
                <div
                    style={{
                        background: '#fff3cd',
                        border: '1px solid #ffc107',
                        borderLeft: '5px solid #ffc107',
                        borderRadius: '4px',
                        padding: '16px 20px',
                        color: '#664d03',
                    }}
                >
                    <p style={{ margin: 0, fontWeight: 'bold' }}>Acesso restrito a assinantes</p>
                    <p style={{ margin: '8px 0 16px' }}>{erroAssinatura}</p>
                    <button
                        onClick={onNavegarAssinatura}
                        style={{
                            background: '#ffc107',
                            color: '#664d03',
                            border: 'none',
                            padding: '8px 16px',
                            borderRadius: '4px',
                            fontWeight: 'bold',
                            cursor: 'pointer',
                        }}
                    >
                        Assinar agora
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{ maxWidth: '800px', margin: '30px auto' }}>
            <h2>Plano de Estudos de Hoje</h2>
            <p>Tempo total disponível para hoje: <strong>{minutosDisponiveis} minutos</strong></p>

            {plano.length === 0 ? (
                <p>Nenhuma meta agendada para hoje ou disponibilidade não configurada.</p>
            ) : (
                <table border="1" cellPadding="10" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr>
                            <th>Disciplina</th>
                            <th>Tópico</th>
                            <th>Tipo de Tarefa</th>
                            <th>Tempo Sugerido</th>
                        </tr>
                    </thead>
                    <tbody>
                        {plano.map((item) => (
                            <tr key={item.topico_id}>
                                <td>{item.disciplina_nome}</td>
                                <td>{item.topico_nome}</td>
                                <td><strong>{item.tipo_tarefa}</strong></td>
                                <td>{item.tempo_sugerido_minutos} min</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}
