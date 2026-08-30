import os, re, secrets, time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Set

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from .database import Base, engine, get_db, SessionLocal
from .models import User, Service, Project, Milestone, ResearchFile, Booking, Message, AuditEvent
from .schemas import RegisterRequest, LoginRequest, ProjectCreate, AIRequest
from .auth import hash_password, verify_password, create_token, current_user
import stripe
import httpx

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ResearchHub API",
    version="1.1.0",
    description="Research collaboration, consulting, integrity and payment API."
)

raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
origins = [x.strip() for x in raw_origins.split(",") if x.strip()]
if "*" in origins:
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Simple per-process rate limiter. Replace with Redis-backed limiting when horizontally scaling.
_rate = defaultdict(deque)
def rate_limit(request: Request, bucket: str, limit: int = 60, window: int = 60):
    now = time.time()
    key = f"{request.client.host if request.client else 'unknown'}:{bucket}"
    q = _rate[key]
    while q and q[0] <= now - window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many requests. Please try again shortly.")
    q.append(now)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/", include_in_schema=False)
def root():
    return {"name": "ResearchHub", "version": "1.1.0", "docs": "/docs", "health": "/api/health"}

@app.get("/api/health")
def health():
    db = SessionLocal()
    try:
        db.execute(sql_text("SELECT 1"))
        return {"status": "ok", "database": "ok", "service": "ResearchHub"}
    finally:
        db.close()

def normalize_email(email: str) -> str:
    return email.strip().lower()

def log_event(db, user_id, action, project_id=None, details=""):
    db.add(AuditEvent(user_id=user_id, project_id=project_id, action=action, details=details[:1000]))
    db.commit()

@app.post("/api/auth/register")
def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "register", 10)
    email = normalize_email(data.email)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")
    role = data.role if data.role in {"researcher", "consultant"} else "researcher"
    user = User(
        name=data.name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        role=role,
        research_interest=data.research_interest.strip()[:255],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_token(user), "user": serialize_user(user)}

@app.post("/api/auth/login")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "login", 12)
    user = db.query(User).filter(User.email == normalize_email(data.email)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"token": create_token(user), "user": serialize_user(user)}

@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return serialize_user(user)

@app.get("/api/services")
def services(db: Session = Depends(get_db)):
    return [serialize_service(s) for s in db.query(Service).order_by(Service.id).all()]

@app.post("/api/services/{service_id}/book")
def book(service_id: int, notes: str = "", user: User = Depends(current_user), db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(404, "Service not found")
    booking = Booking(user_id=user.id, service_id=service.id, notes=notes[:2000])
    db.add(booking)
    db.commit()
    db.refresh(booking)
    log_event(db, user.id, "booking_created", details=f"service_id={service.id}")
    return {"booking_id": booking.id, "status": booking.status}

@app.post("/api/payments/checkout/{service_id}")
def checkout(service_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(404, "Service not found")
    secret = os.getenv("STRIPE_SECRET_KEY")
    if not secret:
        return {"demo": True, "message": "Stripe is not configured. Set STRIPE_SECRET_KEY to enable Checkout."}
    stripe.api_key = secret
    booking = Booking(user_id=user.id, service_id=service.id, notes="", status="Payment Pending")
    db.add(booking)
    db.commit()
    db.refresh(booking)
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {"name": service.title},
                    "unit_amount": service.price_inr * 100,
                },
                "quantity": 1,
            }],
            metadata={"booking_id": str(booking.id), "user_id": str(user.id), "service_id": str(service.id)},
            success_url=os.getenv("FRONTEND_URL", "http://localhost:5173") + "?payment=success",
            cancel_url=os.getenv("FRONTEND_URL", "http://localhost:5173") + "?payment=cancelled",
        )
    except Exception:
        booking.status = "Payment Error"
        db.commit()
        raise HTTPException(502, "Payment provider could not create checkout.")
    booking.stripe_session_id = session.id
    db.commit()
    log_event(db, user.id, "checkout_created", details=f"booking_id={booking.id}")
    return {"checkout_url": session.url, "booking_id": booking.id}

