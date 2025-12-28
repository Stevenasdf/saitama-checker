# db.py - Core DB SaitamaChk (SIN auto init)

import sqlite3
import logging

# ==============================
# CONFIG
# ==============================

DB_NAME = "saitamachk.db"
OWNER_ID = 6522771171

RANKS = ("free", "premium", "admin", "owner")

MAX_PROXIES = 50
MAX_SHOPIFY_SITES = 50
MAX_STRIPE_SITES = 50

# ==============================
# LOGGING
# ==============================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("db")

# ==============================
# CONEXIÓN
# ==============================

def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def q(query, params=(), one=False, all=False):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        conn.commit()

        if one:
            r = cur.fetchone()
            return dict(r) if r else None
        if all:
            return [dict(x) for x in cur.fetchall()]
        return True
    except Exception as e:
        conn.rollback()
        log.error(f"SQL ERROR: {e} | {query} | {params}")
        raise
    finally:
        conn.close()

# ==============================
# USUARIOS
# ==============================

def get_user(user_id):
    return q(
        "SELECT user_id, rank, days, registered_at FROM users WHERE user_id = ?",
        (user_id,),
        one=True
    )

def register_user(user_id):
    if get_user(user_id):
        return False, "Ya registrado"

    q(
        "INSERT INTO users (user_id, rank, days) VALUES (?, 'free', 0)",
        (user_id,)
    )
    return True, "OK"

def get_user_rank(user_id):
    u = get_user(user_id)
    return u["rank"] if u else "free"

def update_user_rank(user_id, rank):
    q("UPDATE users SET rank = ? WHERE user_id = ?", (rank, user_id))

def update_user_days(user_id, delta):
    u = get_user(user_id)
    if not u:
        return False
    days = max(0, u["days"] + delta)
    q("UPDATE users SET days = ? WHERE user_id = ?", (days, user_id))
    return True

# ==============================
# PERMISOS
# ==============================

def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    return get_user_rank(user_id) in ("admin", "owner")

def is_premium(user_id):
    return get_user_rank(user_id) in ("premium", "admin", "owner")

# ==============================
# PROXIES
# ==============================

def get_user_proxies(user_id):
    rows = q(
        "SELECT proxies FROM proxy_management WHERE user_id = ? ORDER BY rowid ASC",
        (user_id,),
        all=True
    )
    return [r["proxies"] for r in rows]

def add_user_proxy(user_id, proxy):
    if q(
        "SELECT 1 FROM proxy_management WHERE user_id = ? AND proxies = ?",
        (user_id, proxy),
        one=True
    ):
        return False, "Duplicada"

    q(
        "INSERT INTO proxy_management (user_id, proxies) VALUES (?, ?)",
        (user_id, proxy)
    )
    return True, "OK"

def remove_user_proxy(user_id, proxy):
    q(
        "DELETE FROM proxy_management WHERE user_id = ? AND proxies = ?",
        (user_id, proxy)
    )

def clear_user_proxies(user_id):
    q("DELETE FROM proxy_management WHERE user_id = ?", (user_id,))

def count_user_proxies(user_id):
    r = q(
        "SELECT COUNT(*) c FROM proxy_management WHERE user_id = ?",
        (user_id,),
        one=True
    )
    return r["c"]

# ==============================
# SHOPIFY
# ==============================

def get_user_shopify_sites(user_id):
    rows = q(
        "SELECT shopify_sites FROM shopify_management WHERE user_id = ? ORDER BY rowid ASC",
        (user_id,),
        all=True
    )
    return [r["shopify_sites"] for r in rows]

def add_user_shopify_site(user_id, site):
    if q(
        "SELECT 1 FROM shopify_management WHERE user_id = ? AND shopify_sites = ?",
        (user_id, site),
        one=True
    ):
        return False, "Duplicado"

    q(
        "INSERT INTO shopify_management (user_id, shopify_sites) VALUES (?, ?)",
        (user_id, site)
    )
    return True, "OK"

def remove_user_shopify_site(user_id, site):
    q(
        "DELETE FROM shopify_management WHERE user_id = ? AND shopify_sites = ?",
        (user_id, site)
    )

def clear_user_shopify_sites(user_id):
    q("DELETE FROM shopify_management WHERE user_id = ?", (user_id,))

def count_user_shopify_sites(user_id):
    r = q(
        "SELECT COUNT(*) c FROM shopify_management WHERE user_id = ?",
        (user_id,),
        one=True
    )
    return r["c"]

# ==============================
# STRIPE
# ==============================

def get_user_stripe_sites(user_id):
    rows = q(
        "SELECT stripe_sites FROM stripe_management WHERE user_id = ? ORDER BY rowid ASC",
        (user_id,),
        all=True
    )
    return [r["stripe_sites"] for r in rows]

def add_user_stripe_site(user_id, site):
    if q(
        "SELECT 1 FROM stripe_management WHERE user_id = ? AND stripe_sites = ?",
        (user_id, site),
        one=True
    ):
        return False, "Duplicado"

    q(
        "INSERT INTO stripe_management (user_id, stripe_sites) VALUES (?, ?)",
        (user_id, site)
    )
    return True, "OK"

def remove_user_stripe_site(user_id, site):
    q(
        "DELETE FROM stripe_management WHERE user_id = ? AND stripe_sites = ?",
        (user_id, site)
    )

def clear_user_stripe_sites(user_id):
    q("DELETE FROM stripe_management WHERE user_id = ?", (user_id,))

def count_user_stripe_sites(user_id):
    r = q(
        "SELECT COUNT(*) c FROM stripe_management WHERE user_id = ?",
        (user_id,),
        one=True
    )
    return r["c"]

# ==============================
# LIMITES
# ==============================

def check_limit(user_id, res):
    if res == "proxies":
        return count_user_proxies(user_id) >= MAX_PROXIES
    if res == "shopify_sites":
        return count_user_shopify_sites(user_id) >= MAX_SHOPIFY_SITES
    if res == "stripe_sites":
        return count_user_stripe_sites(user_id) >= MAX_STRIPE_SITES
    return False