import React, { useEffect, useState } from 'react';
import api from '../services/api';

function mensagemDeErro(err, generica) {
    const detalhe = err.response?.data;
    if (typeof detalhe?.detail === 'string') return detalhe.detail;
    if (detalhe && typeof detalhe === 'object') {
        const primeiroCampo = Object.values(detalhe)[0];
        if (Array.isArray(primeiroCampo)) return primeiroCampo[0];
        if (typeof primeiroCampo === 'string') return primeiroCampo;
    }
    return generica;
}

function IniciaisAvatar({ nome }) {
    const iniciais = (nome || '?').trim().slice(0, 2).toUpperCase();
    return <div className="avatar avatar--placeholder">{iniciais}</div>;
}

export default function MinhaConta() {
    const [carregando, setCarregando] = useState(true);
    const [dados, setDados] = useState({ username: '', email: '', telefone: '', foto_perfil: null });
    const [novaFoto, setNovaFoto] = useState(null);
    const [previewFoto, setPreviewFoto] = useState(null);
    const [salvando, setSalvando] = useState(false);
    const [erroPerfil, setErroPerfil] = useState(null);

    const [senhaAtual, setSenhaAtual] = useState('');
    const [novaSenha, setNovaSenha] = useState('');
    const [confirmarNovaSenha, setConfirmarNovaSenha] = useState('');
    const [trocandoSenha, setTrocandoSenha] = useState(false);
    const [erroSenha, setErroSenha] = useState(null);

    useEffect(() => {
        api.get('/usuarios/minha-conta/')
            .then((res) => setDados(res.data))
            .catch(() => alert('Erro ao carregar os dados da conta.'))
            .finally(() => setCarregando(false));
    }, []);

    useEffect(() => {
        if (!novaFoto) return undefined;
        const url = URL.createObjectURL(novaFoto);
        setPreviewFoto(url);
        return () => URL.revokeObjectURL(url);
    }, [novaFoto]);

    const handleSalvarPerfil = async (e) => {
        e.preventDefault();
        setErroPerfil(null);
        setSalvando(true);

        const formData = new FormData();
        formData.append('username', dados.username);
        formData.append('email', dados.email || '');
        formData.append('telefone', dados.telefone || '');
        if (novaFoto) formData.append('foto_perfil', novaFoto);

        try {
            const { data } = await api.patch('/usuarios/minha-conta/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setDados(data);
            setNovaFoto(null);
            alert('Dados da conta atualizados com sucesso!');
        } catch (err) {
            setErroPerfil(mensagemDeErro(err, 'Erro ao salvar os dados da conta.'));
        } finally {
            setSalvando(false);
        }
    };

    const handleTrocarSenha = async (e) => {
        e.preventDefault();
        setErroSenha(null);

        if (novaSenha !== confirmarNovaSenha) {
            setErroSenha('A confirmação não bate com a nova senha.');
            return;
        }

        setTrocandoSenha(true);
        try {
            await api.post('/usuarios/trocar-senha/', { senha_atual: senhaAtual, nova_senha: novaSenha });
            alert('Senha alterada com sucesso!');
            setSenhaAtual('');
            setNovaSenha('');
            setConfirmarNovaSenha('');
        } catch (err) {
            setErroSenha(mensagemDeErro(err, 'Erro ao alterar a senha.'));
        } finally {
            setTrocandoSenha(false);
        }
    };

    if (carregando) {
        return (
            <div className="page" style={{ maxWidth: '520px' }}>
                <p className="muted">Carregando...</p>
            </div>
        );
    }

    return (
        <div className="page" style={{ maxWidth: '520px' }}>
            <div className="page-header">
                <span className="kicker">Conta</span>
                <h2>Minha Conta</h2>
            </div>

            {erroPerfil && (
                <div className="alert alert--danger" style={{ marginBottom: '20px' }}>
                    <p className="alert__title">Não foi possível salvar</p>
                    <p className="alert__body" style={{ marginBottom: 0 }}>{erroPerfil}</p>
                </div>
            )}

            <div className="card">
                <div className="card__body">
                    <form onSubmit={handleSalvarPerfil}>
                        <div className="avatar-row">
                            {previewFoto || dados.foto_perfil ? (
                                <img className="avatar" src={previewFoto || dados.foto_perfil} alt="Foto de perfil" />
                            ) : (
                                <IniciaisAvatar nome={dados.username} />
                            )}
                            <div className="avatar-upload">
                                <label htmlFor="foto_perfil">Alterar foto</label>
                                <input
                                    id="foto_perfil"
                                    type="file"
                                    accept="image/*"
                                    onChange={(e) => setNovaFoto(e.target.files[0] || null)}
                                />
                            </div>
                        </div>

                        <div className="field">
                            <label htmlFor="username">Usuário</label>
                            <input
                                id="username"
                                className="input"
                                type="text"
                                value={dados.username}
                                onChange={(e) => setDados({ ...dados, username: e.target.value })}
                                required
                            />
                        </div>

                        <div className="field">
                            <label htmlFor="email">E-mail</label>
                            <input
                                id="email"
                                className="input"
                                type="email"
                                value={dados.email || ''}
                                onChange={(e) => setDados({ ...dados, email: e.target.value })}
                            />
                        </div>

                        <div className="field">
                            <label htmlFor="telefone">Número de celular</label>
                            <input
                                id="telefone"
                                className="input"
                                type="tel"
                                placeholder="(11) 91234-5678"
                                value={dados.telefone || ''}
                                onChange={(e) => setDados({ ...dados, telefone: e.target.value })}
                            />
                        </div>

                        <button type="submit" className="btn btn-accent btn-block" disabled={salvando}>
                            {salvando ? 'Salvando...' : 'Salvar alterações'}
                        </button>
                    </form>

                    <hr className="section-divider" />

                    <h3 style={{ fontSize: '15px', marginBottom: '16px' }}>Alterar senha</h3>

                    {erroSenha && (
                        <div className="alert alert--danger" style={{ marginBottom: '18px' }}>
                            <p className="alert__body" style={{ marginBottom: 0 }}>{erroSenha}</p>
                        </div>
                    )}

                    <form onSubmit={handleTrocarSenha}>
                        <div className="field">
                            <label htmlFor="senha_atual">Senha atual</label>
                            <input
                                id="senha_atual"
                                className="input"
                                type="password"
                                value={senhaAtual}
                                onChange={(e) => setSenhaAtual(e.target.value)}
                                required
                            />
                        </div>

                        <div className="field">
                            <label htmlFor="nova_senha">Nova senha</label>
                            <input
                                id="nova_senha"
                                className="input"
                                type="password"
                                value={novaSenha}
                                onChange={(e) => setNovaSenha(e.target.value)}
                                required
                            />
                        </div>

                        <div className="field">
                            <label htmlFor="confirmar_nova_senha">Confirmar nova senha</label>
                            <input
                                id="confirmar_nova_senha"
                                className="input"
                                type="password"
                                value={confirmarNovaSenha}
                                onChange={(e) => setConfirmarNovaSenha(e.target.value)}
                                required
                            />
                        </div>

                        <button type="submit" className="btn btn-ghost btn-block" disabled={trocandoSenha}>
                            {trocandoSenha ? 'Alterando...' : 'Alterar senha'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
