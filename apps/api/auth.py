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

# 10 Pre-configured initial users with simple initial passwords
INITIAL_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "name": "مدیر ارشد سامانه",
        "role": "Super Admin",
        "department": "مرکز فرماندهی و رصد استراتژیک",
        "clearance_level": "Level 5 (Top Secret)",
        "badge_color": "emerald",
        "avatar": "🛡️"
    },
    {
        "username": "intel_officer",
        "password": "intel123",
        "name": "افسر ارشد اطلاعات",
        "role": "Senior Intelligence Analyst",
        "department": "اداره کل اطلاعات و امنیت راهبردی",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "cyan",
        "avatar": "🦅"
    },
    {
        "username": "defense_analyst",
        "password": "defense123",
        "name": "تحلیل‌گر استراتژی دفاعی",
        "role": "Defense Strategy Analyst",
        "department": "قرارگاه مطالعات دفاعی و موشکی",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "blue",
        "avatar": "⚔️"
    },
    {
        "username": "osint_lead",
        "password": "osint123",
        "name": "سرپرست رصد متن‌باز",
        "role": "OSINT Collection Lead",
        "department": "شبکه پایش ماهواره‌ای و منابع باز",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "indigo",
        "avatar": "🛰️"
    },
    {
        "username": "cyber_intel",
        "password": "cyber123",
        "name": "کارشناس پایش سایبری",
        "role": "Cyber Threat Analyst",
        "department": "مرکز تحلیل تهدیدات فضای مجازی",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "purple",
        "avatar": "💻"
    },
    {
        "username": "geo_specialist",
        "password": "geo123",
        "name": "متخصص مطالعات ژئوپلیتیک",
        "role": "Geopolitical Strategist",
        "department": "اندیشکده ژئوپلیتیک غرب آسیا",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "amber",
        "avatar": "🌐"
    },
    {
        "username": "ai_operator",
        "password": "ai123",
        "name": "اپراتور هوش مصنوعی",
        "role": "AI & NLP Operator",
        "department": "آزمایشگاه پردازش داده‌های کلان و هوش محلی",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "rose",
        "avatar": "🧠"
    },
    {
        "username": "field_editor",
        "password": "editor123",
        "name": "ویراستار صحت‌سنجی اخبار",
        "role": "News Verification Editor",
        "department": "اتاق خبر و راستی‌آزمایی روایت‌ها",
        "clearance_level": "Level 2 (Restricted)",
        "badge_color": "teal",
        "avatar": "✍️"
    },
    {
        "username": "strategic_planner",
        "password": "foresight123",
        "name": "پژوهشگر آینده‌پژوهی",
        "role": "Strategic Foresight Officer",
        "department": "مرکز تحقیقات روندها و سناریونگاری",
        "clearance_level": "Level 2 (Restricted)",
        "badge_color": "sky",
        "avatar": "🔭"
    },
    {
        "username": "guest_viewer",
        "password": "guest123",
        "name": "کاربر ناظر / مهمان",
        "role": "Observer / Guest",
        "department": "پژوهشکده روابط بین‌الملل",
        "clearance_level": "Level 1 (Internal Only)",
        "badge_color": "zinc",
        "avatar": "👤"
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

            if not verify_password(password, salt, stored_hash):
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
