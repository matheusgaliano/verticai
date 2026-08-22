import React, { useState } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import UploadEdital from './pages/UploadEdital';
import Assinatura from './pages/Assinatura';

export default function App() {
    const [token, setToken] = useState(localStorage.getItem('access_token'));
    const [currentTab, setCurrentTab] = useState('dashboard');

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setToken(null);
    };

    if (!token) {
        return <Login onLoginSuccess={() => setToken(localStorage.getItem('access_token'))} />;
    }

    return (
        <div>
            <header style={{ background: '#282c34', padding: '15px', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{ margin: 0, fontSize: '20px' }}>VerticAI - Painel de Estudos</h1>
                <nav>
                    <button
                        onClick={() => setCurrentTab('dashboard')}
                        style={{ marginRight: '10px', fontWeight: currentTab === 'dashboard' ? 'bold' : 'normal' }}
                    >
                        Dashboard
                    </button>
                    <button
                        onClick={() => setCurrentTab('upload')}
                        style={{ marginRight: '10px', fontWeight: currentTab === 'upload' ? 'bold' : 'normal' }}
                    >
                        Importar Edital (PDF)
                    </button>
                    <button onClick={handleLogout} style={{ background: '#dc3545', color: 'white', border: 'none', padding: '5px 10px', cursor: 'pointer' }}>
                        Sair
                    </button>
                </nav>
            </header>

            <main style={{ padding: '20px' }}>
                {currentTab === 'dashboard' && (
                    <Dashboard onNavegarAssinatura={() => setCurrentTab('assinatura')} />
                )}
                {currentTab === 'upload' && <UploadEdital />}
                {currentTab === 'assinatura' && (
                    <Assinatura onVoltar={() => setCurrentTab('dashboard')} />
                )}
            </main>
        </div>
    );
}