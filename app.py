import speech_recognition as sr
import re
import json
import pandas as pd
from datetime import datetime
import os
from pydub import AudioSegment

# ----------------------------------------
# LOAD MENU PRICES
# ----------------------------------------

with open("menu_prices.json", "r", encoding="utf-8") as file:
    menu_prices = json.load(file)

# ----------------------------------------
# FIND AUDIO FILE AUTOMATICALLY
# ----------------------------------------

audio_folder = "audio"

supported_formats = (
    ".mp3",
    ".wav",
    ".ogg",
    ".m4a",
    ".aac",
    ".flac"
)

audio_file = None

for file in os.listdir(audio_folder):
    if file.lower().endswith(supported_formats):
        audio_file = os.path.join(audio_folder, file)
        break

if not audio_file:
    print("❌ No audio file found in 'audio' folder.")
    exit()

print(f"🎵 Found audio file: {audio_file}")

# ----------------------------------------
# CONVERT TO WAV IF NEEDED
# ----------------------------------------

wav_path = "audio/converted_audio.wav"

file_extension = os.path.splitext(audio_file)[1].lower()

if file_extension != ".wav":
    print("🔄 Converting audio to WAV...")

    audio = AudioSegment.from_file(audio_file)
    audio.export(wav_path, format="wav")

    print("✅ Audio converted successfully!")

    audio_path = wav_path
else:
    audio_path = audio_file

# ----------------------------------------
# SPEECH TO TEXT
# ----------------------------------------

recognizer = sr.Recognizer()

try:
    with sr.AudioFile(audio_path) as source:
        print("🎤 Listening to audio...")
        audio = recognizer.record(source)

    print("📝 Converting speech to text...")

    text = recognizer.recognize_google(
        audio,
        language="ta-IN"
    )

    print("\n📄 Text Output:")
    print(text)

    # ----------------------------------------
    # EXTRACT ITEM + QUANTITY
    # ----------------------------------------

    pattern = r'(\d+)\s([\w\u0B80-\u0BFF]+)'
    matches = re.findall(pattern, text)

    # Excel row structure
    row_data = {
        "DATE": datetime.now().strftime("%d-%m-%Y"),
        "IDLY": "",
        "QUANTITY": "",
        "DOSA": "",
        "QUANTITY_2": "",
        "POORI": "",
        "QUANTITY_3": "",
        "TEA": "",
        "QUANTITY_4": "",
        "COFFEE": "",
        "QUANTITY_5": "",
        "TOTAL": 0
    }

    calculated_total = 0

    # ----------------------------------------
    # FOOD NAME MAPPING
    # ----------------------------------------

    food_map = {
        "idly": "IDLY",
        "இட்லி": "IDLY",

        "dosa": "DOSA",
        "தோசை": "DOSA",

        "poori": "POORI",
        "பூரி": "POORI",

        "tea": "TEA",
        "டீ": "TEA",

        "coffee": "COFFEE",
        "காபி": "COFFEE"
    }

    quantity_columns = {
        "IDLY": "QUANTITY",
        "DOSA": "QUANTITY_2",
        "POORI": "QUANTITY_3",
        "TEA": "QUANTITY_4",
        "COFFEE": "QUANTITY_5"
    }

    # ----------------------------------------
    # PROCESS ITEMS
    # ----------------------------------------

    for qty, item in matches:
        item = item.lower()
        qty = int(qty)

        if item in food_map:
            food_name = food_map[item]

            # Store item name
            row_data[food_name] = food_name.capitalize()

            # Store quantity
            row_data[quantity_columns[food_name]] = qty

            # Calculate total from menu prices
            if item in menu_prices:
                item_total = qty * menu_prices[item]
                calculated_total += item_total

    # ----------------------------------------
    # ALWAYS USE CALCULATED TOTAL
    # ----------------------------------------

    row_data["TOTAL"] = calculated_total

    print(f"\n💰 Calculated Total: ₹{calculated_total}")

    # ----------------------------------------
    # SAVE TO EXCEL
    # ----------------------------------------

    df = pd.DataFrame([row_data])

    excel_file = "sales.xlsx"

    # Append existing data
    if os.path.exists(excel_file):
        old_df = pd.read_excel(excel_file)
        df = pd.concat([old_df, df], ignore_index=True)

    df.to_excel(excel_file, index=False)

    print("\n✅ Saved to sales.xlsx successfully!")

except Exception as e:
    print("❌ Error:", e)