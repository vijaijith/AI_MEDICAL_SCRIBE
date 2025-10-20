# 🩺 AI Doctor Assistant – Audio to Structured Prescription

This project is an **AI-powered medical assistant** that converts **doctor–patient voice conversations** into **structured medical prescriptions**.  
It uses **Whisper** for audio transcription, **Llama 3** for structured summarization, and allows sending prescriptions **instantly via WhatsApp**.

---

## 🚀 Features

- 🎙️ **Audio Transcription** – Converts speech to English text using the Whisper model (via Faster-Whisper).
- 🧠 **AI Medical Summarization** – Uses **Llama 3** to structure data into sections:
  - Chief Complaint  
  - History of Present Illness  
  - Relevant Past History  
  - Symptoms & Examination Findings  
  - Assessment / Impression  
  - Plan  
  - Suggested & Predicted Medications
- 💬 **WhatsApp Integration** – Instantly send generated prescriptions to patients via WhatsApp.
- 🖥️ **Interactive UI** – Gradio-based web interface for uploading, reviewing, and sending prescriptions.

---

## 🧩 Project Structure

📂 AI-Doctor-Assistant/
│
├── audio.py # Handles transcription & structured medical summarization
├── whatsapp.py # Sends prescription messages via WhatsApp
├── gradio.ipynb # UI built with Gradio
├── requirements.txt # Dependencies list
└── README.md # Project overview

## 🧠 Model Setup

This project uses:

Ollama for Llama3 model inference
👉 Install from https://ollama.ai

ollama pull llama3.1:8b


Faster Whisper for transcription
👉 Automatically downloads when running the app.


## ▶️ Running the Project

Simply open and run:

jupyter notebook gradio.ipynb or in VScode

## 🧰 Requirements

See requirements.txt
 for all required dependencies.

## 🛡️ Disclaimer

This project is a prototype for educational and research use.
It should not be used as a replacement for professional medical advice or diagnosis.

## 🧑‍💻 Author

Developed by: github.com/vijaijith
