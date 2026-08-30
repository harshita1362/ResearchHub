# 🔬 ResearchHub

### AI-Powered Research Collaboration & Consulting Platform

> **Connect. Collaborate. Create Impact.**

ResearchHub is a full-stack research collaboration MVP for researchers, students and consultants. It combines research services, project management, milestones, secure file uploads, real-time project chat, an AI-ready research assistant, and online payments in one platform.

## ✨ MVP

- 🔐 JWT authentication
- 👤 Researcher and consultant roles
- 🔬 Research services marketplace
- 📋 Research projects + milestones
- 📁 Project file uploads
- 💬 Real-time WebSocket chat
- 🤖 AI research assistant endpoint
- 💳 Stripe Checkout payment integration
- 📊 Dashboard statistics
- 📱 Flutter Android client
- 🐘 PostgreSQL
- 🐳 Docker / Docker Compose
- ☁️ Production-ready container deployment configuration

## 🛠️ Technology Stack

**Backend** · Python · FastAPI · SQLAlchemy · PostgreSQL · WebSockets  
**Frontend** · React · Vite · JavaScript · CSS  
**Mobile** · Flutter · Dart  
**AI** · OpenAI-compatible API endpoint · Research Assistant architecture  
**Security** · JWT · bcrypt · CORS · role-aware API design  
**Payments** · Stripe Checkout + webhook  
**DevOps** · Docker · Docker Compose · Render Blueprint

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/harshita1362/researchhub.git
cd researchhub
```

### 2. Backend

```bash
cd backend
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Backend: `http://127.0.0.1:8000`  
Swagger: `http://127.0.0.1:8000/docs`

### 3. Web frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite app normally runs at `http://localhost:5173`.

### 4. PostgreSQL + complete stack with Docker

From the repository root:

```bash
docker compose up --build
```

Backend: `http://localhost:8000`  
Web: `http://localhost:5173`

## 💳 Payments

Set these values in `backend/.env`:

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
FRONTEND_URL=http://localhost:5173
```

Create a Stripe webhook pointing to:

```text
https://YOUR-DOMAIN/api/payments/webhook
```

For local webhook testing, Stripe CLI can forward events to:

```text
stripe listen --forward-to localhost:8000/api/payments/webhook
```

The implementation uses Stripe Checkout in test mode. Never commit secret keys.

## 🤖 AI

The AI endpoint is intentionally provider-agnostic. Add an OpenAI-compatible key:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

Without a key, ResearchHub returns a safe local research-planning response so the MVP remains runnable.

## 📱 Flutter

```bash
cd mobile
flutter pub get
flutter run
```

For an Android emulator, the backend URL is configured in `lib/config.dart` as `http://10.0.2.2:8000`. For a physical phone, replace it with the computer's LAN IP.

## ☁️ Production

The repository contains:

- `Dockerfile`
- `docker-compose.yml`
- `render.yaml`
- `.env.example`
- health endpoint
- PostgreSQL configuration
- production CORS configuration
- Stripe webhook endpoint
- WebSocket endpoint

For a real deployment, set production secrets, HTTPS, a managed PostgreSQL database, object storage for uploaded files, and a production frontend URL.


## 🛡️ Quality & Security

This version includes defensive defaults intended for an MVP:

- Password hashing with bcrypt
- JWT authentication and ownership checks
- Input length validation
- Login/registration rate limiting
- Security response headers
- Restricted CORS defaults
- File-extension allowlist and 15 MB upload limit
- Randomized stored filenames
- Stripe signature verification and idempotent paid-state update
- Audit events for important project/payment actions
- WebSocket authentication and message-length limits
- Research Integrity Guard to encourage citation, provenance and reproducibility checks

### Test the backend

```bash
cd backend
pytest -q
```

> No software can honestly be guaranteed to have “zero loopholes.” Before accepting real users or money, run a security review, dependency scan, HTTPS deployment, managed database backups, private object storage, and production monitoring.

## 🔐 Ethical Research Support

ResearchHub is designed for legitimate research consulting and technical support. It supports methodology, implementation, analysis, experimentation, mentoring and editing. It does not promote plagiarism, fabricated results, manipulated data or academic misconduct.

## 📁 Repository

```text
ResearchHub/
├── backend/
├── frontend/
├── mobile/
├── deploy/
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── README.md
```

## 📄 License

MIT
