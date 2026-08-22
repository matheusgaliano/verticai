import React from 'react';

export default function Assinatura({ onVoltar }) {
    return (
        <div className="page" style={{ maxWidth: '480px' }}>
            <div className="card" style={{ textAlign: 'center', padding: '40px 32px' }}>
                <span className="kicker">Assinatura</span>
                <h2 style={{ marginBottom: '12px' }}>Em construção</h2>
                <p className="muted" style={{ marginBottom: onVoltar ? '24px' : 0 }}>
                    O checkout ainda está em construção. Em breve você poderá assinar por aqui.
                </p>
                {onVoltar && (
                    <button className="btn btn-ghost" onClick={onVoltar}>
                        Voltar
                    </button>
                )}
            </div>
        </div>
    );
}
