import React, { useState } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import UploadEdital from './pages/UploadEdital';
import Assinatura from './pages/Assinatura';
import MinhaConta from './pages/MinhaConta';
import Logo from './components/Logo';

export default function App() {
    const [token, setToken] = useState(localStorage.getItem('access_token'));
    const [currentTab, setCurrentTab] = useState('dashboard');

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setToken(null);
        setCurrentTab('dashboard');
    };

    if (!token) {
        return <Login onLoginSuccess={() => setToken(localStorage.getItem('access_token'))} />;
    }

    return (
        <div className="app-shell">
            <header className="app-header">
                <div className="brand">
                    <Logo size={34} />
                    VerticAI
                </div>
                <nav className="app-nav">
                    <button
                        className={`nav__btn ${currentTab === 'dashboard' ? 'nav__btn--active' : ''}`}
                        onClick={() => setCurrentTab('dashboard')}
                    >
                        Dashboard
                    </button>
                    <button
                        className={`nav__btn ${currentTab === 'upload' ? 'nav__btn--active' : ''}`}
                        onClick={() => setCurrentTab('upload')}
                    >
                        Importar Edital
                    </button>
                    <button
                        className={`nav__btn ${currentTab === 'conta' ? 'nav__btn--active' : ''}`}
                        onClick={() => setCurrentTab('conta')}
                    >
                        Minha Conta
                    </button>
                    <button className="btn btn-danger-ghost" onClick={handleLogout} style={{ marginLeft: '12px' }}>
                        Sair
                    </button>
                </nav>
            </header>

            <main>
                {currentTab === 'dashboard' && (
                    <Dashboard onNavegarAssinatura={() => setCurrentTab('assinatura')} />
                )}
                {currentTab === 'upload' && <UploadEdital />}
                {currentTab === 'conta' && <MinhaConta />}
                {currentTab === 'assinatura' && (
                    <Assinatura onVoltar={() => setCurrentTab('dashboard')} />
                )}
            </main>
        </div>
    );
}
