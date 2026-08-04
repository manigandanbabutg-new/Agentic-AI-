import os
import re
import urllib.parse
import urllib.request
from flask import Flask
from flask import abort
from flask import jsonify
from flask import render_template_string
from flask import request

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Voice Agent</title>
<style>
body {
  font-family: sans-serif;
  max-width: 500px;
  margin: 50px auto;
}
button {
  padding: 10px;
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 5px;
}
</style>
</head>
<body>
<h1>Voice Agent</h1>
<button onclick="startListening()">
🎤 Speak Now
</button>
<div id="status"></div>
<script>
const Speech = window.SpeechRecognition
  || window.webkitSpeechRecognition;

async function sendCommand(cmd) {
  document.getElementById('status').innerText = 
    'Processing...';
  const res = await fetch('/agent', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text_command: cmd
    })
  });
  const data = await res.json();
  if (data.error) return;
  window.open(data.url, '_blank');
}

function startListening() {
  if (!Speech) return;
  const rec = new Speech();
  rec.lang = 'en-US';
  rec.onresult = e => {
    sendCommand(e.results[0][0].transcript);
  };
  rec.start();
}
</script>
</body>
</html>
"""

def find_first_video_id(query):
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Cookie": "SOCS=CAI"
        }
        req = urllib.request.Request(
            url, 
            headers=headers
        )
        res = urllib.request.urlopen(
            req, 
            timeout=5
        )
        html = res.read().decode('utf-8')
        pattern = r'(?:"videoId":|/watch\?v=)"([a-zA-Z0-9_-]{11})"'
        match = re.search(pattern, html)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None

def build_youtube_target(command):
    wants_play = "play" in command
    clean = re.sub(
        r"(open youtube|play|search)", 
        "", 
        command
    ).strip()
    if not clean:
        return "https://www.youtube.com"
    if wants_play:
        vid = find_first_video_id(clean)
        if vid:
            return f"https://www.youtube.com/watch?v={vid}&autoplay=1"
    encoded = urllib.parse.quote_plus(clean)
    return f"https://www.youtube.com/results?search_query={encoded}"

def build_gmail_target(command):
    to = ""
    body = ""
    m1 = re.search(r"to\s+(\S+)", command)
    if m1:
        to = m1.group(1)
    m2 = re.search(r"saying\s+(.*)", command)
    if m2:
        body = m2.group(1)
    params = urllib.parse.urlencode({
        'view': 'cm',
        'to': to,
        'body': body
    })
    return f"https://mail.google.com/mail/u/0/?{params}"

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/agent", methods=["POST"])
def agent():
    data = request.get_json(silent=True)
    if not data:
        abort(400)
    cmd = data.get("text_command", "")
    cmd = cmd.lower()
    if "play" in cmd:
        url = build_youtube_target(cmd)
        return jsonify({"url": url})
    if "gmail" in cmd:
        url = build_gmail_target(cmd)
        return jsonify({"url": url})
    return jsonify({"error": "Unsupported"})

if __name__ == "__main__":
    app.run(port=8000)
