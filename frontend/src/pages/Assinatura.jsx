import React from 'react';

export default function Assinatura({ onVoltar }) {
    return (
        <div style={{ maxWidth: '500px', margin: '60px auto', textAlign: 'center' }}>
            <h2>Assinatura</h2>
            <p>O checkout ainda está em construção. Em breve você poderá assinar por aqui.</p>
            {onVoltar && (
                <button onClick={onVoltar} style={{ marginTop: '16px' }}>
                    Voltar
                </button>
            )}
        </div>
    );
}
