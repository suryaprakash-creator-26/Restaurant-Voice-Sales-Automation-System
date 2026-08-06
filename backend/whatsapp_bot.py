from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from requests.auth import HTTPBasicAuth
import requests
import os
import subprocess
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()
#----------------------------------------------------
# TWILIO CREDENTIALS

account_sid = os.getenv("ACCOUNT_SID")
auth_token = os.getenv("AUTH_TOKEN")

#----------------------------------------------------


app = Flask(__name__)

#Dashboard voice input result
@app.route("/dashboard-data")
def dashboard_data():
    return jsonify(latest_result)


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")
# ----------------------------------------
# HOME ROUTE
# ----------------------------------------

@app.route("/")
def home():
    return "WhatsApp Bot Running!"

# ----------------------------------------
# WHATSAPP WEBHOOK
# ----------------------------------------

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    response = MessagingResponse()

    incoming_msg = request.values.get("Body", "")
    num_media = request.values.get("NumMedia", "0")

    print("Message:", incoming_msg)
    print("Media Count:", num_media)

    # ----------------------------------------
    # IF VOICE MESSAGE
    # ----------------------------------------

    if num_media != "0":

        media_url = request.values.get("MediaUrl0")
        media_type = request.values.get("MediaContentType0")

        print("Media URL:", media_url)
        print("Media Type:", media_type)

        # Create audio folder
        os.makedirs("audio", exist_ok=True)

        # Remove old files
        for file in os.listdir("audio"):
            file_path = os.path.join("audio", file)
            os.remove(file_path)

        # Decide extension
        extension = ".ogg"

        if "mpeg" in media_type:
            extension = ".mp3"

        elif "wav" in media_type:
            extension = ".wav"

        elif "m4a" in media_type:
            extension = ".m4a"

        audio_path = f"audio/voice{extension}"

        
       # Download audio
        audio_data = requests.get(
            media_url,
            auth=HTTPBasicAuth(
                ACCOUNT_SID,
                AUTH_TOKEN
            ),
            stream=True
        )

        print("Download Status:", audio_data.status_code)

        with open(audio_path, "wb") as f:
            for chunk in audio_data.iter_content(1024):
                f.write(chunk)

        print("File Size:", os.path.getsize(audio_path))
        print("Voice saved:", audio_path)
       

        # ----------------------------------------
        # RUN YOUR EXISTING APP.PY
        # ----------------------------------------

        result = subprocess.run(
            ["python", "app.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        print("OUTPUT:")
        print(result.stdout)

        if result.stderr.strip():
            print("ERROR:")
            print(result.stderr)

        response.message(
            "Voice processed successfully!\n"
            "Sales saved to Excel."
        )

    else:

        response.message(
            f"Received: {incoming_msg}"
        )

    return str(response)

# ----------------------------------------
# RUN SERVER
# ----------------------------------------

if __name__ == "__main__":
    app.run(port=5000)