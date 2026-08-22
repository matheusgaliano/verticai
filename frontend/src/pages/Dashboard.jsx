import React, { useEffect, useState } from 'react';
import api from '../services/api';

export default function Dashboard() {
    const [plano, setPlano] = useState([]);
    const [minutosDisponiveis, setMinutosDisponiveis] = useState(0);

    useEffect(() => {
        api.get('/estudos/plano-diario/')
            .then((res) => {
                setPlano(res.data.plano || []);
                setMinutosDisponiveis(res.data.minutos_disponiveis || 0);
            })
            .catch(() => alert('Erro ao carregar o plano de hoje.'));
    }, []);

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
                        {plano.map((item, index) => (
                            <tr key={index}>
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