import os, re, urllib.parse, urllib.request
from flask import Flask, abort, jsonify, render_template_string, request

app = Flask(__name__)

HTML = """Voice Agent"""

# ---------------- YouTube ---------------- #

def find_first_video_id(query):
    """Fetches first YouTube video ID bypassing consent and user-agent blocks."""
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": "SOCS=CAI"
        })

        html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
        match = re.search(r'(?:"videoId":|/watch\?v=)"([a-zA-Z0-9_-]{11})"', html)

        return match.group(1) if match else None

    except Exception as e:
        print(f"Scraper error: {e}")
        return None


def build_youtube_target(command):
    wants_play = "play" in command
    query = re.sub(
        r"(open youtube( and (play|search))?|play|search( for)?|on youtube)",
        "", command
    ).strip()

    if not query:
        return "https://www.youtube.com"

    if wants_play:
        video_id = find_first_video_id(query)
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}&autoplay=1"

    return f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"


# ---------------- Gmail ---------------- #

def build_gmail_target(command):
    to, body = "", ""

    if m := re.search(r"to\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(and|type|saying|$))", command):
        recipient = m.group(1).strip().replace(" ", "")
        to = recipient if "@" in recipient else f"{recipient}@gmail.com"

    if m := re.search(r"(type|saying)\s+(.*)", command):
        body = m.group(2).strip().capitalize()

    if not to and not body:
        return "https://mail.google.com"

    return f"https://mail.google.com/mail/u/0/?{urllib.parse.urlencode({'view':'cm','fs':'1','to':to,'body':body})}"


# ---------------- Routes ---------------- #

@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/agent", methods=["POST"])
def agent():
    data = request.get_json(silent=True)

    if not data or "text_command" not in data:
        abort(400, description="Missing command")

    cmd = data["text_command"].strip().lower()

    if "youtube" in cmd or "play" in cmd:
        return jsonify({"action": "open_tab", "url": build_youtube_target(cmd)})

    if any(k in cmd for k in ["gmail", "email", "mail"]):
        return jsonify({"action": "open_tab", "url": build_gmail_target(cmd)})

    return jsonify({"error": "Only YouTube and Gmail commands supported."})


# ---------------- Run ---------------- #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
