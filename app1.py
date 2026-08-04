import os, re, urllib.parse, urllib.request
from flask import Flask, request, jsonify, render_template_string, abort

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
*{
   
}

body{
   
}

.container{
    
}

h2{
  
}

button{
   
}

button:hover{
    
}

#status{
   
}
</style>
</head>

<body>

<div class="container">
    <h2>🎤 Voice Agent</h2>

    <button onclick="start()">Speak</button>

    <p id="status"></p>
</div>

<script>
const SR=window.SpeechRecognition||window.webkitSpeechRecognition,
s=document.getElementById("status");

async function send(cmd){
 let r=await fetch("/agent",{method:"POST",headers:{"Content-Type":"application/json"},
 body:JSON.stringify({text_command:cmd})});
 let d=await r.json();
 if(d.error)return s.innerText=d.error;
 s.innerText="Opening...";
 window.open(d.url,"_blank");
}

function start(){
 if(!SR)return alert("Use Chrome/Edge");
 let rec=new SR();
 rec.lang="en-US";
 rec.onresult=e=>send(e.results[0][0].transcript);
 rec.onerror=e=>s.innerText=e.error;
 rec.start();
}
</script>

</body>
</html>
"""


def find_first_video_id(query):
    try:
        req=urllib.request.Request(
            "https://www.youtube.com/results?search_query="+urllib.parse.quote_plus(query),
            headers={"User-Agent":"Mozilla/5.0","Accept-Language":"en-US","Cookie":"SOCS=CAI"})
        html=urllib.request.urlopen(req,timeout=5).read().decode()
        m=re.search(r'(?:"videoId":|/watch\?v=)"([A-Za-z0-9_-]{11})"',html)
        return m.group(1) if m else None
    except Exception as e:
        print("Scraper:",e); return None

def build_youtube_target(cmd):
    play="play" in cmd
    q=re.sub(r"(open youtube( and (play|search))?|play|search( for)?|on youtube)","",cmd).strip()
    if not q: return "https://www.youtube.com"
    if play:
        vid=find_first_video_id(q)
        if vid: return f"https://www.youtube.com/watch?v={vid}&autoplay=1"
    return "https://www.youtube.com/results?search_query="+urllib.parse.quote_plus(q)

def build_gmail_target(cmd):
    to=body=""
    if m:=re.search(r"to\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(and|type|saying|$))",cmd):
        to=m.group(1).replace(" ","")
        if "@" not in to: to+="@gmail.com"
    if m:=re.search(r"(type|saying)\s+(.*)",cmd):
        body=m.group(2).capitalize()
    if not(to or body): return "https://mail.google.com"
    return "https://mail.google.com/mail/u/0/?"+urllib.parse.urlencode(
        {"view":"cm","fs":"1","to":to,"body":body})

@app.route("/")
def home():
    return render_template_string(HTML)

@app.post("/agent")
def agent():
    data=request.get_json(silent=True)
    if not data or "text_command" not in data:
        abort(400,description="Missing command")
    cmd=data["text_command"].lower().strip()
    if "youtube" in cmd or "play" in cmd:
        return jsonify(action="open_tab",url=build_youtube_target(cmd))
    if any(k in cmd for k in ["gmail","email","mail"]):
        return jsonify(action="open_tab",url=build_gmail_target(cmd))
    return jsonify(error="Only YouTube and Gmail commands supported.")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",8000)))
