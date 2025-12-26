from __future__ import annotations
import os, json, subprocess, sys
from datetime import datetime, timezone
from hashlib import sha256
from sqlalchemy import create_engine, text
from hakilix.config import settings
from hakilix.security import hash_password

def main():
    db_url = (os.environ.get("DATABASE_URL_MIGRATOR") or os.environ.get("HAKILIX_DATABASE_URL_MIGRATOR") or os.environ.get("DATABASE_URL_APP") or os.environ.get("HAKILIX_DATABASE_URL_APP") or settings.database_url_migrator or settings.database_url_app)
    if not db_url:
        raise SystemExit("No database URL configured (set DATABASE_URL_APP or DATABASE_URL_MIGRATOR)")

    # Run migrations
    subprocess.run([sys.executable, "-m", "alembic", "-c", "/app/alembic.ini", "upgrade", "head"], check=True)

    eng = create_engine(db_url, future=True)
    now = datetime.now(timezone.utc)

    agency_id = settings.demo_agency_id
    token = "devtok_" + sha256((settings.demo_device_id + agency_id).encode("utf-8")).hexdigest()[:24]
    token_hash = sha256(token.encode("utf-8")).hexdigest()

    with eng.begin() as c:
        c.execute(text("INSERT INTO hakilix.agencies(id,name,created_at) VALUES (:id,:n,:t) ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name"),
                  {"id": agency_id, "n": settings.demo_agency_name, "t": now})
        c.execute(text("""
            INSERT INTO hakilix.users(id, agency_id, email, password_hash, role, created_at)
            VALUES ('U-001', :aid, :e, :ph, 'agency_admin', :t)
            ON CONFLICT(email) DO UPDATE SET password_hash=EXCLUDED.password_hash
        """), {"aid": agency_id, "e": settings.demo_admin_email, "ph": hash_password(settings.demo_admin_password), "t": now})
        # Seed 10 demo residents so the dashboard has a realistic fleet.
        # R-001 is kept compatible with existing demos.
        for i in range(1, 11):
            rid = f"R-{i:03d}"
            dn = settings.demo_resident_name if rid == settings.demo_resident_id else f"Resident {i:02d}"
            c.execute(
                text(
                    """
                    INSERT INTO hakilix.residents(id, agency_id, display_name, created_at)
                    VALUES (:id, :aid, :dn, :t)
                    ON CONFLICT(id) DO UPDATE SET display_name=EXCLUDED.display_name
                    """
                ),
                {"id": rid, "aid": agency_id, "dn": dn, "t": now},
            )
        c.execute(text("""
            INSERT INTO hakilix.devices(id, agency_id, resident_id, state, token_hash, token_version, rotated_at, created_at)
            VALUES (:id, :aid, :rid, 'active', :th, 1, NULL, :t)
            ON CONFLICT(id) DO UPDATE SET token_hash=EXCLUDED.token_hash, state='active'
        """), {"id": settings.demo_device_id, "aid": agency_id, "rid": settings.demo_resident_id, "th": token_hash, "t": now})
        c.execute(text("""
            INSERT INTO hakilix.audit_log(time, agency_id, actor_user_id, action, resource, resource_id, detail)
            VALUES (:t,:aid,'U-001','seed.complete','agency',:rid,:d)
        """), {"t": now, "aid": agency_id, "rid": agency_id, "d": json.dumps({"device_token": token})})

    print("Migrations complete. Demo seeded.")
    print("Device token (demo):", token)

if __name__ == "__main__":
    main()
