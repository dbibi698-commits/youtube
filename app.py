import os, json, uuid, time, secrets, hashlib, hmac, mimetypes
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory, abort
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.abspath(__file__))
# Set DATA_DIR and UPLOADS_DIR to persistent storage paths when deploying.
DATA = os.environ.get("DATA_DIR", os.path.join(BASE, "data"))
UPLOADS = os.environ.get("UPLOADS_DIR", os.path.join(BASE, "uploads"))
os.makedirs(DATA, exist_ok=True)
os.makedirs(UPLOADS, exist_ok=True)
DB_FILE = os.path.join(DATA, "store.json")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "dbibi698@gmail.com").lower()
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-before-deploying")
ALLOWED = {"mp4", "webm", "mov", "m4v", "jpg", "jpeg", "png", "webp", "gif", "mp3", "wav", "ogg"}

app = Flask(__name__, static_folder="static")
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1 GB demo limit

def load_store():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "videos": {}, "comments": {}, "notifications": [], "events": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return {"users": {}, "videos": {}, "comments": {}, "notifications": [], "events": []}

def save_store(data):
    temp = DB_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp, DB_FILE)

def pw_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180000).hex()
    return salt + "$" + value

def pw_check(password, stored):
    try:
        salt, value = stored.split("$", 1)
        return hmac.compare_digest(pw_hash(password, salt).split("$", 1)[1], value)
    except Exception:
        return False

def current_user(store=None):
    store = store or load_store()
    email = session.get("email")
    return store["users"].get(email) if email else None

def public_user(user):
    if not user: return None
    return {k: user.get(k) for k in ("email","name","bio","avatar","created_at","blocked","is_admin")}

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            return jsonify(error="Please sign in first."), 401
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        u = current_user()
        if not u or not u.get("is_admin") or u.get("email","").lower() != ADMIN_EMAIL:
            return jsonify(error="Admin access only."), 403
        return fn(*args, **kwargs)
    return wrapped

def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED

def video_public(v, store):
    creator = store["users"].get(v.get("owner"))
    return {**v, "owner_name": (creator or {}).get("name", "Unknown creator"),
            "owner_avatar": (creator or {}).get("avatar", ""),
            "owner_blocked": bool((creator or {}).get("blocked"))}

@app.get("/")
def index():
    return send_from_directory("static", "index.html")

@app.get("/api/me")
def me():
    s = load_store()
    return jsonify(user=public_user(current_user(s)), admin_email=ADMIN_EMAIL)

@app.post("/api/register")
def register():
    d = request.get_json(silent=True) or {}
    email = str(d.get("email","")).strip().lower()
    password = str(d.get("password",""))
    name = str(d.get("name","")).strip()[:60]
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(error="Enter a valid email address."), 400
    if len(password) < 8:
        return jsonify(error="Password must be at least 8 characters."), 400
    if not name:
        return jsonify(error="Enter your channel name."), 400
    s = load_store()
    if email in s["users"]:
        return jsonify(error="This email is already registered. Please sign in."), 409
    s["users"][email] = {"email":email,"password":pw_hash(password),"name":name,"bio":"",
        "avatar":"","created_at":int(time.time()),"blocked":False,"is_admin":email == ADMIN_EMAIL,
        "subscriptions":[],"liked":[],"disliked":[],"history":[],"private_videos":[]}
    save_store(s); session["email"] = email
    return jsonify(user=public_user(s["users"][email]))

@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    email = str(d.get("email","")).strip().lower()
    s = load_store(); u = s["users"].get(email)
    if not u or not pw_check(str(d.get("password","")), u["password"]):
        return jsonify(error="Email or password is incorrect."), 401
    if u.get("blocked"):
        return jsonify(error="This account is blocked by the administrator."), 403
    session["email"] = email
    return jsonify(user=public_user(u))

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@app.get("/api/videos")
def videos():
    s = load_store()
    q = request.args.get("q","").lower().strip()
    category = request.args.get("category","").lower().strip()
    kind = request.args.get("kind","").lower().strip()
    sort = request.args.get("sort","latest")
    viewer = current_user(s)
    out = []
    for v in s["videos"].values():
        u = s["users"].get(v.get("owner"), {})
        if v.get("restricted") or u.get("blocked"): continue
        if v.get("private") and (not viewer or viewer["email"] != v.get("owner")): continue
        if q and q not in (v.get("title","")+" "+v.get("description","")+" "+v.get("tags","")+" "+v.get("owner_name","")).lower(): continue
        if category and v.get("category","").lower() != category: continue
        if kind and v.get("kind","long") != kind: continue
        out.append(video_public(v,s))
    out.sort(key=lambda x: x.get("created_at",0), reverse=(sort != "popular"))
    if sort == "popular": out.sort(key=lambda x: x.get("views",0), reverse=True)
    return jsonify(videos=out)

