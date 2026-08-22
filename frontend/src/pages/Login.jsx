import React, { useState } from 'react';
import api from '../services/api';
import Logo from '../components/Logo';

export default function Login({ onLoginSuccess }) {
    const [isRegister, setIsRegister] = useState(false);
    const [formData, setFormData] = useState({ username: '', email: '', password: '' });

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (isRegister) {
                await api.post('/usuarios/register/', formData);
                alert('Usuário cadastrado com sucesso! Faça login.');
                setIsRegister(false);
            } else {
                const response = await api.post('/usuarios/login/', {
                    username: formData.username,
                    password: formData.password,
                });
                localStorage.setItem('access_token', response.data.access);
                localStorage.setItem('refresh_token', response.data.refresh);
                if (onLoginSuccess) onLoginSuccess();
            }
        } catch (err) {
            alert('Erro na operação. Verifique os dados fornecidos.');
        }
    };

    return (
        <div className="auth-shell">
            <div className="auth-card">
                <div className="auth-brand">
                    <div className="brand">
                        <Logo size={42} />
                        VerticAI
                    </div>
                    <p className="auth-tagline">Sua trilha até a aprovação</p>
                </div>

                <div className="card">
                    <div className="card__body">
                        <h2 style={{ fontSize: '18px', marginBottom: '20px' }}>
                            {isRegister ? 'Criar conta' : 'Entrar'}
                        </h2>
                        <form onSubmit={handleSubmit}>
                            <div className="field">
                                <label htmlFor="username">Usuário</label>
                                <input
                                    id="username"
                                    className="input"
                                    type="text"
                                    placeholder="Seu usuário"
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                    required
                                />
                            </div>

                            {isRegister && (
                                <div className="field">
                                    <label htmlFor="email">E-mail</label>
                                    <input
                                        id="email"
                                        className="input"
                                        type="email"
                                        placeholder="voce@exemplo.com"
                                        value={formData.email}
                                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    />
                                </div>
                            )}

                            <div className="field">
                                <label htmlFor="password">Senha</label>
                                <input
                                    id="password"
                                    className="input"
                                    type="password"
                                    placeholder="••••••••"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    required
                                />
                            </div>

                            <button type="submit" className="btn btn-accent btn-block">
                                {isRegister ? 'Cadastrar' : 'Entrar'}
                            </button>
                        </form>
                    </div>
                </div>

                <div className="auth-toggle">
                    {isRegister ? 'Já tem conta?' : 'Não tem conta?'}{' '}
                    <button className="btn-link" onClick={() => setIsRegister(!isRegister)}>
                        {isRegister ? 'Entrar' : 'Cadastre-se'}
                    </button>
                </div>
            </div>
        </div>
    );
}
