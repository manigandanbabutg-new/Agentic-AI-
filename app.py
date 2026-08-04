import os, re, urllib.parse, urllib.request
from flask import Flask, abort, jsonify, render_template_string, request
 
app = Flask(__name__)
HTML = """<!DOCTYPE html><html><head><title>Voice Agent</title>
<style>body{font-family:Arial;max-width:500px;margin:60px auto}button{padding:10px 18px;background:#4f46e5;color:#fff;border:0;border-radius:6px}#t{margin-top:20px;font-style:italic}#s{font-size:13px;color:#555;word-break:break-all}</style></head>
<body><h1>Voice Command Agent</h1><button onclick="go()">🎤 Speak</button>
<div id="t">Waiting...</div><div id="s"></div>
<script>
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
async function send(c){t.innerText='"'+c+'"';s.innerText='Processing...';
const d=await(await fetch('/agent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text_command:c})})).json();
s.innerText='Opening: '+d.url;window.open(d.url,'_blank');}
function go(){if(!SR)return alert('Use Chrome/Edge');const r=new SR();r.lang='en-US';
r.onresult=e=>send(e.results[0][0].transcript);r.onerror=e=>s.innerText='Error: '+e.error;r.start();}
</script></body></html>"""
 
def get_vid(q):
    try:
        req = urllib.request.Request(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}", headers={"User-Agent": "Mozilla/5.0"})
        ids = re.findall(r"\"videoId\":\"([^\"]+)\"", urllib.request.urlopen(req, timeout=5).read().decode())
        return ids[0] if ids else None
    except Exception:
        return None
 
@app.route("/")
def home(): return render_template_string(HTML)
 
@app.route("/agent", methods=["POST"])
def agent():
    d = request.get_json(silent=True)
    if not d or "text_command" not in d: abort(400)
    cmd = d["text_command"].strip().lower()
    if "youtube" in cmd:
        q = cmd
        for p in ["open youtube and search", "open youtube and play", "open youtube", "search for", "search", "and play", "play", "on youtube"]: q = q.replace(p, "")
        q = q.strip()
        target = "https://www.youtube.com" if not q else (f"https://www.youtube.com/watch?v={v}&autoplay=1" if (v := get_vid(q)) else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}")
    elif any(k in cmd for k in ["gmail", "email", "mail", "message"]):
        to, body = "", ""
        if tm := re.search(r"(?:update|send|mail|message)?\s*to\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(?:and|type|write|saying|with|content|that|message|$))", cmd):
            c = tm.group(1).strip().replace(" at ", "@").replace(" dot ", ".").replace(" ", "")
            to = c if "@" in c else f"{c}@gmail.com"
        if bm := re.search(r"(?:type|write|saying|content|message|that)\s+(.*)", cmd):
            body = (bm.group(1).strip() or "")
            body = body[0].upper() + body[1:] if body else ""
        target = f"https://mail.google.com/mail/u/0/?view=cm&fs=1&to={urllib.parse.quote(to)}&body={urllib.parse.quote(body)}" if to or body else "https://mail.google.com"
    else:
        target = f"https://www.google.com/search?q={urllib.parse.quote_plus(cmd)}"
    return jsonify({"action": "open_tab", "url": target})
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
