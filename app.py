import base64, json, os, subprocess, uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, unquote

CONFIG_PATH = "/app/config.json"
USERS_PATH = "/app/users.json"
ENV_DOMAIN = os.environ.get("DOMAIN", "").strip()

def load_users():
    return json.load(open(USERS_PATH)) if os.path.exists(USERS_PATH) else []

def save_users(users):
    json.dump(users, open(USERS_PATH, "w"), indent=2)
    data = json.load(open(CONFIG_PATH))
    u_cli = [{"id": u["id"], "email": u["name"]} for u in users]
    t_cli = [{"password": u["id"], "email": u["name"]} for u in users]
    for ib in data["inbounds"]:
        ib["settings"]["clients"] = t_cli if ib.get("protocol") == "trojan" else u_cli
    json.dump(data, open(CONFIG_PATH, "w"), indent=2)
    subprocess.run(["pkill", "-x", "xray"])

def make_vmess(uid, dom, port, net, path, tls, ps):
    obj = {"v":"2","ps":ps,"add":dom,"port":str(port),"id":uid,"aid":"0","scy":"auto","net":net,"type":"auto" if net=="xhttp" else "none","host":dom,"path":path,"tls":"tls" if tls else "","sni":dom if tls else ""}
    return "vmess://" + base64.b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode()