@app.post("/api/upload")
@login_required
def upload():
    s = load_store(); u = current_user(s)
    if not u or u.get("blocked"): return jsonify(error="Account unavailable."), 403
    f = request.files.get("video")
    if not f or not f.filename: return jsonify(error="Choose a video file."), 400
    if not allowed_file(f.filename): return jsonify(error="Unsupported file type."), 400
    title = request.form.get("title","").strip()[:120]
    if not title: return jsonify(error="Video title is required."), 400
    kind = request.form.get("kind","long")
    if kind not in ("short","long"): kind = "long"
    ext = secure_filename(f.filename).rsplit(".",1)[-1].lower()
    vid = uuid.uuid4().hex
    filename = vid + "." + ext
    f.save(os.path.join(UPLOADS, filename))
    thumb_name = ""
    thumb = request.files.get("thumbnail")
    if thumb and thumb.filename and allowed_file(thumb.filename):
        te = secure_filename(thumb.filename).rsplit(".",1)[-1].lower()
        thumb_name = vid + "_thumb." + te
        thumb.save(os.path.join(UPLOADS, thumb_name))
    v = {"id":vid,"owner":u["email"],"title":title,"description":request.form.get("description","")[:5000],
        "tags":request.form.get("tags","")[:500],"category":request.form.get("category","Other")[:60],
        "kind":kind,"filename":filename,"thumbnail":thumb_name,"private":request.form.get("private")=="true",
        "restricted":False,"created_at":int(time.time()),"views":0,"likes":[],"dislikes":[],"subtitles":request.form.get("captions","")[:10000],
        "duration":"","quality":"Original"}
    s["videos"][vid] = v
    for email, user in s["users"].items():
        if email != u["email"] and u["email"] in user.get("subscriptions",[]):
            s["notifications"].append({"id":uuid.uuid4().hex,"to":email,"text":u["name"]+" uploaded: "+title,"video_id":vid,"created_at":int(time.time()),"read":False})
    save_store(s)
    return jsonify(video=video_public(v,s))

@app.get("/media/<path:filename>")
def media(filename):
    return send_from_directory(UPLOADS, filename, conditional=True)

@app.get("/api/video/<vid>")
def get_video(vid):
    s=load_store(); v=s["videos"].get(vid)
    if not v or v.get("restricted"): return jsonify(error="Video not found."),404
    u=s["users"].get(v.get("owner"),{})
    if u.get("blocked"): return jsonify(error="Creator unavailable."),404
    viewer=current_user(s)
    if v.get("private") and (not viewer or viewer["email"] != v.get("owner")): return jsonify(error="This video is private."),403
    v["views"] = v.get("views",0)+1
    if viewer:
        viewer["history"] = ([vid]+[x for x in viewer.get("history",[]) if x != vid])[:100]
    save_store(s)
    return jsonify(video=video_public(v,s), comments=s["comments"].get(vid,[]), user=public_user(viewer))

@app.post("/api/video/<vid>/react")
@login_required
def react(vid):
    s=load_store(); u=current_user(s); v=s["videos"].get(vid)
    if not v: return jsonify(error="Video not found."),404
    d=request.get_json(silent=True) or {}; action=d.get("action")
    if action not in ("like","dislike"): return jsonify(error="Invalid reaction."),400
    arr="likes" if action=="like" else "dislikes"; other="dislikes" if arr=="likes" else "likes"
    if u["email"] in v[arr]: v[arr].remove(u["email"])
    else:
        v[arr].append(u["email"])
        if u["email"] in v[other]: v[other].remove(u["email"])
        owner=v["owner"]
        if owner != u["email"]: s["notifications"].append({"id":uuid.uuid4().hex,"to":owner,"text":u["name"]+" "+action+"d your video: "+v["title"],"video_id":vid,"created_at":int(time.time()),"read":False})
    save_store(s); return jsonify(likes=len(v["likes"]),dislikes=len(v["dislikes"]))

