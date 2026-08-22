import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function UploadEdital() {
    const [file, setFile] = useState(null);
    const [cargoId, setCargoId] = useState('');
    const [cargos, setCargos] = useState([]);
    const [loading, setLoading] = useState(false);

    // Busca os cargos cadastrados ao carregar a página
    useEffect(() => {
        api.get('/editais/cargos/')
            .then((res) => {
                setCargos(res.data || []);
            })
            .catch(() => alert('Erro ao carregar a lista de cargos.'));
    }, []);

    const handleDragOver = (e) => e.preventDefault();

    const handleDrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
        }
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!file || !cargoId) return alert('Selecione um PDF e um Cargo.');

        const formData = new FormData();
        formData.append('file', file);
        formData.append('cargo_id', cargoId);

        setLoading(true);
        try {
            await api.post('/editais/processar-pdf/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            alert('Edital processado e disciplinas cadastradas com sucesso!');
            setFile(null);
            setCargoId('');
        } catch (err) {
            alert('Erro ao processar o edital.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ maxWidth: '500px', margin: '40px auto' }}>
            <h2>Upload de Edital PDF</h2>
            <form onSubmit={handleUpload}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                    Selecione o Cargo:
                </label>
                <select
                    value={cargoId}
                    onChange={(e) => setCargoId(e.target.value)}
                    required
                    style={{ width: '100%', padding: '10px', marginBottom: '20px' }}
                >
                    <option value="">-- Selecione o Cargo (ex: Contador, Agente) --</option>
                    {cargos.map((cargo) => (
                        <option key={cargo.id} value={cargo.id}>
                            {cargo.nome}
                        </option>
                    ))}
                </select>

                <div
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                    style={{ border: '2px dashed #888', padding: '30px', textAlign: 'center', cursor: 'pointer', borderRadius: '8px' }}
                >
                    {file ? (
                        <p style={{ color: '#28a745', fontWeight: 'bold' }}>Arquivo selecionado: {file.name}</p>
                    ) : (
                        <p>Arraste o PDF do Edital aqui ou clique para selecionar</p>
                    )}
                    <input
                        type="file"
                        accept=".pdf"
                        onChange={(e) => setFile(e.target.files[0])}
                        style={{ marginTop: '10px' }}
                    />
                </div><br />

                <button
                    type="submit"
                    disabled={loading}
                    style={{ width: '100%', padding: '12px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                    {loading ? 'Processando com IA...' : 'Enviar e Processar Edital'}
                </button>
            </form>
        </div>
    );
}