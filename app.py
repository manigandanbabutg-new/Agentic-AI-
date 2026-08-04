import os, re, urllib.parse, urllib.request
from flask import Flask, request, jsonify, render_template_string, abort

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head><title>Voice Agent</title>
<style>
body{font-family:Arial;max-width:550px;margin:60px auto}
button{padding:10px 18px;background:#4f46e5;color:#fff;border:0;border-radius:6px;cursor:pointer}
#transcript{margin-top:20px;font-style:italic}#status{font-size:13px;color:#555;word-break:break-all}
</style></head>
<body>
<h2>🎤 Voice Command Agent</h2>
<button onclick="start()">Speak (YouTube / Gmail)</button>
<div id="transcript"></div><div id="status"></div>
<script>
const t=document.getElementById("transcript"),s=document.getElementById("status");
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;

async function send(cmd){
    t.innerText='"'+cmd+'"'; s.innerText="Processing...";
    let r=await fetch("/agent",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({text_command:cmd})});
    let d=await r.json();
    if(d.error) return s.innerText=d.error;
    s.innerText="Opening: "+d.url;
    window.open(d.url,"_blank");
}

function start(){
    if(!SR) return alert("Use Chrome or Edge");
    let rec=new SR();
    rec.lang="en-US";
    rec.onresult=e=>send(e.results[0][0].transcript);
    rec.onerror=e=>s.innerText=e.error;
    rec.start();
}
</script></body></html>
"""

def first_video(query):
    try:
        url="https://www.youtube.com/results?search_query="+urllib.parse.quote_plus(query)
        req=urllib.request.Request(url,headers={
            "User-Agent":"Mozilla/5.0",
            "Accept-Language":"en-US",
            "Cookie":"SOCS=CAI"
        })
        html=urllib.request.urlopen(req,timeout=5).read().decode()
        m=re.search(r'(?:"videoId":|/watch\?v=)"([\\w-]{11})"',html)
        return m.group(1) if m else None
    except:
        return None

def youtube(cmd):
    play="play" in cmd
    q=re.sub(r"(open youtube( and (play|search))?|play|search( for)?|on youtube)","",cmd).strip()
    if not q: return "https://www.youtube.com"
    if play:
        vid=first_video(q)
        if vid: return f"https://www.youtube.com/watch?v={vid}&autoplay=1"
    return "https://www.youtube.com/results?search_query="+urllib.parse.quote_plus(q)

def gmail(cmd):
    to=body=""
    m=re.search(r"to\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(and|type|saying|$))",cmd)
    if m:
        to=m.group(1).replace(" ","")
        if "@" not in to: to+="@gmail.com"
    m=re.search(r"(type|saying)\s+(.*)",cmd)
    if m: body=m.group(2).capitalize()
    if not(to or body): return "https://mail.google.com"
    return "https://mail.google.com/mail/u/0/?"+urllib.parse.urlencode({
        "view":"cm","fs":"1","to":to,"body":body
    })

@app.route("/")
def home():
    return render_template_string(HTML)

@app.post("/agent")
def agent():
    data=request.get_json(silent=True)
    if not data or "text_command" not in data:
        abort(400,"Missing command")
    cmd=data["text_command"].lower().strip()
    if "youtube" in cmd or "play" in cmd:
        return jsonify(action="open_tab",url=youtube(cmd))
    if any(x in cmd for x in ["gmail","mail","email"]):
        return jsonify(action="open_tab",url=gmail(cmd))
    return jsonify(error="Only YouTube and Gmail commands supported.")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",8000)))