@app.post("/api/video/<vid>/comment")
@login_required
def comment(vid):
    s=load_store(); u=current_user(s)
    if vid not in s["videos"]: return jsonify(error="Video not found."),404
    d=request.get_json(silent=True) or {}; body=str(d.get("text","")).strip()[:2000]
    if not body: return jsonify(error="Write a comment first."),400
    c={"id":uuid.uuid4().hex,"email":u["email"],"name":u["name"],"avatar":u.get("avatar",""),"text":body,"created_at":int(time.time())}
    s["comments"].setdefault(vid,[]).append(c)
    owner=s["videos"][vid]["owner"]
    if owner != u["email"]: s["notifications"].append({"id":uuid.uuid4().hex,"to":owner,"text":u["name"]+" commented on: "+s["videos"][vid]["title"],"video_id":vid,"created_at":int(time.time()),"read":False})
    save_store(s); return jsonify(comment=c)

@app.post("/api/subscribe/<email>")
@login_required
def subscribe(email):
    s=load_store(); u=current_user(s); email=email.lower()
    if email not in s["users"]: return jsonify(error="Channel not found."),404
    if email==u["email"]: return jsonify(error="You cannot subscribe to your own channel."),400
    subs=u.setdefault("subscriptions",[])
    if email in subs: subs.remove(email); state=False
    else:
        subs.append(email); state=True
        s["notifications"].append({"id":uuid.uuid4().hex,"to":email,"text":u["name"]+" subscribed to your channel","created_at":int(time.time()),"read":False})
    save_store(s); return jsonify(subscribed=state,count=sum(email in x.get("subscriptions",[]) for x in s["users"].values()))

@app.get("/api/channel/<email>")
def channel(email):
    s=load_store(); email=email.lower(); u=s["users"].get(email)
    if not u or u.get("blocked"): return jsonify(error="Channel not found."),404
    vids=[video_public(v,s) for v in s["videos"].values() if v["owner"]==email and (not v.get("private") or (current_user(s) or {}).get("email")==email)]
    vids.sort(key=lambda x:x["created_at"],reverse=True)
    return jsonify(channel=public_user(u),videos=vids,subscribers=sum(email in x.get("subscriptions",[]) for x in s["users"].values()),
                   subscribed=bool(current_user(s) and email in current_user(s).get("subscriptions",[])))


@app.get("/api/channels")
def channels():
    """Search public channels by channel name or email."""
    s = load_store()
    q = request.args.get("q", "").strip().lower()
    rows = []
    for u in s["users"].values():
        if u.get("blocked"):
            continue
        if q and q not in (u.get("name", "") + " " + u.get("email", "")).lower():
            continue
        rows.append({
            "email": u.get("email"),
            "name": u.get("name"),
            "bio": u.get("bio", ""),
            "avatar": u.get("avatar", ""),
            "subscribers": sum(u.get("email") in x.get("subscriptions", []) for x in s["users"].values()),
            "video_count": sum(v.get("owner") == u.get("email") and not v.get("restricted") for v in s["videos"].values())
        })
    rows.sort(key=lambda x: (x["subscribers"], x["name"].lower()), reverse=True)
    return jsonify(channels=rows[:100])

@app.patch("/api/video/<vid>")
@login_required
def edit_own_video(vid):
    """Edit metadata for a video owned by the signed-in user."""
    s = load_store()
    u = current_user(s)
    v = s["videos"].get(vid)
    if not v:
        return jsonify(error="Video not found."), 404
    if v.get("owner") != u["email"] and not u.get("is_admin"):
        return jsonify(error="You can only edit your own videos."), 403
    d = request.get_json(silent=True) or {}
    if "title" in d:
        title = str(d["title"]).strip()
        if not title:
            return jsonify(error="Title cannot be empty."), 400
        v["title"] = title[:120]
    for key, limit in (("description", 5000), ("tags", 500), ("category", 60)):
        if key in d:
            v[key] = str(d[key])[:limit]
    if "private" in d:
        v["private"] = bool(d["private"])
    if "captions" in d:
        v["subtitles"] = str(d["captions"])[:10000]
    save_store(s)
    return jsonify(video=video_public(v, s))

