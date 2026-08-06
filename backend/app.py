import speech_recognition as sr
import re
import json
import pandas as pd
from datetime import datetime
import os
from pydub import AudioSegment
import sys
from database import (
    save_sale,
    save_review,
    save_voice_result,
    load_menu_prices,
    load_food_aliases,
    load_all_foods
)
from rapidfuzz import process, fuzz



# ----------------------------------------
# UTF-8 FIX
# ----------------------------------------
sys.stdout.reconfigure(encoding="utf-8")


# ----------------------------------------
# LOAD MENU & ALAISES
# ----------------------------------------
price_map = load_menu_prices()

    
aliases_data = load_food_aliases()



# ----------------------------------------
# INIT MAPS
# ----------------------------------------
food_map = {}



# ----------------------------------------
# BUILD MENU MAPS
# ----------------------------------------
all_foods = load_all_foods()

# ----------------------------------------
# LOAD ALIASES INTO FOOD MAP
# ----------------------------------------

food_map = {}

all_aliases = []

alias_to_food = {}

for food_name, alias in aliases_data:

    alias = alias.lower().strip()

    food_map[alias] = food_name

    alias_to_food[alias] = food_name

    all_aliases.append(alias)




# ----------------------------------------
# NORMALIZE
# ----------------------------------------
def normalize(text):
    return " ".join(text.lower().strip().split())

def fuzzy_match(item_text):

    result = process.extractOne(
        item_text,
        all_aliases,
        scorer=fuzz.WRatio
    )

    if result:

        alias, score, _ = result

        food_name = alias_to_food[alias]

        return food_name, score

    return None, 0


def top_matches(item_text):

    results = process.extract(
        item_text,
        all_aliases,
        scorer=fuzz.WRatio,
        limit=3
    )

    cleaned = []

    for alias, score, _ in results:

        cleaned.append({
            "alias": alias,
            "food": alias_to_food[alias],
            "score": round(score)
        })

    return cleaned

# ----------------------------------------
# AUDIO FILE
# ----------------------------------------
audio_folder = "audio"
supported_formats = (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac")

audio_file = None

for file in os.listdir(audio_folder):
    if file == "converted_audio.wav":
        continue
    if file.lower().endswith(supported_formats):
        audio_file = os.path.join(audio_folder, file)
        break

if not audio_file:
    print("No audio file found")
    exit()

print("Found:", audio_file)


# ----------------------------------------
# CONVERT AUDIO
# ----------------------------------------
wav_path = "audio/converted_audio.wav"

if os.path.splitext(audio_file)[1].lower() != ".wav":
    audio = AudioSegment.from_file(audio_file)
    audio.export(wav_path, format="wav")
    audio_path = wav_path
else:
    audio_path = audio_file


# ----------------------------------------
# SPEECH TO TEXT
# ----------------------------------------
recognizer = sr.Recognizer()

try:


    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)

    text = recognizer.recognize_google(audio, language="ta-IN")

    print("\nTEXT:", text)


    # ----------------------------------------
    # EXTRACT ITEMS
    # ----------------------------------------
    pattern = r'(\d+)\s([\w\u0B80-\u0BFF\s]+?)(?=\s\d+|$)'
    matches = re.findall(pattern, text)


    row_data = {"DATE": datetime.now().strftime("%d-%m-%Y")}

    for food in all_foods:
        row_data[food] = 0


    calculated_total = 0


    # ⭐ FIX ADDED HERE
    matched_items = []
    unknown_items = []
    review_items = []

    # ----------------------------------------
    # PROCESS ITEMS
    # ----------------------------------------
    for qty, item in matches:

        qty = int(qty)
        item = normalize(item)

        food_name = None
        score = 100

        # Exact Alias Match
        if item in food_map:

            food_name = food_map[item]
            score = 100

        # Fuzzy Match
        else:

            food_name, score = fuzzy_match(item)

    # ----------------------------------
    # HIGH CONFIDENCE
    # ----------------------------------
        if food_name and score >= 90:
            row_data[food_name] += qty

            item_price = price_map.get(food_name, 0)

            item_total = qty * item_price

            matched_items.append({
                "food": food_name,
                "qty": qty,
                "revenue": item_total
            })

            calculated_total += item_total
        

            try:
                save_sale(
                    datetime.now().strftime("%d-%m-%Y"),
                    food_name,
                    qty,
                    item_price,
                    item_total
                )
            except Exception as e:
                print("DB Error:", e)

            print(f"{item} → {food_name}")

    # ----------------------------------
    # MEDIUM CONFIDENCE
    # ----------------------------------
        elif food_name and score >= 70:

            print("TOP 3 MATCHES")

            print(top_matches(item))
    # ----------------------------------
    # UNKNOWN
    # ----------------------------------
        else:

            food_name, score = fuzzy_match(item)

            print("INPUT:", item)
            print("BEST MATCH:", food_name)
            print("SCORE:", score)
            print("TOP 3:", top_matches(item))

    # LOOP ENDS HERE
    voice_result_id = save_voice_result(
        text,
        json.dumps(matched_items),
        json.dumps(unknown_items),
        len(review_items),
        calculated_total,
        "waiting_approval" if review_items else "completed",
        datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )
    
    row_data["TOTAL"] = calculated_total
    
    for review in review_items:

        save_review(
            review["spoken_text"],
            review["suggested_food"],
            review["score"],
            review["qty"]
        )
    
    # ----------------------------------------
    # SAVE EXCEL
    # ----------------------------------------
    excel_file = "sales.xlsx"

    new_df = pd.DataFrame([row_data])

    if os.path.exists(excel_file):

        old_df = pd.read_excel(excel_file)

        for col in new_df.columns:
            if col not in old_df.columns:
                old_df[col] = 0

        for col in old_df.columns:
            if col not in new_df.columns:
                new_df[col] = 0

        new_df = new_df[old_df.columns]

        final_df = pd.concat([old_df, new_df], ignore_index=True)

    else:
        final_df = new_df
        
    # Move TOTAL to last column
    if "TOTAL" in final_df.columns:

        cols = [col for col in final_df.columns if col != "TOTAL"]

        cols.append("TOTAL")

        final_df = final_df[cols]

# Save Excel


    final_df.to_excel(excel_file, index=False)

    print("Saved to Excel ✔")


    # ⭐ FIXED latest_result (NO ERROR NOW)
    latest_result = {
        "text": text,
        "matched": matched_items,
        "unknown": unknown_items,
        "total": calculated_total,
        "status": "completed"
    }


    # ----------------------------------------
    # CLEANUP
    # ----------------------------------------
    if os.path.exists(audio_file):
        os.remove(audio_file)

    if os.path.exists(wav_path):
        os.remove(wav_path)

    print("Done ✔")


except Exception as e:
    print("ERROR:", e)