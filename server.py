"""
CrystalMC & MasterCraft — Backend v3
pip install flask flask-cors mcrcon mcstatus
python server.py
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from mcrcon import MCRcon
import sqlite3, os, hashlib, datetime, threading, time, json, secrets

app = Flask(__name__, static_folder=".")
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

OWNER_LOGIN  = "echoranger"
OWNER_PASS   = "shamsiddin1312"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(BASE_DIR, "donate.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "checks")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

RANK_MAP = {"VIP":"vip","VIP+":"vip_plus","LEGEND":"legend","DONATOR":"donator","GOLD":"gold","NITRO":"nitro","COMET":"comet","HERO":"hero","ULTRA":"ultra","PRIME":"prime"}

# ── DB ──
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, nick TEXT NOT NULL, rank TEXT NOT NULL,
            period TEXT, duration TEXT, amount INTEGER NOT NULL,
            original_amount INTEGER, promo_code TEXT, discount_percent INTEGER DEFAULT 0,
            tg TEXT, check_file TEXT, status TEXT DEFAULT 'pending',
            time TEXT NOT NULL, approved_at TEXT, expires_at TEXT,
            type TEXT DEFAULT 'rank', token_amount TEXT)""")
        # Migrate existing orders table if needed
        try: con.execute("ALTER TABLE orders ADD COLUMN original_amount INTEGER")
        except: pass
        try: con.execute("ALTER TABLE orders ADD COLUMN promo_code TEXT")
        except: pass
        try: con.execute("ALTER TABLE orders ADD COLUMN discount_percent INTEGER DEFAULT 0")
        except: pass
        con.execute("""CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY, discount_percent INTEGER NOT NULL DEFAULT 10,
            max_uses INTEGER DEFAULT 0, used_count INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1, created TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL, password_hash TEXT, name TEXT,
            role TEXT DEFAULT 'moder', tg TEXT, google_id TEXT,
            google_email TEXT, avatar TEXT, active INTEGER DEFAULT 1, created TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
        default_ranks = json.dumps([
            {"id":"VIP",    "name":"VIP",    "icon":"🟢","lp":"vip",      "color":"#00E5FF","month_price":2999, "life_price":5999},
            {"id":"VIP+",   "name":"VIP+",   "icon":"💎","lp":"vip_plus", "color":"#7B61FF","month_price":5999, "life_price":12999},
            {"id":"LEGEND", "name":"LEGEND", "icon":"⭐","lp":"legend",   "color":"#FF55CC","month_price":8999, "life_price":20999},
            {"id":"DONATOR","name":"DONATOR","icon":"💰","lp":"donator",  "color":"#F97316","month_price":9999, "life_price":25999},
            {"id":"GOLD",   "name":"GOLD",   "icon":"🏆","lp":"gold",     "color":"#FFD700","month_price":14999,"life_price":34999},
            {"id":"NITRO",  "name":"NITRO",  "icon":"⚡","lp":"nitro",    "color":"#FF4DE6","month_price":17999,"life_price":42999},
            {"id":"COMET",  "name":"COMET",  "icon":"☄️","lp":"comet",    "color":"#00FFC8","month_price":22999,"life_price":55999},
            {"id":"HERO",   "name":"HERO",   "icon":"🦸","lp":"hero",     "color":"#44AAFF","month_price":27999,"life_price":79999},
            {"id":"ULTRA",  "name":"ULTRA",  "icon":"🔥","lp":"ultra",    "color":"#22C55E","month_price":33999,"life_price":99999},
            {"id":"PRIME",  "name":"PRIME",  "icon":"👑","lp":"prime",    "color":"#FF5533","month_price":49999,"life_price":149999}
        ])
        defaults = {"rcon_host":"localhost","rcon_port":"25575","rcon_password":"",
                    "card_number":"3400 0385 6025 XXXX","card_holder":"MASTERCRAFT ADMIN",
                    "card_bank":"Uzcard / Humo","tg_admin":"@MASTERCRAFT_ADMIN","google_client_id":"",
                    "ranks_config":default_ranks}
        for k,v in defaults.items():
            con.execute("INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)",(k,v))
        con.commit()

def get_db():
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row; return con

init_db()

def get_setting(k, d=""): 
    with get_db() as con:
        r=con.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone()
        return r["value"] if r else d

def set_setting(k,v):
    with get_db() as con:
        con.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",(k,v)); con.commit()

def get_all_settings():
    with get_db() as con:
        return {r["key"]:r["value"] for r in con.execute("SELECT key,value FROM settings").fetchall()}

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

# ── AUTH ──
def check_auth():
    token = request.headers.get("X-Admin-Token","")
    import base64
    try:
        decoded = base64.b64decode(token).decode()
        if decoded == f"{OWNER_LOGIN}:{OWNER_PASS}": return True
    except: pass
    if token == hash_pass(f"{OWNER_LOGIN}:{OWNER_PASS}"): return True
    with get_db() as con:
        for acc in con.execute("SELECT * FROM accounts WHERE active=1").fetchall():
            if acc["password_hash"] and token == hash_pass(f"{acc['login']}:{acc['password_hash']}"): return True
            if acc["google_id"] and token == hash_pass(f"{acc['login']}:{acc['google_id']}"): return True
    return False

def get_current_user(token):
    import base64
    try:
        if base64.b64decode(token).decode() == f"{OWNER_LOGIN}:{OWNER_PASS}":
            return {"login":OWNER_LOGIN,"name":"Owner","role":"owner"}
    except: pass
    if token == hash_pass(f"{OWNER_LOGIN}:{OWNER_PASS}"):
        return {"login":OWNER_LOGIN,"name":"Owner","role":"owner"}
    with get_db() as con:
        for acc in con.execute("SELECT * FROM accounts WHERE active=1").fetchall():
            if acc["password_hash"] and token == hash_pass(f"{acc['login']}:{acc['password_hash']}"):
                return dict(acc)
            if acc["google_id"] and token == hash_pass(f"{acc['login']}:{acc['google_id']}"):
                return dict(acc)
    return None

# ── RANKS CONFIG ──
def get_ranks():
    raw=get_setting("ranks_config","[]")
    try: return json.loads(raw)
    except: return []

@app.route("/api/ranks")
def api_ranks():
    return jsonify({"ok":True,"ranks":get_ranks()})

@app.route("/api/ranks",methods=["POST"])
def api_ranks_save():
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    ranks=request.get_json() or []
    set_setting("ranks_config",json.dumps(ranks))
    return jsonify({"ok":True,"message":"Ranklar saqlandi"})

# ── RCON ──
def run_rcon(cmd):
    host=get_setting("rcon_host","localhost")
    port=int(get_setting("rcon_port","25575"))
    password=get_setting("rcon_password","")
    with MCRcon(host,password,port=port) as mcr: return mcr.command(cmd)

def give_rank(nick, rank, period):
    # ranks_config  `` dan lp nomini olish
    ranks=get_ranks()
    lp=rank.lower()
    for r in ranks:
        if r["id"]==rank: lp=r.get("lp",rank.lower()); break
    if not lp: lp=RANK_MAP.get(rank,rank.lower())
    # period DB da "30 kun" yoki "Butun umr" sifatida saqlanadi
    is_temp = period in ("month", "30 kun")
    cmd=f"lp user {nick} parent add {lp}" if not is_temp else f"lp user {nick} parent addtemp {lp} 30d"
    return run_rcon(cmd), cmd

def give_token(nick, amount):
    cmd=f"points give {nick} {amount}"
    return run_rcon(cmd), cmd

def do_unban(nick):
    cmd=f"unban {nick}"  # RCON da / belgisi kerak emas
    return run_rcon(cmd), cmd

# ── EXPIRE ──
def expire_checker():
    while True:
        try:
            now=datetime.datetime.utcnow().isoformat()
            with get_db() as con:
                expired=con.execute("SELECT id FROM orders WHERE period='month' AND status='approved' AND expires_at<?  AND type='rank'",(now,)).fetchall()
                for r in expired: con.execute("UPDATE orders SET status='expired' WHERE id=?",(r["id"],))
                con.commit()
        except: pass
        time.sleep(600)

threading.Thread(target=expire_checker,daemon=True).start()

# ── STATIC ──
@app.route("/")
def index(): return send_from_directory(".","donate.html")

@app.route("/admin")
@app.route("/admin.html")
def admin_page(): return send_from_directory(".","admin.html")

@app.route("/checks/<path:filename>")
def get_check(filename):
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    return send_from_directory(UPLOAD_FOLDER,filename)

# ── AUTH API ──
@app.route("/api/auth/login",methods=["POST"])
def auth_login():
    d=request.get_json() or {}
    l,p=d.get("login","").strip(),d.get("password","")
    if l==OWNER_LOGIN and p==OWNER_PASS:
        import base64
        return jsonify({"ok":True,"token":base64.b64encode(f"{OWNER_LOGIN}:{OWNER_PASS}".encode()).decode(),"user":{"login":OWNER_LOGIN,"name":"Owner","role":"owner","avatar":None}})
    with get_db() as con:
        acc=con.execute("SELECT * FROM accounts WHERE login=? AND active=1",(l,)).fetchone()
    if acc and acc["password_hash"]==hash_pass(p):
        return jsonify({"ok":True,"token":hash_pass(f"{acc['login']}:{acc['password_hash']}"),"user":{"login":acc["login"],"name":acc["name"] or acc["login"],"role":acc["role"],"avatar":acc["avatar"],"tg":acc["tg"]}})
    return jsonify({"ok":False,"error":"Login yoki parol noto'g'ri!"}),401

@app.route("/api/auth/register",methods=["POST"])
def auth_register():
    d=request.get_json() or {}
    l,p=d.get("login","").strip(),d.get("password","")
    name=d.get("name","").strip()
    role=d.get("role","moder")
    token=request.headers.get("X-Admin-Token","")
    if token: 
        if not check_auth(): return jsonify({"ok":False,"error":"Ruxsat yo'q"}),403
    else: role="moder"
    if not l or not p: return jsonify({"ok":False,"error":"Login va parol kiritish shart"}),400
    if l==OWNER_LOGIN: return jsonify({"ok":False,"error":"Bu login band!"}),400
    with get_db() as con:
        if con.execute("SELECT id FROM accounts WHERE login=?",(l,)).fetchone():
            return jsonify({"ok":False,"error":"Bu login allaqachon mavjud!"}),400
        con.execute("INSERT INTO accounts (login,password_hash,name,role,tg,active,created) VALUES (?,?,?,?,?,1,?)",
                    (l,hash_pass(p),name or l,role,d.get("tg",""),datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
        con.commit()
    return jsonify({"ok":True,"message":"Akkaunt yaratildi!"})

@app.route("/api/auth/google",methods=["POST"])
def auth_google():
    d=request.get_json() or {}
    google_token=d.get("token","")
    try:
        import urllib.request
        with urllib.request.urlopen(f"https://oauth2.googleapis.com/tokeninfo?id_token={google_token}") as resp:
            info=json.loads(resp.read().decode())
        google_id=info.get("sub"); email=info.get("email"); name=info.get("name",email); avatar=info.get("picture")
        if not google_id: return jsonify({"ok":False,"error":"Google token noto'g'ri"}),400
        with get_db() as con:
            acc=con.execute("SELECT * FROM accounts WHERE google_id=? AND active=1",(google_id,)).fetchone()
            if not acc:
                con.execute("INSERT INTO accounts (login,name,role,google_id,google_email,avatar,active,created) VALUES (?,?,?,?,?,?,1,?)",
                           (email,name,"moder",google_id,email,avatar,datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
                con.commit()
                acc=con.execute("SELECT * FROM accounts WHERE google_id=?",(google_id,)).fetchone()
        token=hash_pass(f"{acc['login']}:{acc['google_id']}")
        return jsonify({"ok":True,"token":token,"user":{"login":acc["login"],"name":acc["name"],"role":acc["role"],"avatar":acc["avatar"],"google_email":acc["google_email"]}})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/auth/me")
def auth_me():
    token=request.headers.get("X-Admin-Token","")
    user=get_current_user(token)
    if not user: return jsonify({"ok":False,"error":"Token noto'g'ri"}),401
    return jsonify({"ok":True,"user":user})

# ── SETTINGS ──
@app.route("/api/settings",methods=["GET"])
def get_settings():
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    s=get_all_settings()
    if s.get("rcon_password"): s["rcon_password"]="••••••••"
    return jsonify({"ok":True,"settings":s})

@app.route("/api/settings",methods=["POST"])
def update_settings():
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    d=request.get_json() or {}
    allowed=["rcon_host","rcon_port","rcon_password","card_number","card_holder","card_bank","tg_admin","google_client_id"]
    updated=[]
    for k in allowed:
        if k in d and d[k] and d[k]!="••••••••": set_setting(k,str(d[k])); updated.append(k)
    return jsonify({"ok":True,"updated":updated,"message":f"{len(updated)} ta sozlama saqlandi"})

@app.route("/api/settings/public")
def public_settings():
    return jsonify({"ok":True,
        "card_number":get_setting("card_number","3400 0385 6025 XXXX"),
        "card_holder":get_setting("card_holder","MASTERCRAFT ADMIN"),
        "card_bank":get_setting("card_bank","Uzcard / Humo"),
        "tg_admin":get_setting("tg_admin","@MASTERCRAFT_ADMIN"),
        "google_client_id":get_setting("google_client_id","")})

# ── ACCOUNTS ──
@app.route("/api/accounts")
def list_accounts():
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    with get_db() as con:
        rows=[dict(r) for r in con.execute("SELECT id,login,name,role,tg,google_email,avatar,active,created FROM accounts").fetchall()]
    return jsonify({"ok":True,"accounts":rows})

@app.route("/api/accounts/<int:aid>",methods=["PUT"])
def update_account(aid):
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    d=request.get_json() or {}
    with get_db() as con:
        if "active" in d: con.execute("UPDATE accounts SET active=? WHERE id=?",(1 if d["active"] else 0,aid))
        if "role" in d: con.execute("UPDATE accounts SET role=? WHERE id=?",(d["role"],aid))
        if "password" in d and d["password"]: con.execute("UPDATE accounts SET password_hash=? WHERE id=?",(hash_pass(d["password"]),aid))
        con.commit()
    return jsonify({"ok":True})

@app.route("/api/accounts/<int:aid>",methods=["DELETE"])
def delete_account(aid):
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    with get_db() as con:
        con.execute("DELETE FROM accounts WHERE id=?",(aid,)); con.commit()
    return jsonify({"ok":True})

# ── ORDERS ──
@app.route("/api/orders",methods=["POST"])
def create_order():
    nick=request.form.get("nick","").strip()
    rank=request.form.get("rank","").strip().upper()
    period=request.form.get("period","month")
    amount=request.form.get("amount","0")
    tg=request.form.get("tg","").strip()
    order_type=request.form.get("type","rank")  # rank | token | unban
    token_amount=request.form.get("token_amount","")
    check=request.files.get("check")
    promo_code=request.form.get("promo_code","").strip().upper()
    discount_percent=0; original_amount=int(amount)

    if not nick: return jsonify({"ok":False,"error":"Nick majburiy"}),400

    # Validate promo code if provided
    if promo_code:
        with get_db() as con:
            prow=con.execute("SELECT * FROM promocodes WHERE code=? AND active=1",(promo_code,)).fetchone()
        if prow and (prow["max_uses"]==0 or prow["used_count"]<prow["max_uses"]):
            discount_percent=prow["discount_percent"]
            original_amount=int(amount)
            amount=str(int(original_amount*(1-discount_percent/100)))
            with get_db() as con:
                con.execute("UPDATE promocodes SET used_count=used_count+1 WHERE code=?",(promo_code,))
                con.commit()
        else:
            promo_code=""  # invalid, ignore silently

    check_file=None
    if check and check.filename:
        ext=os.path.splitext(check.filename)[1].lower()
        if ext not in [".png",".jpg",".jpeg",".webp"]:
            return jsonify({"ok":False,"error":"Faqat rasm fayl yuklang"}),400
        ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe="".join(c for c in nick if c.isalnum() or c in "-_")[:20]
        check_file=f"{ts}_{safe}{ext}"
        check.save(os.path.join(UPLOAD_FOLDER,check_file))

    # Period label
    if order_type=="token": period_label=f"Token x{token_amount}"
    elif order_type=="unban": period_label="Bir martalik"
    else: period_label="30 kun" if period=="month" else "Butun umr"

    oid=f"ORD-{int(datetime.datetime.now().timestamp()*1000)}"
    with get_db() as con:
        con.execute("INSERT INTO orders (id,nick,rank,period,amount,original_amount,promo_code,discount_percent,tg,check_file,status,time,type,token_amount) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (oid,nick,rank,period_label,int(amount),original_amount,promo_code or None,discount_percent,tg,check_file,"pending",
                     datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),order_type,token_amount))
        con.commit()
    return jsonify({"ok":True,"id":oid})

@app.route("/api/my-orders")
def my_orders():
    nick = request.args.get("nick","").strip()
    if not nick:
        return jsonify({"ok":False,"error":"Nick kiritilmagan"}),400
    with get_db() as con:
        rows=[dict(r) for r in con.execute(
            "SELECT id,nick,rank,period,amount,original_amount,promo_code,discount_percent,status,time,approved_at,expires_at,type,token_amount FROM orders WHERE nick=? ORDER BY time DESC LIMIT 50",
            (nick,)).fetchall()]
    return jsonify({"ok":True,"orders":rows})

@app.route("/api/orders")
def list_orders():
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    status=request.args.get("status")
    q=request.args.get("q","")
    order_type=request.args.get("type")  # token | unban
    sql="SELECT * FROM orders WHERE 1=1"; params=[]
    if order_type: sql+=" AND type=?"; params.append(order_type)
    if status and not order_type: sql+=" AND status=?"; params.append(status)
    if q: sql+=" AND (nick LIKE ? OR rank LIKE ?)"; params+=[f"%{q}%",f"%{q}%"]
    sql+=" ORDER BY time DESC"
    with get_db() as con:
        rows=[dict(r) for r in con.execute(sql,params).fetchall()]
    for r in rows:
        if r.get("check_file"): r["check_url"]=f"/checks/{r['check_file']}"
    stats={}
    with get_db() as con:
        for s in ["pending","approved","rejected","expired"]:
            stats[s]=con.execute("SELECT COUNT(*) FROM orders WHERE status=?",(s,)).fetchone()[0]
    stats["total"]=sum(stats.values())
    return jsonify({"ok":True,"orders":rows,"stats":stats})

@app.route("/api/orders/<oid>/approve",methods=["POST"])
def approve_order(oid):
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    with get_db() as con:
        row=con.execute("SELECT * FROM orders WHERE id=?",(oid,)).fetchone()
    if not row: return jsonify({"ok":False,"error":"Order topilmadi"}),404
    if row["status"]=="approved": return jsonify({"ok":False,"error":"Allaqachon tasdiqlangan"}),400

    cmd=""; resp=""
    try:
        if row["type"]=="token":
            resp,cmd=give_token(row["nick"],row["token_amount"] or "1000")
        elif row["type"]=="unban":
            resp,cmd=do_unban(row["nick"])
        else:
            resp,cmd=give_rank(row["nick"],row["rank"],row["period"])
    except Exception as e:
        return jsonify({"ok":False,"error":f"RCON xatolik: {e}","hint":"Minecraft server yoqilganmi? RCON sozlamalarini tekshiring."}),500

    expires=None
    if row["type"]=="rank" and row["period"]=="30 kun":
        expires=(datetime.datetime.utcnow()+datetime.timedelta(days=30)).isoformat()

    with get_db() as con:
        con.execute("UPDATE orders SET status='approved',approved_at=?,expires_at=? WHERE id=?",
                    (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),expires,oid))
        con.commit()
    return jsonify({"ok":True,"message":"✅ Muvaffaqiyatli!","command":cmd,"rcon_response":resp})

@app.route("/api/orders/<oid>/reject",methods=["POST"])
def reject_order(oid):
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    with get_db() as con:
        con.execute("UPDATE orders SET status='rejected' WHERE id=?",(oid,)); con.commit()
    return jsonify({"ok":True})

@app.route("/api/orders/<oid>/reset",methods=["POST"])
def reset_order(oid):
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    with get_db() as con:
        con.execute("UPDATE orders SET status='pending',approved_at=NULL,expires_at=NULL WHERE id=?",(oid,)); con.commit()
    return jsonify({"ok":True})

@app.route("/api/orders/<oid>",methods=["DELETE"])
def delete_order(oid):
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    with get_db() as con:
        r=con.execute("SELECT check_file FROM orders WHERE id=?",(oid,)).fetchone()
        if r and r["check_file"]:
            try: os.remove(os.path.join(UPLOAD_FOLDER,r["check_file"]))
            except: pass
        con.execute("DELETE FROM orders WHERE id=?",(oid,)); con.commit()
    return jsonify({"ok":True})

@app.route("/api/orders/clear",methods=["DELETE"])
def clear_orders():
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    with get_db() as con:
        rows=con.execute("SELECT check_file FROM orders WHERE check_file IS NOT NULL").fetchall()
        for r in rows:
            try: os.remove(os.path.join(UPLOAD_FOLDER,r["check_file"]))
            except: pass
        con.execute("DELETE FROM orders"); con.commit()
    return jsonify({"ok":True})

# ── PROMOCODES ──
@app.route("/api/promocodes/validate", methods=["POST"])
def validate_promo():
    d = request.get_json() or {}
    code = d.get("code", "").strip().upper()
    if not code:
        return jsonify({"ok": False, "error": "Promokod kiritilmagan"}), 400
    with get_db() as con:
        row = con.execute("SELECT * FROM promocodes WHERE code=?", (code,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Promokod topilmadi"}), 404
    if not row["active"]:
        return jsonify({"ok": False, "error": "Promokod faol emas"}), 400
    if row["max_uses"] > 0 and row["used_count"] >= row["max_uses"]:
        return jsonify({"ok": False, "error": "Promokod limiti tugagan"}), 400
    return jsonify({"ok": True, "discount_percent": row["discount_percent"], "code": row["code"]})

@app.route("/api/promocodes", methods=["GET"])
def list_promos():
    if not check_auth(): return jsonify({"error": "Ruxsat yo'q"}), 403
    with get_db() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM promocodes ORDER BY created DESC").fetchall()]
    return jsonify({"ok": True, "promocodes": rows})

@app.route("/api/promocodes", methods=["POST"])
def create_promo():
    if not check_auth(): return jsonify({"error": "Ruxsat yo'q"}), 403
    d = request.get_json() or {}
    code = d.get("code", "").strip().upper()
    discount = int(d.get("discount_percent", 10))
    max_uses = int(d.get("max_uses", 0))
    if not code:
        return jsonify({"ok": False, "error": "Kod kiritilmagan"}), 400
    if discount < 1 or discount > 99:
        return jsonify({"ok": False, "error": "Chegirma 1–99% orasida bo'lishi kerak"}), 400
    with get_db() as con:
        try:
            con.execute("INSERT INTO promocodes (code,discount_percent,max_uses,used_count,active,created) VALUES (?,?,?,0,1,?)",
                        (code, discount, max_uses, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            con.commit()
        except sqlite3.IntegrityError:
            return jsonify({"ok": False, "error": "Bu promokod allaqachon mavjud"}), 400
    return jsonify({"ok": True, "message": "Promokod yaratildi"})

@app.route("/api/promocodes/<pcode>", methods=["PUT"])
def update_promo(pcode):
    if not check_auth(): return jsonify({"error": "Ruxsat yo'q"}), 403
    d = request.get_json() or {}
    with get_db() as con:
        if "active" in d:
            con.execute("UPDATE promocodes SET active=? WHERE code=?", (1 if d["active"] else 0, pcode.upper()))
        if "discount_percent" in d:
            con.execute("UPDATE promocodes SET discount_percent=? WHERE code=?", (int(d["discount_percent"]), pcode.upper()))
        if "max_uses" in d:
            con.execute("UPDATE promocodes SET max_uses=? WHERE code=?", (int(d["max_uses"]), pcode.upper()))
        con.commit()
    return jsonify({"ok": True})

@app.route("/api/promocodes/<pcode>", methods=["DELETE"])
def delete_promo(pcode):
    if not check_auth(): return jsonify({"error": "Ruxsat yo'q"}), 403
    with get_db() as con:
        con.execute("DELETE FROM promocodes WHERE code=?", (pcode.upper(),))
        con.commit()
    return jsonify({"ok": True})

# ── RCON ──
@app.route("/api/rcon/test",methods=["POST"])
def rcon_test():
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    try: return jsonify({"ok":True,"response":run_rcon("list")})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@app.route("/api/rcon/run",methods=["POST"])
def rcon_run():
    if not check_auth(): return jsonify({"error":"Ruxsat yo'q"}),403
    d=request.get_json() or {}; cmd=d.get("cmd","").strip()
    if not cmd: return jsonify({"ok":False,"error":"Buyruq bo'sh"}),400
    try: return jsonify({"ok":True,"response":run_rcon(cmd)})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

# ── SERVER STATUS ──
@app.route("/api/server-status")
def server_status():
    ip=request.args.get("ip","")
    if not ip: return jsonify({"online":False})
    try:
        from mcstatus import JavaServer
        st=JavaServer.lookup(ip).status()
        return jsonify({"online":True,"players_online":st.players.online,"players_max":st.players.max,"version":st.version.name})
    except Exception as e:
        return jsonify({"online":False,"error":str(e)})

if __name__=="__main__":
    print("="*55)
    print("  CrystalMC & MasterCraft — Backend v3")
    print("="*55)
    print("  Sayt:   http://localhost:5000")
    print("  Admin:  http://localhost:5000/admin")
    print("="*55)
    app.run(host="0.0.0.0",port=5000,debug=False)
