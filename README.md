# VerticAI

Plataforma para organização de estudos para concursos públicos. O sistema lê edital em PDF, extrai as disciplinas com IA e gera um cronograma diário baseado no tempo disponível e na data da prova.

## Tecnologias

- **Backend:** Python, Django, Django REST Framework, JWT, SQLite, Stripe
- **Frontend:** React (Vite), Axios, React Router

## Funcionalidades

- Autenticação de usuários (JWT)
- Leitura e extração de disciplinas/tópicos de editais em PDF
- Geração de plano de estudos diário automático
- Controle de acesso por assinatura (Stripe)

## Como rodar o projeto

### Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
### Frontend

```
cd frontend
npm install
npm run dev

Acesse em http://localhost:5173.

```
---

Para atualizar no repositório:

```bash
git add README.md
git commit -m "docs: simplifica readme"
git push
```