@app.delete("/api/video/<vid>")
@login_required
def delete_own_video(vid):
    """Delete a video owned by the signed-in user."""
    s = load_store()
    u = current_user(s)
    v = s["videos"].get(vid)
    if not v:
        return jsonify(error="Video not found."), 404
    if v.get("owner") != u["email"] and not u.get("is_admin"):
        return jsonify(error="You can only delete your own videos."), 403
    s["videos"].pop(vid, None)
    s["comments"].pop(vid, None)
    for name in (v.get("filename"), v.get("thumbnail")):
        if name:
            try:
                os.remove(os.path.join(UPLOADS, name))
            except OSError:
                pass
    save_store(s)
    return jsonify(ok=True)

@app.post("/api/profile")
@login_required
def profile():
    s=load_store(); u=current_user(s); d=request.form
    u["name"]=d.get("name",u["name"]).strip()[:60] or u["name"]
    u["bio"]=d.get("bio",u.get("bio",""))[:500]
    f=request.files.get("avatar")
    if f and f.filename and allowed_file(f.filename):
        ext=secure_filename(f.filename).rsplit(".",1)[-1].lower()
        name="avatar_"+hashlib.sha256(u["email"].encode()).hexdigest()[:20]+"."+ext
        f.save(os.path.join(UPLOADS,name)); u["avatar"]="/media/"+name
    save_store(s); return jsonify(user=public_user(u))

@app.post("/api/password")
@login_required
def password():
    s=load_store(); u=current_user(s); d=request.get_json(silent=True) or {}
    if not pw_check(str(d.get("old","")),u["password"]): return jsonify(error="Current password is incorrect."),400
    if len(str(d.get("new",""))) < 8: return jsonify(error="New password must be at least 8 characters."),400
    u["password"]=pw_hash(str(d["new"])); save_store(s); return jsonify(ok=True)

@app.get("/api/notifications")
@login_required
def notifications():
    s=load_store(); email=current_user(s)["email"]
    return jsonify(notifications=sorted([n for n in s["notifications"] if n.get("to")==email],key=lambda x:x["created_at"],reverse=True)[:100])

@app.post("/api/notifications/read")
@login_required
def read_notifications():
    s=load_store(); email=current_user(s)["email"]
    for n in s["notifications"]:
        if n.get("to")==email: n["read"]=True
    save_store(s); return jsonify(ok=True)

@app.get("/api/history")
@login_required
def history():
    s=load_store(); u=current_user(s)
    return jsonify(videos=[video_public(s["videos"][i],s) for i in u.get("history",[]) if i in s["videos"]])

@app.get("/api/admin/overview")
@admin_required
def admin_overview():
    s=load_store()
    return jsonify(users=[public_user(u) for u in s["users"].values()],
                   videos=[video_public(v,s) for v in s["videos"].values()],
                   total_views=sum(v.get("views",0) for v in s["videos"].values()))

@app.post("/api/admin/user/<email>/block")
@admin_required
def admin_block(email):
    s=load_store(); u=s["users"].get(email.lower())
    if not u: return jsonify(error="User not found."),404
    if u.get("is_admin"): return jsonify(error="Cannot block the admin account."),400
    u["blocked"]=not u.get("blocked",False); save_store(s)
    return jsonify(blocked=u["blocked"])

@app.post("/api/admin/video/<vid>/restrict")
@admin_required
def admin_restrict(vid):
    s=load_store(); v=s["videos"].get(vid)
    if not v: return jsonify(error="Video not found."),404
    v["restricted"]=not v.get("restricted",False); save_store(s)
    return jsonify(restricted=v["restricted"])

@app.delete("/api/admin/video/<vid>")
@admin_required
def admin_delete_video(vid):
    s=load_store(); v=s["videos"].pop(vid,None)
    if not v: return jsonify(error="Video not found."),404
    for name in (v.get("filename"),v.get("thumbnail")):
        if name:
            try: os.remove(os.path.join(UPLOADS,name))
            except OSError: pass
    s["comments"].pop(vid,None); save_store(s); return jsonify(ok=True)

@app.get("/api/admin/events")
@admin_required
def admin_events():
    s=load_store()
    return jsonify(events=[{"email":u["email"],"name":u["name"],"blocked":u.get("blocked",False)} for u in s["users"].values()],
                   uploads=[{"id":v["id"],"owner":v["owner"],"title":v["title"],"created_at":v["created_at"]} for v in s["videos"].values()])

@app.get("/api/health")
def health():
    return jsonify(ok=True, app="Murshid Developer", storage="JSON file", admin_email=ADMIN_EMAIL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","5000")), debug=False, threaded=True)
