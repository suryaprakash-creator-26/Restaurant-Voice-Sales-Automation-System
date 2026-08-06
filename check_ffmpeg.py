from pydub import AudioSegment

try:
    # Replace with your audio file name
    input_file = "audio/ffmpeg_check.ogg"

    print("Loading audio file...")

    audio = AudioSegment.from_file(input_file)

    print("Converting to WAV...")

    output_file = "audio/converted_audio.wav"

    audio.export(output_file, format="wav")

    print("✅ Conversion successful!")
    print(f"Saved as: {output_file}")

except Exception as e:
    print("❌ Error:", e)