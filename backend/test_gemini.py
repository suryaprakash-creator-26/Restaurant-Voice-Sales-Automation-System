from ai.gemini_service import ask_gemini

while True:

    question = input("You : ")

    if question.lower() == "exit":
        break

    answer = ask_gemini(question)

    print("Gemini :", answer)