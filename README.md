# CrystalMC & MasterCraft — Donate Tizimi v2

## 📁 Fayllar
```
server.py         ← Backend (Flask)
donate.html       ← Asosiy sayt
admin.html        ← Admin panel (/admin)
requirements.txt  ← Python kutubxonalar
checks/           ← Chek rasmlari (avtomatik)
donate.db         ← Ma'lumotlar bazasi (avtomatik)
```

---

## ⚡ O'rnatish

```bash
pip install -r requirements.txt
python server.py
```

- Sayt: http://localhost:5000
- Admin: http://localhost:5000/admin

---

## 🔐 Admin kirish

| | |
|---|---|
| **Login** | `echoranger` |
| **Parol** | `shamsiddin1312` |

---

## 🔌 RCON Sozlash

1. Admin panelga kiring
2. **Sozlamalar** bo'limiga o'ting
3. RCON Host, Port, Parolni kiriting
4. "RCON Saqlash va Test" tugmasini bosing

`server.properties` fayliga qo'shing:
```
enable-rcon=true
rcon.port=25575
rcon.password=SIZNING_PAROLINGIZ
```

---

## 🔵 Google OAuth Ulash (ixtiyoriy)

### Qadam 1 — Google Cloud Console
1. https://console.cloud.google.com ga kiring
2. Yuqoridan **loyiha yarating** (New Project)
3. Loyiha nomini kiriting → Create

### Qadam 2 — OAuth ekranini sozlash
1. Chap menyu: **APIs & Services → OAuth consent screen**
2. User Type: **External** → Create
3. App name: `CrystalMC Admin` kiriting
4. Support email: emailingizni tanlang
5. Save and Continue (3 marta)

### Qadam 3 — Client ID yaratish
1. Chap menyu: **APIs & Services → Credentials**
2. **+ CREATE CREDENTIALS → OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Name: `CrystalMC Admin`
5. **Authorized JavaScript origins** ga qo'shing:
   - `http://localhost:5000`
   - (yoki serveringiz URL: `https://sizningdomen.uz`)
6. **CREATE** bosing
7. Chiqgan **Client ID** ni nusxalang

### Qadam 4 — Admin panelga kiriting
1. Admin panelga kiring → **Sozlamalar**
2. "Google Client ID" maydoniga yapishthiring
3. **Saqlash** bosing
4. Endi login sahifasida Google tugmasi faol bo'ladi!

---

## ⚡ Rank berish qanday ishlaydi

| Muddat | LuckPerms buyrug'i |
|--------|-------------------|
| Butun umrlik | `lp user NICK parent add rankname` |
| 30 kunlik | `lp user NICK parent addtemp rankname 30d` |
