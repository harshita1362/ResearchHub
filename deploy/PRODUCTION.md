# Production deployment

## Backend

1. Create a managed PostgreSQL database.
2. Deploy `backend/` as a Docker web service.
3. Set `DATABASE_URL`, `SECRET_KEY`, `FRONTEND_URL`, `ALLOWED_ORIGINS`.
4. Add Stripe and AI secrets only through the cloud provider's secret manager.
5. Enable HTTPS.
6. Configure the Stripe webhook to `/api/payments/webhook`.
7. For production file storage, replace local `uploads/` with S3-compatible object storage.

## Frontend

Build the web application:

```bash
cd frontend
npm install
npm run build
```

Set:

```env
VITE_API_URL=https://api.yourdomain.com
```

Deploy the `dist/` directory to a static hosting provider.

## Mobile

Set `apiBaseUrl` in `mobile/lib/config.dart` to the HTTPS API domain, then:

```bash
flutter build apk --release
```

## Important production hardening

- Use a strong random `SECRET_KEY`.
- Restrict `ALLOWED_ORIGINS` to the actual frontend domain.
- Keep Stripe/OpenAI secrets out of Git.
- Use managed PostgreSQL backups.
- Move uploaded research documents to private object storage.
- Add antivirus/content scanning and file-type allowlists before public launch.
- Add rate limiting and account/email verification.
- Use a persistent WebSocket/pub-sub layer such as Redis when scaling the API horizontally.
- Run database migrations rather than relying on `create_all()` for long-term production schema changes.


## Pre-launch security checklist

- [ ] HTTPS only
- [ ] Strong generated SECRET_KEY
- [ ] Production ALLOWED_ORIGINS only
- [ ] Managed PostgreSQL with backups
- [ ] Private S3-compatible storage instead of local uploads
- [ ] Malware/file-content scanning
- [ ] Redis-backed rate limiting and WebSocket pub/sub when scaled
- [ ] Database migrations (Alembic) before schema changes
- [ ] Centralized logs + error monitoring
- [ ] Stripe live-mode webhook secret stored in a secret manager
- [ ] Dependency vulnerability scan and secret scan in CI
- [ ] Privacy policy, terms, refund policy and research-integrity policy
- [ ] Human review for disputes and consultant deliverables