@app.post("/api/payments/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    if len(payload) > 1024 * 1024:
        raise HTTPException(413, "Webhook payload too large")
    signature = request.headers.get("stripe-signature")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(400, "Stripe webhook secret is not configured")
    try:
        event = stripe.Webhook.construct_event(payload, signature, secret)
    except Exception:
        raise HTTPException(400, "Invalid Stripe webhook")
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata") or {}
        try:
            booking_id = int(metadata["booking_id"])
        except (KeyError, ValueError):
            return {"received": True}
        booking = db.get(Booking, booking_id)
        if booking and not booking.paid:
            booking.paid = True
            booking.status = "Paid"
            db.commit()
            log_event(db, booking.user_id, "payment_completed", details=f"booking_id={booking.id}")
    return {"received": True}

@app.get("/api/projects")
def projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [serialize_project(p) for p in db.query(Project).filter(Project.owner_id == user.id).order_by(Project.id.desc()).all()]

@app.post("/api/projects")
def create_project(data: ProjectCreate, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(request, "project-create", 30)
    title = data.title.strip()
    if not title:
        raise HTTPException(422, "Project title cannot be empty")
    project = Project(title=title, description=data.description.strip()[:5000], owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    for title in ["Research scope & literature", "Methodology & experiments", "Analysis & documentation"]:
        db.add(Milestone(project_id=project.id, title=title))
    db.commit()
    log_event(db, user.id, "project_created", project.id)
    return serialize_project(project)

@app.get("/api/projects/{project_id}")
def project_detail(project_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = get_owned_project(project_id, user, db)
    return serialize_project(project, detailed=True)

@app.post("/api/projects/{project_id}/files")
async def upload_file(project_id: int, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = get_owned_project(project_id, user, db)
    allowed = {
        "pdf", "docx", "doc", "txt", "csv", "xlsx", "xls",
        "pptx", "ppt", "png", "jpg", "jpeg", "zip"
    }
    safe_name = Path(file.filename or "").name
    if not safe_name or "." not in safe_name:
        raise HTTPException(400, "A valid filename is required")
    extension = safe_name.rsplit(".", 1)[1].lower()
    if extension not in allowed:
        raise HTTPException(415, "Unsupported research file type")
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "Maximum file size is 15 MB")
    stored_name = f"{project_id}_{secrets.token_hex(8)}_{safe_name}"
    destination = UPLOAD_DIR / stored_name
    destination.write_bytes(content)
    record = ResearchFile(project_id=project.id, filename=safe_name, path=str(destination))
    db.add(record)
    db.commit()
    log_event(db, user.id, "file_uploaded", project.id, safe_name)
    return {"message": "File uploaded", "filename": safe_name}

@app.get("/api/projects/{project_id}/messages")
def messages(project_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = get_owned_project(project_id, user, db)
    return [serialize_message(m) for m in db.query(Message).filter(Message.project_id == project.id).order_by(Message.id.asc()).limit(100).all()]

@app.get("/api/projects/{project_id}/audit")
def audit(project_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_owned_project(project_id, user, db)
    return [
        {"action": e.action, "details": e.details, "created_at": e.created_at.isoformat()}
        for e in db.query(AuditEvent).filter(AuditEvent.project_id == project_id).order_by(AuditEvent.id.desc()).limit(100).all()
    ]

@app.post("/api/research/integrity-check")
def integrity_check(data: AIRequest, user: User = Depends(current_user)):
    return {"checks": [
        {"name": "Citation verification", "status": "REQUIRED", "note": "Verify every citation against the original source."},
        {"name": "Data provenance", "status": "REQUIRED", "note": "Record dataset source, version, license and preprocessing."},
        {"name": "Experiment reproducibility", "status": "REQUIRED", "note": "Preserve seeds, splits, parameters and environment."},
        {"name": "Result integrity", "status": "REQUIRED", "note": "Never fabricate, selectively remove or alter results."},
        {"name": "Authorship", "status": "REVIEW", "note": "All contributors should receive appropriate credit."},
    ], "topic": data.prompt[:500]}

@app.get("/api/stats")
def stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    ps = db.query(Project).filter(Project.owner_id == user.id).all()
    return {
        "projects": len(ps),
        "active": sum(p.status != "Completed" for p in ps),
        "completed": sum(p.status == "Completed" for p in ps),
        "avg_progress": round(sum(p.progress for p in ps) / len(ps)) if ps else 0,
    }

@app.post("/api/ai/assist")
async def ai_assist(data: AIRequest, user: User = Depends(current_user)):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {"answer": local_research_assistant(data.prompt), "mode": "local"}
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are an ethical research assistant. Help with research questions, methodology, experiment design, datasets, analysis and reproducibility. Never fabricate citations, data or results. Distinguish suggestions from verified facts."},
                        {"role": "user", "content": data.prompt},
                    ],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return {"answer": payload["choices"][0]["message"]["content"], "mode": "ai"}
    except Exception:
        return {"answer": local_research_assistant(data.prompt), "mode": "local-fallback"}

class ConnectionManager:
    def __init__(self):
        self.connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, project_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(project_id, set()).add(websocket)

    def disconnect(self, project_id: int, websocket: WebSocket):
        self.connections.get(project_id, set()).discard(websocket)

    async def broadcast(self, project_id: int, message: dict):
        for ws in list(self.connections.get(project_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(project_id, ws)

manager = ConnectionManager()

@app.websocket("/ws/projects/{project_id}")
async def websocket_chat(websocket: WebSocket, project_id: int):
    token = websocket.query_params.get("token")
    db = SessionLocal()
    try:
        if not token:
            await websocket.close(code=1008)
            return
        from jose import jwt, JWTError
        try:
            payload = jwt.decode(token, os.getenv("SECRET_KEY", "development-only-secret-change-me"), algorithms=["HS256"])
            user = db.get(User, int(payload["sub"]))
        except (JWTError, ValueError, TypeError, KeyError):
            user = None
        project = db.get(Project, project_id)
        if not user or not project or project.owner_id != user.id:
            await websocket.close(code=1008)
            return
        await manager.connect(project_id, websocket)
        await manager.broadcast(project_id, {"type": "system", "text": f"{user.name} joined the workspace."})
        while True:
            data = await websocket.receive_json()
            message_text = str(data.get("text", "")).strip()
            if not message_text or len(message_text) > 2000:
                continue
            message = Message(project_id=project_id, user_id=user.id, text=message_text)
            db.add(message)
            db.commit()
            db.refresh(message)
            log_event(db, user.id, "message_sent", project_id)
            await manager.broadcast(project_id, {"type": "message", **serialize_message(message)})
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
    finally:
        db.close()

def get_owned_project(project_id, user, db):
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(404, "Project not found")
    return project

def serialize_user(u):
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "research_interest": u.research_interest}

def serialize_service(s):
    return {"id": s.id, "title": s.title, "category": s.category, "description": s.description, "price_inr": s.price_inr, "duration": s.duration, "icon": s.icon}

def serialize_message(m):
    return {"id": m.id, "project_id": m.project_id, "user_id": m.user_id, "text": m.text, "created_at": m.created_at.isoformat()}

def serialize_project(p, detailed=False):
    data = {"id": p.id, "title": p.title, "description": p.description, "status": p.status, "progress": p.progress, "created_at": p.created_at.isoformat()}
    if detailed:
        data["milestones"] = [{"id": m.id, "title": m.title, "status": m.status} for m in p.milestones]
        data["files"] = [{"id": f.id, "filename": f.filename} for f in p.files]
        data["messages"] = [serialize_message(m) for m in p.messages[-100:]]
    return data

def local_research_assistant(prompt):
    return (
        "ResearchHub AI (local mode): Start by defining the research question and hypothesis. "
        "Specify the dataset, inclusion/exclusion criteria, preprocessing, baseline models, "
        "evaluation metrics, validation strategy and reproducibility plan. "
        f"Your topic was: {prompt[:500]}"
    )

def seed():
    db = SessionLocal()
    if db.query(Service).count() == 0:
        db.add_all([
            Service(title="Research Gap Analysis", category="Research Strategy", description="Identify literature gaps and turn them into actionable research questions.", price_inr=2500, duration="2–3 days", icon="💡"),
            Service(title="AI/ML Technical Support", category="Implementation", description="Hands-on support for Python, ML/DL experiments, evaluation and reproducibility.", price_inr=5000, duration="3–7 days", icon="🤖"),
            Service(title="Cybersecurity Research Support", category="Cybersecurity", description="Technical assistance for cybersecurity experiments, datasets and analysis.", price_inr=5000, duration="3–7 days", icon="🛡️"),
            Service(title="Statistical Analysis", category="Data Science", description="Clean analysis, evaluation metrics and publication-ready visualizations.", price_inr=3000, duration="2–4 days", icon="📊"),
            Service(title="Research Consultation", category="Mentoring", description="Focused one-to-one discussion about your research direction and next steps.", price_inr=1000, duration="60 minutes", icon="🎓"),
            Service(title="Paper Editing & Formatting", category="Publication", description="Language, structure and formatting support while preserving author ownership.", price_inr=2000, duration="2–4 days", icon="📝"),
        ])
        db.commit()
    db.close()

seed()
