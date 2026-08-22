import React, { useState } from 'react';
import api from '../services/api';

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
        <div style={{ maxWidth: '400px', margin: '50px auto', padding: '20px', border: '1px solid #ccc' }}>
            <h2>{isRegister ? 'Criar Conta' : 'Login'}</h2>
            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    placeholder="Usuário"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    required
                /><br /><br />
                {isRegister && (
                    <>
                        <input
                            type="email"
                            placeholder="E-mail"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        /><br /><br />
                    </>
                )}
                <input
                    type="password"
                    placeholder="Senha"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                /><br /><br />
                <button type="submit">{isRegister ? 'Cadastrar' : 'Entrar'}</button>
            </form>
            <br />
            <button onClick={() => setIsRegister(!isRegister)}>
                {isRegister ? 'Já tem conta? Entrar' : 'Não tem conta? Cadastre-se'}
            </button>
        </div>
    );
}