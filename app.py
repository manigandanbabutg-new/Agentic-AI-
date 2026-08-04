import os
import re
import urllib.parse
import urllib.request

from flask import Flask, abort, jsonify, render_template_string, request

app = Flask(__name__)


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Voice Agent</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 500px;
            margin: 60px auto;
        }
        button {
            padding: 30px 30px;
            background: #4f46e5;
            color: #fff;
            border: 0;
            border-radius: 56px;
            cursor: pointer;
        }
        #transcript {
            margin-top: 20px;
            font-style: italic;
        }
        #status {
            font-size: 13px;
            color: #555;
            word-break: break-all;
        }
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

            if (data.error) {
                statusEl.innerText = data.error;
                return;
            }

            statusEl.innerText = 'Opening: ' + data.url;
            window.open(data.url, '_blank');
        }

        function startListening() {
            if (!SpeechRecognition) {
                alert('Please use Chrome or Edge for voice support.');
                return;
            }

            const recognition = new SpeechRecognition();
            recognition.lang = 'en-US';

            recognition.onresult = (event) => {
                const command = event.results[0][0].transcript;
                sendCommand(command);
            };

            recognition.onerror = (event) => {
                statusEl.innerText = 'Error: ' + event.error;
            };

            recognition.start();
        }
    </script>
</body>
</html>
"""


def get_youtube_video_id(query):
    """Search YouTube and return the first matching video ID, or None."""
    try:
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=5).read().decode()

        video_ids = re.findall(r"\"videoId\":\"([^\"]+)\"", html)
        return video_ids[0] if video_ids else None
    except Exception:
        return None


def build_youtube_target(command):
    """Strip filler phrases from the command and build a YouTube URL."""
    filler_pattern = r"(open youtube( and (search|play))?|search for|play|on youtube)"
    query = re.sub(filler_pattern, "", command).strip()

    if not query:
        return "https://www.youtube.com"

    video_id = get_youtube_video_id(query)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}&autoplay=1"

    return f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"


def build_gmail_target(command):
    """Extract a recipient and message body from the command and build a Gmail compose URL."""
    to, body = "", ""

    recipient_match = re.search(r"to\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(and|type|saying|$))", command)
    if recipient_match:
        recipient = recipient_match.group(1).strip().replace(" ", "")
        to = recipient if "@" in recipient else f"{recipient}@gmail.com"

    body_match = re.search(r"(type|saying)\s+(.*)", command)
    if body_match:
        body = body_match.group(2).strip().capitalize()

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

    if "youtube" in command:
        target_url = build_youtube_target(command)
    elif any(keyword in command for keyword in ["gmail", "email", "mail"]):
        target_url = build_gmail_target(command)
    else:
        return jsonify({"error": "Only YouTube and Gmail commands are supported."})

    return jsonify({"action": "open_tab", "url": target_url})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
