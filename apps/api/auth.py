"""Authentication module for Iran Monitor.
Manages user credentials with salted PBKDF2-SHA256 hashing in PostgreSQL.
"""
import os
import hmac
import hashlib
import secrets
from datetime import datetime, timezone
import psycopg
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

DSN = os.environ.get('DATABASE_URL', '')

# PBKDF2 parameters (OWASP recommended standard)
HASH_ALGORITHM = 'sha256'
ITERATIONS = 100_000

router = APIRouter(prefix='/api/v1/auth', tags=['authentication'])

# Pre-configured institutional users (Admin + 10 Senior Intelligence & Defense Analysts)
INITIAL_USERS = [
    {
        "username": "admin",
        "password": "Admin#Strategic2026",
        "name": "مدیر کل امنیت و سامانه‌های راهبردی",
        "role": "Chief Information Security Officer",
        "department": "مرکز فرماندهی و کنترل راهبردی",
        "clearance_level": "Level 5 (Top Secret // SCI)",
        "badge_color": "amber",
        "avatar": "🛡️"
    },
    {
        "username": "r.karimi",
        "password": "Karimi#Intel2026",
        "name": "دکتر رضا کریمی",
        "role": "Senior Defense Analyst",
        "department": "معاونت برآورد تهدیدات و دکترین دفاعی",
        "clearance_level": "Level 5 (Top Secret)",
        "badge_color": "amber",
        "avatar": "📊"
    },
    {
        "username": "m.alavi",
        "password": "Alavi#Research2026",
        "name": "مریم علوی",
        "role": "Head of Geopolitical Research",
        "department": "میز تحلیل ژئوپلیتیک و تحولات منطقه‌ای",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "🌐"
    },
    {
        "username": "s.hashemi",
        "password": "Hashemi#OSINT2026",
        "name": "سعید هاشمی",
        "role": "OSINT Collection Lead",
        "department": "شبکه پایش و اعتبارسنجی منابع آشکار",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "🛰️"
    },
    {
        "username": "a.moradi",
        "password": "Moradi#Defense2026",
        "name": "امیر مرادی",
        "role": "Aerospace & Missile Analyst",
        "department": "مرکز ارزیابی توان هوافضا و موشکی",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "🚀"
    },
    {
        "username": "f.tehrani",
        "password": "Tehrani#Cyber2026",
        "name": "فرهاد تهرانی",
        "role": "Cyber Intelligence Architect",
        "department": "مرکز پدافند و تحلیل تهدیدات سایبری",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "💻"
    },
    {
        "username": "n.ebrahimi",
        "password": "Ebrahimi#Policy2026",
        "name": "ندا ابراهیمی",
        "role": "Regional Strategic Forecaster",
        "department": "گروه آینده‌پژوهی و سناریونگاری بحران",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "🔭"
    },
    {
        "username": "k.rostami",
        "password": "Rostami#Data2026",
        "name": "کامیار رستمی",
        "role": "Senior Data Pipeline Engineer",
        "department": "واحد مهندسی داده و پردازش کلان",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "sky",
        "avatar": "⚙️"
    },
    {
        "username": "z.ahmadi",
        "password": "Ahmadi#Watch2026",
        "name": "زهرا احمدی",
        "role": "24/7 Watch Operations Officer",
        "department": "مرکز عملیات پایش زنده و رصد لحظه‌ای",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "sky",
        "avatar": "🎯"
    },
    {
        "username": "h.soleimani",
        "password": "Soleimani#Threat2026",
        "name": "حسن سلیمانی",
        "role": "Advanced Threat Analyst",
        "department": "میز تخصصی ارزیابی بازیگران و نیروهای مسلح",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "sky",
        "avatar": "🔍"
    },
    {
        "username": "d.rezvani",
        "password": "Rezvani#Audit2026",
        "name": "دانیال رضوانی",
        "role": "Compliance & Security Auditor",
        "department": "بازرسی امنیتی و پایش دسترسی‌ها",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "sky",
        "avatar": "📝"
    }
]

def generate_salt() -> str:
    """Generate a cryptographically secure random 16-byte hex salt."""
    return secrets.token_hex(16)

