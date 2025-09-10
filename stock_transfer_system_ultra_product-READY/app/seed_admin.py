from app.db.session import SessionLocal
from app.models.user import User, Organization
from app.core.security import hash_password

# Open DB session
db = SessionLocal()

# Make sure an org exists (required for user org_id)
org = db.query(Organization).first()
if not org:
    org = Organization(name="Default Org")
    db.add(org)
    db.commit()
    db.refresh(org)

# Check if admin already exists
admin = db.query(User).filter(User.email == "admin@example.com").first()
if not admin:
    admin = User(
        email="admin@example.com",
        name="Admin User",
        role="Admin",
        hashed_password=hash_password("admin123"),
        org_id=org.id,
    )
    db.add(admin)
    db.commit()
    print("✅ Admin user created: admin@example.com / admin123")
else:
    print("ℹ️ Admin user already exists:", admin.email)
