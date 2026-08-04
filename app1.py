import os
import re
import urllib.parse
import urllib.request
from flask import Flask, abort, jsonify, render_template, request

# ---------------------- Flask App ----------------------

app = Flask(__name__)

# ------------------ YouTube Video Finder ------------------

def get_vid(query):
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")

        ids = re.findall(r'"videoId":"([^"]+)"', html)

        return ids[0] if ids else None

    except Exception:
        return None


# ------------------------ Routes ------------------------

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/agent", methods=["POST"])
def ai_agent_router():

    data = request.get_json(silent=True)

    if not data or "text_command" not in data:
        abort(400, description="Missing 'text_command' in request body")

    cmd = data["text_command"].strip().lower()

    # ---------------- YouTube ----------------

    if "youtube" in cmd:

        query = cmd

        for phrase in [
            "open youtube and search",
            "open youtube and play",
            "open youtube",
            "search for",
            "search",
            "and play",
            "play",
            "on youtube",
        ]:
            query = query.replace(phrase, "")

        query = query.strip()

        if not query:
            target = "https://www.youtube.com"

        elif (vid := get_vid(query)):
            target = f"https://www.youtube.com/watch?v={vid}&autoplay=1"

        else:
            target = (
                "https://www.youtube.com/results?search_query="
                f"{urllib.parse.quote_plus(query)}"
            )

    # ---------------- Gmail ----------------

    elif any(word in cmd for word in ["gmail", "email", "mail", "message"]):

        to = ""
        body = ""

        if match := re.search(
            r"(?:update|send|mail|message)?\s*to\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(?:and|type|write|saying|with|content|that|message|$))",
            cmd,
        ):
            contact = (
                match.group(1)
                .strip()
                .replace(" at ", "@")
                .replace(" dot ", ".")
                .replace(" ", "")
            )

            to = contact if "@" in contact else f"{contact}@gmail.com"

        if match := re.search(
            r"(?:type|write|saying|content|message|that)\s+(.*)",
            cmd,
        ):
            text = match.group(1).strip()

            if text:
                body = text[0].upper() + text[1:]

        if to or body:
            target = (
                "https://mail.google.com/mail/u/0/?"
                f"view=cm&fs=1&to={urllib.parse.quote(to)}"
                f"&body={urllib.parse.quote(body)}"
            )
        else:
            target = "https://mail.google.com"

    # ---------------- Google ----------------

    else:
        target = (
            "https://www.google.com/search?q="
            f"{urllib.parse.quote_plus(cmd)}"
        )

    return jsonify(
        {
            "action": "open_tab",
            "url": target,
        }
    )


# -------------------- Run Server --------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
    )
