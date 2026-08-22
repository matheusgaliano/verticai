import React, { useState } from 'react';
import api from '../services/api';

const ETAPAS = [
    { chave: 'upload', label: 'Upload' },
    { chave: 'escolher-cargo', label: 'Escolher cargo' },
    { chave: 'revisar', label: 'Confirmar' },
];

function mensagemDeErro(err, generica) {
    return err.response?.data?.detail || generica;
}

function StepIndicator({ etapaAtual }) {
    const indiceAtual = ETAPAS.findIndex((e) => e.chave === etapaAtual);
    return (
        <div className="steps">
            {ETAPAS.map((etapa, indice) => (
                <React.Fragment key={etapa.chave}>
                    {indice > 0 && <span className="steps__line" />}
                    <span
                        className={`steps__item ${
                            indice === indiceAtual
                                ? 'steps__item--active'
                                : indice < indiceAtual
                                ? 'steps__item--done'
                                : ''
                        }`}
                    >
                        <span className="steps__dot" />
                        {indice + 1}. {etapa.label}
                    </span>
                </React.Fragment>
            ))}
        </div>
    );
}

export default function UploadEdital() {
    const [etapa, setEtapa] = useState('upload');
    const [file, setFile] = useState(null);
    const [arrastando, setArrastando] = useState(false);
    const [loading, setLoading] = useState(false);
    const [erro, setErro] = useState(null);

    const [identificacao, setIdentificacao] = useState(null); // { concurso, ano, data_prova, cargos }
    const [cargoEscolhido, setCargoEscolhido] = useState(null); // { nome, vagas }
    const [disciplinas, setDisciplinas] = useState(null);

    const handleDragOver = (e) => {
        e.preventDefault();
        setArrastando(true);
    };
    const handleDragLeave = () => setArrastando(false);
    const handleDrop = (e) => {
        e.preventDefault();
        setArrastando(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
        }
    };

    const reiniciar = () => {
        setEtapa('upload');
        setFile(null);
        setIdentificacao(null);
        setCargoEscolhido(null);
        setDisciplinas(null);
        setErro(null);
    };

    // Etapa 1 -> 2: envia o PDF, a IA identifica concurso e cargos.
    const handleIdentificar = async (e) => {
        e.preventDefault();
        if (!file) return;

        setErro(null);
        setLoading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const { data } = await api.post('/editais/identificar-cargos/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setIdentificacao(data);
            setCargoEscolhido(data.cargos[0] || null);
            setEtapa('escolher-cargo');
        } catch (err) {
            setErro(mensagemDeErro(err, 'Erro ao identificar o edital. Tente novamente.'));
        } finally {
            setLoading(false);
        }
    };

    // Etapa 2 -> 3: com o cargo escolhido, a IA extrai disciplinas/tópicos/pesos.
    const handleDetalhar = async () => {
        if (!cargoEscolhido) return;

        setErro(null);
        setLoading(true);
        const formData = new FormData();
        formData.append('file', file);
        formData.append('cargo_nome', cargoEscolhido.nome);

        try {
            const { data } = await api.post('/editais/detalhar-cargo/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setDisciplinas(data.disciplinas);
            setEtapa('revisar');
        } catch (err) {
            setErro(mensagemDeErro(err, 'Erro ao detalhar o cargo escolhido. Tente novamente.'));
        } finally {
            setLoading(false);
        }
    };

    // Etapa 3: confirma e persiste Concurso/Edital/Cargo/Disciplina/Tópico.
    // O `file` vai como upload normal; o resto (estruturado, com listas
    // aninhadas) vai como um único campo JSON — multipart não tem uma forma
    // nativa de representar isso.
    const handleConfirmar = async () => {
        setErro(null);
        setLoading(true);

        const dados = {
            concurso: identificacao.concurso,
            ano: identificacao.ano,
            data_prova: identificacao.data_prova,
            cargo_nome: cargoEscolhido.nome,
            vagas: cargoEscolhido.vagas || 1,
            disciplinas,
        };

        const formData = new FormData();
        formData.append('file', file);
        formData.append('dados', JSON.stringify(dados));

        try {
            await api.post('/editais/confirmar/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            alert('Edital confirmado e cadastrado com sucesso!');
            reiniciar();
        } catch (err) {
            setErro(mensagemDeErro(err, 'Erro ao salvar o edital. Tente novamente.'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page" style={{ maxWidth: '560px' }}>
            <div className="page-header">
                <span className="kicker">Editais</span>
                <h2>Importar edital em PDF</h2>
            </div>

            <StepIndicator etapaAtual={etapa} />

            {erro && (
                <div className="alert alert--danger" style={{ marginBottom: '20px' }}>
                    <p className="alert__title">Não foi possível continuar</p>
                    <p className="alert__body" style={{ marginBottom: 0 }}>{erro}</p>
                </div>
            )}

            <div className="card">
                <div className="card__body">
                    {etapa === 'upload' && (
                        <form onSubmit={handleIdentificar}>
                            <p className="muted" style={{ marginBottom: '18px', fontSize: '13.5px' }}>
                                Envie o PDF do edital. A IA vai identificar o concurso e todos os
                                cargos mencionados nele — você escolhe qual quer prestar na próxima etapa.
                            </p>

                            <div
                                className={`dropzone ${arrastando ? 'dropzone--active' : ''}`}
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                style={{ marginBottom: '20px' }}
                            >
                                {file ? (
                                    <p className="dropzone__file">Arquivo selecionado: {file.name}</p>
                                ) : (
                                    <p>Arraste o PDF do edital aqui ou clique para selecionar</p>
                                )}
                                <input
                                    type="file"
                                    accept=".pdf"
                                    onChange={(e) => setFile(e.target.files[0])}
                                />
                            </div>

                            <button type="submit" className="btn btn-accent btn-block" disabled={loading || !file}>
                                {loading ? 'Identificando cargos...' : 'Processar PDF'}
                            </button>
                        </form>
                    )}

                    {etapa === 'escolher-cargo' && identificacao && (
                        <div>
                            <p className="review-summary">
                                Concurso identificado: <strong>{identificacao.concurso.nome}</strong>
                                {' — '}
                                {identificacao.concurso.orgao}
                                {identificacao.ano ? ` (${identificacao.ano})` : ''}
                            </p>

                            <p className="muted" style={{ marginBottom: '12px', fontSize: '13.5px' }}>
                                Qual cargo deste edital você vai prestar?
                            </p>

                            {identificacao.cargos.map((cargo) => (
                                <label
                                    key={cargo.nome}
                                    className={`cargo-option ${
                                        cargoEscolhido?.nome === cargo.nome ? 'cargo-option--selected' : ''
                                    }`}
                                >
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <input
                                            type="radio"
                                            name="cargo"
                                            checked={cargoEscolhido?.nome === cargo.nome}
                                            onChange={() => setCargoEscolhido(cargo)}
                                        />
                                        <span className="cargo-option__nome">{cargo.nome}</span>
                                    </span>
                                    {cargo.vagas != null && (
                                        <span className="cargo-option__vagas">{cargo.vagas} vagas</span>
                                    )}
                                </label>
                            ))}

                            <div className="wizard-actions">
                                <button className="btn btn-ghost" onClick={reiniciar} disabled={loading}>
                                    Voltar
                                </button>
                                <button
                                    className="btn btn-accent"
                                    onClick={handleDetalhar}
                                    disabled={loading || !cargoEscolhido}
                                >
                                    {loading ? 'Extraindo conteúdo...' : 'Continuar'}
                                </button>
                            </div>
                        </div>
                    )}

                    {etapa === 'revisar' && disciplinas && (
                        <div>
                            <p className="review-summary">
                                Cargo: <strong>{cargoEscolhido.nome}</strong> — confira o conteúdo
                                programático identificado antes de confirmar.
                            </p>

                            {disciplinas.map((disciplina) => (
                                <div className="review-disciplina" key={disciplina.nome}>
                                    <div className="review-disciplina__head">
                                        <span className="review-disciplina__nome">{disciplina.nome}</span>
                                        <span className="review-disciplina__peso">peso {disciplina.peso}</span>
                                    </div>
                                    <ul className="review-topicos">
                                        {disciplina.topicos.map((topico) => (
                                            <li key={topico}>{topico}</li>
                                        ))}
                                    </ul>
                                </div>
                            ))}

                            <div className="wizard-actions">
                                <button
                                    className="btn btn-ghost"
                                    onClick={() => setEtapa('escolher-cargo')}
                                    disabled={loading}
                                >
                                    Voltar
                                </button>
                                <button className="btn btn-accent" onClick={handleConfirmar} disabled={loading}>
                                    {loading ? 'Salvando...' : 'Confirmar e salvar'}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
