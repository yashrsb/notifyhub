# notifyhub - Phase 1 scaffold checklist

## 1. Scaffold project structure
- [ ] Create `backend/` directory layout
- [ ] Add core entrypoints: `backend/app/main.py` + routers

## 2. Dependencies & config
- [ ] Create `backend/requirements.txt`
- [ ] Add Dockerfile + docker-compose
- [ ] Add `.env.example` and config loader

## 3. Database (async SQLAlchemy + Alembic)
- [ ] Create SQLAlchemy async engine/session
- [ ] Implement models: users, notification_templates, notifications
- [ ] Configure Alembic env for async
- [ ] Create initial migration

## 4. Auth module (JWT + bcrypt)
- [ ] Implement register/login endpoints
- [ ] Implement password hashing + JWT creation/validation
- [ ] Implement protected dependency `get_current_user`

## 5. Templates CRUD
- [ ] Implement templates routes + repository + service

## 6. Notifications module
- [ ] Implement notifications create/list/get
- [ ] Render template variables before saving

## 7. API standards
- [ ] Consistent response envelope `{success, data, message}`
- [ ] Global exception handling
- [ ] API versioning under `/api/v1`

## 8. Tests (pytest)
- [ ] Create test database fixtures
- [ ] Write tests: registration/login, template CRUD, notification creation

## 9. Documentation
- [ ] README setup instructions + env vars + API overview
- [ ] Ensure OpenAPI docs works

