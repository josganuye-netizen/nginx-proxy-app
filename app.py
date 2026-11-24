import json, os, subprocess, uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, unquote

CONFIG_PATH = "/app/config.json"
USERS_PATH = "/app/users.json"
ENV_DOMAIN = os.environ.get("DOMAIN", "").strip()

def load_users():
    if os.path.exists(USERS_PATH):
        with open(USERS_PATH, "r") as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_PATH, "w") as f:
        json.dump(users, f, indent=2)
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    clean_clients = [{"id": u["id"], "email": u["name"]} for u in users]
    for ib in data["inbounds"]:
        ib["settings"]["clients"] = clean_clients
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)
    subprocess.run(["pkill", "-x", "xray"])

class Handler(BaseHTTPRequestHandler):
    def get_saved_domain(self):
        cookie_header = self.headers.get("Cookie", "")
        if cookie_header:
            c = SimpleCookie()
            c.load(cookie_header)
            if "user_domain" in c:
                val = unquote(c["user_domain"].value).strip()
                if val:
                    return val
        if ENV_DOMAIN:
            return ENV_DOMAIN
        host = self.headers.get("Host", "").split(":")[0].strip().lower()
        if host and not host.endswith(".railway.app") and host not in ("127.0.0.1", "localhost"):
            return host
        return ""

    def do_GET(self):
        users = load_users()
        saved_dom = self.get_saved_domain()
        rows = ""
        for u in reversed(users):
            uid = u["id"]
            name = u["name"]
            dom = u["domain"]
            l_xhttp_tls = f"vless://{uid}@{dom}:443?encryption=none&security=tls&sni={dom}&type=xhttp&host={dom}&path=%2Fxhttp&mode=auto#{name}-XHTTP-443"
            l_httpup_tls = f"vless://{uid}@{dom}:443?encryption=none&security=tls&sni={dom}&type=httpupgrade&host={dom}&path=%2Fhttpup#{name}-HTTPUp-443"
            l_ws_tls = f"vless://{uid}@{dom}:443?encryption=none&security=tls&sni={dom}&type=ws&host={dom}&path=%2Fvless#{name}-WS-443"
            l_xhttp_80 = f"vless://{uid}@{dom}:80?encryption=none&security=none&type=xhttp&host={dom}&path=%2Fxhttp&mode=auto#{name}-XHTTP-80"
            l_httpup_80 = f"vless://{uid}@{dom}:80?encryption=none&security=none&type=httpupgrade&host={dom}&path=%2Fhttpup#{name}-HTTPUp-80"
            l_ws_80 = f"vless://{uid}@{dom}:80?encryption=none&security=none&type=ws&host={dom}&path=%2Fvless#{name}-WS-80"

            rows += f"""
            <div class="card">
              <div class="top"><b>{name}</b><span class="tag">{dom}</span></div>
              <small>{uid}</small>
              <div class="lbl">Port TLS 443</div>
              <div class="btns">
                <button onclick="copy('{l_xhttp_tls}')">XHTTP 443</button>
                <button onclick="copy('{l_httpup_tls}')">HTTPUp 443</button>
                <button onclick="copy('{l_ws_tls}')">WS 443</button>
              </div>
              <div class="lbl">Port Non-TLS 80</div>
              <div class="btns ntls">
                <button onclick="copy('{l_xhttp_80}')">XHTTP 80</button>
                <button onclick="copy('{l_httpup_80}')">HTTPUp 80</button>
                <button onclick="copy('{l_ws_80}')">WS 80</button>
              </div>
            </div>"""

        if not rows:
            rows = '<div class="empty">Belum ada akun terdaftar. Silakan buat akun di atas.</div>'

        html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Generator Akun VLESS</title>
        <style>body{{background:#0f172a;color:#f8fafc;font-family:sans-serif;padding:16px;max-width:540px;margin:auto}}
        .box{{background:#1e293b;padding:16px;border-radius:12px;margin-bottom:16px}}
        input{{width:100%;padding:11px;border-radius:8px;border:none;margin-bottom:10px;box-sizing:border-box}}
        .add{{width:100%;padding:11px;border-radius:8px;border:none;background:#22c55e;color:#fff;font-weight:bold;font-size:14px}}
        .card{{background:#1e293b;padding:14px;border-radius:12px;margin-bottom:10px}}
        .empty{{text-align:center;color:#94a3b8;padding:20px;font-size:13px}}
        .top{{display:flex;justify-content:space-between;align-items:center;gap:8px}}
        .tag{{background:#334155;color:#38bdf8;font-size:11px;padding:3px 8px;border-radius:6px;word-break:break-all}}
        small{{color:#94a3b8;word-break:break-all;display:block;margin:6px 0}}
        .lbl{{font-size:11px;color:#cbd5e1;margin:8px 0 4px}}
        .btns{{display:flex;gap:6px}}.btns button{{flex:1;padding:8px;border:none;border-radius:6px;background:#3b82f6;color:#fff;font-size:12px}}
        .ntls button{{background:#0ea5e9}}</style></head>
        <body><h3>Generator Akun VLESS</h3>
        <div class="box"><form method="POST" action="/add" onsubmit="saveDom()">
        <input type="text" name="name" maxlength="20" placeholder="Nama akun (misal: user1)" required>
        <input type="text" id="domInput" name="domain" maxlength="60" value="{saved_dom}" placeholder="Domain Zero Trust (misal: sub.domain.com)" required>
        <button class="add" type="submit">+ Buat Akun</button></form></div>
        {rows}
        <script>
        (function(){{
          var el=document.getElementById('domInput');
          if(!el.value){{
            var saved=localStorage.getItem('vless_user_domain');
            if(saved){{el.value=saved;}}
          }}
        }})();
        function saveDom(){{
          var val=document.getElementById('domInput').value.trim();
          if(val){{localStorage.setItem('vless_user_domain',val);}}
        }}
        function copy(t){{
          if(navigator.clipboard){{navigator.clipboard.writeText(t).then(()=>alert('Link berhasil disalin!')).catch(()=>fallback(t));}}
          else{{fallback(t);}}
        }}
        function fallback(t){{
          var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');document.body.removeChild(a);alert('Link berhasil disalin!');
        }}
        </script>
        </body></html>"""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = parse_qs(self.rfile.read(length).decode())
        users = load_users()
        dom = ""
        if self.path == "/add":
            name = "".join(c for c in body.get("name", ["user"])[0] if c.isalnum() or c in "-_")[:20] or "user"
            raw_dom = body.get("domain", [""])[0].strip().lower()
            raw_dom = raw_dom.replace("https://", "").replace("http://", "").split("/")[0]
            dom = "".join(c for c in raw_dom if c.isalnum() or c in ".-")[:60]
            if dom:
                users.append({"id": str(uuid.uuid4()), "name": name, "domain": dom})
                save_users(users)
        self.send_response(302)
        if dom:
            self.send_header("Set-Cookie", f"user_domain={quote(dom)}; Path=/; Max-Age=31536000")
        self.send_header("Location", "/")
        self.end_headers()

HTTPServer(("0.0.0.0", 2053), Handler).serve_forever()
