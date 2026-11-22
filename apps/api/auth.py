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

# Pre-configured initial users (Admin + 10 Specialized Operational Intelligence Roles)
INITIAL_USERS = [
    {
        "username": "admin",
        "password": "Admin#Strategic2026!",
        "name": "مدیر کل امنیت و سامانه‌های راهبردی",
        "role": "Super Admin & Defense Director",
        "department": "مرکز فرماندهی و کنترل راهبردی",
        "clearance_level": "Level 5 (Top Secret // SCI)",
        "badge_color": "amber",
        "avatar": "🛡️"
    },
    {
        "username": "cipher_sentinel",
        "password": "Sentinel#Secure91!",
        "name": "فرمانده پایش سیگنالی و رمزنگاری",
        "role": "Chief Cryptanalyst",
        "department": "مرکز عملیات سیگنال و امواج",
        "clearance_level": "Level 5 (Top Secret)",
        "badge_color": "amber",
        "avatar": "🔐"
    },
    {
        "username": "vanguard_intel",
        "password": "Vanguard@Ops2026",
        "name": "سرپرست ارزیابی تهدیدات پیشرفته",
        "role": "Principal Threat Analyst",
        "department": "معاونت تحلیل و برآورد راهبردی",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "🦅"
    },
    {
        "username": "shadow_recon",
        "password": "Recon#Orbital77!",
        "name": "متخصص شناسایی و تصویربرداری ماهواره‌ای",
        "role": "IMINT & Geospatial Analyst",
        "department": "رصدخانه اطلاعات مکانی و مداری",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "🛰️"
    },
    {
        "username": "cyber_warden",
        "password": "Warden@Shield42#",
        "name": "مدیر پدافند سایبری و جنگ الکترونیک",
        "role": "Cyber Threat Architect",
        "department": "فرماندهی پدافند سایبری",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "⚡"
    },
    {
        "username": "nexus_analyst",
        "password": "Nexus#Tactical88$",
        "name": "تحلیل‌گر ارشد همگرایی ژئوپلیتیک",
        "role": "Senior Geopolitical Analyst",
        "department": "گروه مطالعات بحران‌های منطقه‌ای",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "🌐"
    },
    {
        "username": "apex_commander",
        "password": "Apex@Command55!",
        "name": "رئیس میز عملیات ۲۴ ساعته پایش",
        "role": "Watch Operations Director",
        "department": "مرکز عملیات وضعیت لحظه‌ای (TOC)",
        "clearance_level": "Level 4 (Secret)",
        "badge_color": "emerald",
        "avatar": "🎯"
    },
    {
        "username": "strato_observer",
        "password": "Strato#SkyWatch99@",
        "name": "افسر رصد و اخطار هوانوردی و موشکی",
        "role": "Aerospace Intelligence Officer",
        "department": "مرکز هشدار زودهنگام پدافند هوایی",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "sky",
        "avatar": "🚀"
    },
    {
        "username": "iron_gate",
        "password": "Iron#Defense33!",
        "name": "سرپرست حریم اطلاعاتی و حفاظت زیرساخت",
        "role": "Infrastructure Security Lead",
        "department": "پایش زیرساخت‌های حیاتی و انرژی",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "sky",
        "avatar": "🏰"
    },
    {
        "username": "horizon_scout",
        "password": "Horizon@Radar24#",
        "name": "سرپرست رصد متن‌باز و شبکه‌های منطقه‌ای",
        "role": "Senior OSINT Scout",
        "department": "شبکه جمع‌آوری اطلاعات منابع آشکار",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "sky",
        "avatar": "🔭"
    },
    {
        "username": "ghost_matrix",
        "password": "Matrix#Signal19$",
        "name": "پژوهشگر جنگ روانی و تحلیل داده‌های کلان",
        "role": "Info-Ops & Big Data Analyst",
        "department": "مرکز داده‌کاوی و پردازش پیشرفته",
        "clearance_level": "Level 3 (Confidential)",
        "badge_color": "sky",
        "avatar": "📡"
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