class Handler(BaseHTTPRequestHandler):
    def get_saved_domain(self):
        ch = self.headers.get("Cookie", "")
        if ch:
            c = SimpleCookie(); c.load(ch)
            if "user_domain" in c and unquote(c["user_domain"].value).strip():
                return unquote(c["user_domain"].value).strip()
        if ENV_DOMAIN: return ENV_DOMAIN
        host = self.headers.get("Host", "").split(":")[0].strip().lower()
        return host if host and not host.endswith(".railway.app") and host not in ("127.0.0.1", "localhost") else ""
    def do_GET(self):
        users, saved_dom, rows = load_users(), self.get_saved_domain(), ""
        for u in reversed(users):
            uid, name, dom = u["id"], u["name"], u["domain"]
            vl = [f"vless://{uid}@{dom}:{p}?encryption=none&security={'tls&sni='+dom if p==443 else 'none'}&type={t}&host={dom}&path=%2F{pa}{'&mode=auto' if t=='xhttp' else ''}#{name}-VLESS-{lb}-{p}" for p in (443,80) for t,pa,lb in [("xhttp","xhttp","XHTTP"),("httpupgrade","httpup","HTTPUp"),("ws","vless","WS")]]
            vm = [make_vmess(uid, dom, p, t, "/"+pa, p==443, f"{name}-VMess-{lb}-{p}") for p in (443,80) for t,pa,lb in [("xhttp","vmess-xhttp","XHTTP"),("httpupgrade","vmess-httpup","HTTPUp"),("ws","vmess","WS")]]
            tr = [f"trojan://{uid}@{dom}:{p}?security={'tls&sni='+dom if p==443 else 'none'}&type={t}&host={dom}&path=%2F{pa}{'&mode=auto' if t=='xhttp' else ''}#{name}-Trojan-{lb}-{p}" for p in (443,80) for t,pa,lb in [("xhttp","trojan-xhttp","XHTTP"),("httpupgrade","trojan-httpup","HTTPUp"),("ws","trojan","WS")]]
            rows += f"""<div class="card"><div class="top"><b>{name}</b><span class="tag">{dom}</span></div><small>{uid}</small>
            <div class="proto">VLESS</div><div class="lbl">Port TLS 443</div><div class="btns"><button onclick="copy('{vl[0]}')">XHTTP 443</button><button onclick="copy('{vl[1]}')">HTTPUp 443</button><button onclick="copy('{vl[2]}')">WS 443</button></div>
            <div class="lbl">Port Non-TLS 80</div><div class="btns ntls"><button onclick="copy('{vl[3]}')">XHTTP 80</button><button onclick="copy('{vl[4]}')">HTTPUp 80</button><button onclick="copy('{vl[5]}')">WS 80</button></div>
            <div class="proto vm">VMess</div><div class="lbl">Port TLS 443</div><div class="btns vm-btn"><button onclick="copy('{vm[0]}')">XHTTP 443</button><button onclick="copy('{vm[1]}')">HTTPUp 443</button><button onclick="copy('{vm[2]}')">WS 443</button></div>
            <div class="lbl">Port Non-TLS 80</div><div class="btns vm-ntls"><button onclick="copy('{vm[3]}')">XHTTP 80</button><button onclick="copy('{vm[4]}')">HTTPUp 80</button><button onclick="copy('{vm[5]}')">WS 80</button></div>
            <div class="proto tr">Trojan</div><div class="lbl">Port TLS 443</div><div class="btns tr-btn"><button onclick="copy('{tr[0]}')">XHTTP 443</button><button onclick="copy('{tr[1]}')">HTTPUp 443</button><button onclick="copy('{tr[2]}')">WS 443</button></div>
            <div class="lbl">Port Non-TLS 80</div><div class="btns tr-ntls"><button onclick="copy('{tr[3]}')">XHTTP 80</button><button onclick="copy('{tr[4]}')">HTTPUp 80</button><button onclick="copy('{tr[5]}')">WS 80</button></div></div>"""
        if not rows: rows = '<div class="empty">Belum ada akun terdaftar. Silakan buat akun di atas.</div>'
        html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Generator Akun Multi-Protokol</title>
        <style>body{{background:#0f172a;color:#f8fafc;font-family:sans-serif;padding:16px;max-width:540px;margin:auto}}.box,.card{{background:#1e293b;padding:14px;border-radius:12px;margin-bottom:12px}}input{{width:100%;padding:11px;border-radius:8px;border:none;margin-bottom:10px;box-sizing:border-box}}.add{{width:100%;padding:11px;border-radius:8px;border:none;background:#22c55e;color:#fff;font-weight:bold}}.empty{{text-align:center;color:#94a3b8;padding:20px;font-size:13px}}.top{{display:flex;justify-content:space-between;align-items:center;gap:8px}}.tag{{background:#334155;color:#38bdf8;font-size:11px;padding:3px 8px;border-radius:6px;word-break:break-all}}small{{color:#94a3b8;word-break:break-all;display:block;margin:6px 0}}.proto{{font-size:12px;font-weight:bold;color:#60a5fa;margin-top:12px;padding-top:8px;border-top:1px solid #334155}}.proto.vm{{color:#c084fc}}.proto.tr{{color:#fb923c}}.lbl{{font-size:11px;color:#cbd5e1;margin:6px 0 4px}}.btns{{display:flex;gap:6px}}.btns button{{flex:1;padding:8px;border:none;border-radius:6px;background:#3b82f6;color:#fff;font-size:12px}}.ntls button{{background:#0ea5e9}}.vm-btn button{{background:#9333ea}}.vm-ntls button{{background:#a855f7}}.tr-btn button{{background:#ea580c}}.tr-ntls button{{background:#f97316}}</style></head>
        <body><h3>Generator Akun VLESS / VMess / Trojan</h3><div class="box"><form method="POST" action="/add" onsubmit="saveDom()"><input type="text" name="name" maxlength="20" placeholder="Nama akun (misal: user1)" required><input type="text" id="domInput" name="domain" maxlength="60" value="{saved_dom}" placeholder="Domain Zero Trust (misal: sub.domain.com)" required><button class="add" type="submit">+ Buat Akun</button></form></div>{rows}
        <script>(function(){{var el=document.getElementById('domInput');if(!el.value){{var s=localStorage.getItem('vless_user_domain');if(s)el.value=s;}}}})();function saveDom(){{var v=document.getElementById('domInput').value.trim();if(v)localStorage.setItem('vless_user_domain',v);}}function copy(t){{if(navigator.clipboard)navigator.clipboard.writeText(t).then(()=>alert('Link berhasil disalin!')).catch(()=>fb(t));else fb(t);}}function fb(t){{var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');document.body.removeChild(a);alert('Link berhasil disalin!');}}</script></body></html>"""
        self.send_response(200); self.send_header("Content-type", "text/html"); self.end_headers(); self.wfile.write(html.encode())

    def do_POST(self):
        body = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
        users, dom = load_users(), ""
        if self.path == "/add":
            name = "".join(c for c in body.get("name", ["user"])[0] if c.isalnum() or c in "-_")[:20] or "user"
            dom = "".join(c for c in body.get("domain", [""])[0].strip().lower().replace("https://","").replace("http://","").split("/")[0] if c.isalnum() or c in ".-")[:60]
            if dom: users.append({"id": str(uuid.uuid4()), "name": name, "domain": dom}); save_users(users)
        self.send_response(302)
        if dom: self.send_header("Set-Cookie", f"user_domain={quote(dom)}; Path=/; Max-Age=31536000")
        self.send_header("Location", "/"); self.end_headers()

HTTPServer(("0.0.0.0", 2053), Handler).serve_forever()
