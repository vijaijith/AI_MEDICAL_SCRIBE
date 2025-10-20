from faster_whisper import WhisperModel
import os
import ollama

# --------------------------
# Environment Setup
# --------------------------
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

# --------------------------
# Preload Models
# --------------------------
print("Initializing llama client...")
client = ollama.Client()

print("Loading Whisper model on GPU...")
whisper_model = WhisperModel(
    "large",          # You can switch to "medium" or "large" if GPU allows
    device="cuda",
    compute_type="float16"
)
print("Whisper model loaded.")


# --------------------------
# structured prescription
# --------------------------
def stru_pres(raw_text):
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    extracted_text = ""
    for line in lines:
        lower_line = line.lower()

        if "chief complaint" in lower_line:
            extracted_text += f"\n📝 Chief Complaint\n{line.replace('Chief Complaint', '').strip()}\n"
        elif "history of present illness" in lower_line:
            extracted_text += f"\n📖 History of Present Illness\n{line.replace('History of Present Illness', '').strip()}\n"
        elif "relevant past history" in lower_line:
            extracted_text += f"\n📜 Relevant Past History\n{line.replace('Relevant Past History', '').strip()}\n"
        elif "symptoms & examination findings" in lower_line:
            extracted_text += f"\n🔍 Symptoms & Examination Findings\n{line.replace('Symptoms & Examination Findings', '').strip()}\n"
        elif "assessment" in lower_line:
            extracted_text += f"\n🩺 Assessment / Impression\n{line.replace('Assessment / Impression', '').strip()}\n"
        elif "plan" in lower_line:
            extracted_text += f"\n🧾 Plan\n{line.replace('Plan', '').strip()}\n"
        elif "suggested medications" in lower_line:
            extracted_text += f"\n💊 Suggested Medications (with purpose)\n"
        elif "predicted medications" in lower_line:
            extracted_text += f"\n💊 Predicted Medications (with purpose)\n"
        elif "predicted disease" in lower_line:
            extracted_text += f"\n🩸 Predicted Disease\n"
        else:
            extracted_text += line + "\n"

    #print(extracted_text)
    return(extracted_text)
# --------------------------
# llama3 Helper
# --------------------------

def ask_llama(prompt: str, model_name: str = "llama3.1:8b") -> str:
    """
    Sends a prompt to llama3 and returns the response.
    """
    print("Sending request to llama3 model...")
    try:
        response = client.generate(
            model=model_name,
            prompt=prompt,
            stream=False
        )
        #return response.response
        text=stru_pres(response.response)
        return text
    except Exception as e:
        return f"Error: {e}"

# --------------------------
# Audio Processing Function
# --------------------------
def audio_pres(audio_path: str) -> str:
    """
    Transcribe audio to English, detect language, and generate structured medical note.
    """
    # 1️⃣ Transcribe & Translate
    segments, info = whisper_model.transcribe(
        audio_path,
        beam_size=5,
        task="translate"  # Auto translate to English
    )
    print(f"Detected predominant language: {info.language}")

    # 2️⃣ Build structured transcript
    transcript_lines = [
        f"[{seg.start:.2f}s - {seg.end:.2f}s] : {seg.text.strip()}"
        for seg in segments
    ]
    transcript_text = "\n".join(transcript_lines)
    print("\n--- Transcript ---\n")
    print(transcript_text)

    # 3️⃣ llama3 Prompt Rules
    rules = """
1. Write only clinical information from the conversation.  
2. Use concise, professional medical language.  
3. Structure output as:  
   - Chief Complaint  
   - History of Present Illness  
   - Relevant Past History (if mentioned)  
   - Symptoms & Examination Findings  
   - Assessment / Impression  
   - Plan  
4. Do not invent or assume details.  
5. Do not include demographics, identifiers, or dates.  
6. Use ICD-10-CM codes only if it is correct, double check that otherwise leave it.  
7. If it is not a doctor–patient conversation, output: "Not a conversation".  
8. End after **Probable Diagnosis** and do not repeat the note.
"""

    prompt = f"""
Convert the following doctor-patient conversation into standard format.
Follow these rules: {rules}
Conversation with timestamp:
{transcript_text}

At the end, provide:
- SUGGESTED MEDICATIONS with PURPOSE
- Try to predict Medications for the disease with purpose
- Predicted disease (if confident), only disease name otherwise give exactly "NOT SURE"
"""

    # 4️⃣ Ask llama3
    answer = ask_llama(prompt)
    return answer

# --------------------------
# Example Usage
# --------------------------
if __name__ == "__main__":
    # Optional: Preload llama3 model with a "warm-up" request
    print("Warming up llama3 model...")
    warmup = ask_llama("Act as an AI medical scribe")
    print("Warm-up complete.")

    # Process an audio file
    audio_file = "patient_recording.mp3"
    print(f"\nProcessing audio file: {audio_file}\n")
    transcript_note = audio_pres(audio_file)
    print("\n--- Generated Medical Note ---\n")
    print(transcript_note)