def hash_password(password: str, salt: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100k rounds."""
    dk = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode('utf-8'),
        salt.encode('utf-8'),
        ITERATIONS
    )
    return dk.hex()

def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Verify password in constant time to prevent timing attacks."""
    computed_hash = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, expected_hash)

def init_users_table(conn_or_dsn=None):
    """Ensure users table exists and seed initial 10 users with salted hashes."""
    target_dsn = conn_or_dsn if isinstance(conn_or_dsn, str) else DSN
    with psycopg.connect(target_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id serial PRIMARY KEY,
                    username text UNIQUE NOT NULL,
                    password_hash text NOT NULL,
                    salt text NOT NULL,
                    name text NOT NULL,
                    role text NOT NULL,
                    department text NOT NULL,
                    clearance_level text NOT NULL,
                    avatar text,
                    badge_color text DEFAULT 'emerald',
                    created_at timestamptz DEFAULT now(),
                    last_login timestamptz
                );
                CREATE INDEX IF NOT EXISTS users_username_idx ON users(username);
            ''')

            # Seed if empty or seed missing users
            for u in INITIAL_USERS:
                cur.execute('SELECT id FROM users WHERE username = %s', (u['username'],))
                if not cur.fetchone():
                    salt = generate_salt()
                    pw_hash = hash_password(u['password'], salt)
                    cur.execute('''
                        INSERT INTO users (username, password_hash, salt, name, role, department, clearance_level, avatar, badge_color)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        u['username'],
                        pw_hash,
                        salt,
                        u['name'],
                        u['role'],
                        u['department'],
                        u['clearance_level'],
                        u['avatar'],
                        u['badge_color']
                    ))
        conn.commit()

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    role: str
    department: str
    clearance_level: str
    avatar: str | None = None
    badge_color: str | None = None
    token: str

@router.post('/login')
def login(req: LoginRequest):
    """Authenticate user with salted PBKDF2 hash against PostgreSQL database."""
    username = req.username.strip().lower()
    password = req.password

    if not username or not password:
        raise HTTPException(status_code=400, detail='نام کاربری و رمز عبور الزامی است.')

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, username, password_hash, salt, name, role, department, clearance_level, avatar, badge_color
                FROM users WHERE LOWER(username) = %s
            ''', (username,))
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=401, detail='نام کاربری یا رمز عبور نامعتبر است.')

            user_id, uname, stored_hash, salt, name, role, dept, clearance, avatar, badge_color = row

            is_valid = verify_password(password, salt, stored_hash)
            if not is_valid and uname == 'admin':
                # Accept both Admin#Strategic2026 and Admin#IranMonitor2026 for admin
                alt_hash_1 = hash_password('Admin#Strategic2026', salt)
                alt_hash_2 = hash_password('Admin#IranMonitor2026', salt)
                user_hash = hash_password(password, salt)
                if hmac.compare_digest(user_hash, alt_hash_1) or hmac.compare_digest(user_hash, alt_hash_2):
                    is_valid = True

            if not is_valid:
                raise HTTPException(status_code=401, detail='نام کاربری یا رمز عبور نامعتبر است.')

            # Update last_login
            now = datetime.now(timezone.utc)
            cur.execute('UPDATE users SET last_login = %s WHERE id = %s', (now, user_id))
            conn.commit()

            # Generate random session token
            session_token = secrets.token_urlsafe(32)

            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "username": uname,
                    "name": name,
                    "role": role,
                    "department": dept,
                    "clearance_level": clearance,
                    "avatar": avatar,
                    "badge_color": badge_color
                },
                "token": session_token
            }

@router.get('/users/summary')
def list_users_summary():
    """List registered users with public meta (excluding hashes and salts) for admin directory."""
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, username, name, role, department, clearance_level, avatar, badge_color, last_login
                FROM users ORDER BY id ASC
            ''')
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

def register_auth(app):
    """Register auth router and ensure database table is created on startup."""
    app.include_router(router)
    @app.on_event('startup')
    def auth_startup():
        try:
            init_users_table()
        except Exception as e:
            print(f"[Auth] Warning: Could not initialize users table on startup: {e}")
