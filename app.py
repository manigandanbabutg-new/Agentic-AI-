import os
import re
import urllib.parse

from flask import Flask, abort, jsonify, render_template_string, request

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><title>Voice Agent</title>
<style>
body{font-family:Arial,sans-serif;max-width:560px;margin:60px auto}
button{padding:10px 18px;background:#4f46e5;color:#fff;border:0;border-radius:6px;cursor:pointer}
#transcript{margin-top:20px;font-style:italic}
#status{font-size:13px;color:#555;word-break:break-all}
</style>
</head>
<body>
<h1>Voice Command Agent</h1>
<button onclick="startListening()">🎤 Speak (YouTube / Gmail)</button>
<div id="transcript"></div>
<div id="status"></div>
<script>
const transcriptEl = document.getElementById('transcript');
const statusEl = document.getElementById('status');
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

async function sendCommand(command) {
    transcriptEl.innerText = '"' + command + '"';
    statusEl.innerText = 'Processing...';
    const response = await fetch('/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text_command: command })
    });
    const data = await response.json();
    if (data.error) { statusEl.innerText = data.error; return; }
    statusEl.innerText = 'Opening: ' + data.url;
    window.open(data.url, '_blank');
}

function startListening() {
    if (!SpeechRecognition) return alert('Please use Chrome or Edge for voice support.');
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.onresult = e => sendCommand(e.results[0][0].transcript);
    recognition.onerror = e => statusEl.innerText = 'Error: ' + e.error;
    recognition.start();
}
</script>
</body>
</html>
"""


def build_youtube_target(command):
    """Build a YouTube search/results URL (opens in a new tab) from the spoken command."""
    query = re.sub(r"(open youtube( and (play|search))?|play|search( for)?|on youtube)", "", command).strip()
    if not query:
        return "https://www.youtube.com"
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"


def build_gmail_target(command):
    """Extract a recipient and body from the command and build a Gmail compose URL."""
    to, body = "", ""
    if m := re.search(r"to\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(and|type|saying|$))", command):
        recipient = m.group(1).strip().replace(" ", "")
        to = recipient if "@" in recipient else f"{recipient}@gmail.com"
    if m := re.search(r"(type|saying)\s+(.*)", command):
        body = m.group(2).strip().capitalize()
    if not to and not body:
        return "https://mail.google.com"
    params = urllib.parse.urlencode({"view": "cm", "fs": "1", "to": to, "body": body})
    return f"https://mail.google.com/mail/u/0/?{params}"


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/agent", methods=["POST"])
def agent():
    data = request.get_json(silent=True)
    if not data or "text_command" not in data:
        abort(400, description="Missing 'text_command' in request body")
    command = data["text_command"].strip().lower()
    if "youtube" in command or "play" in command:
        return jsonify({"action": "open_tab", "url": build_youtube_target(command)})
    if any(k in command for k in ["gmail", "email", "mail"]):
        return jsonify({"action": "open_tab", "url": build_gmail_target(command)})
    return jsonify({"error": "Only YouTube and Gmail commands are supported."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
