import gradio as gr
import sqlite3
import shutil
import hashlib
import datetime
import os
from audio import audio_pres   # ✅ your transcription function
from whatsapp import send_prescription

import base64  # Make sure this import is at the top

# ----------------- CONFIG -----------------
DB_PATH = "medical_scribe.db"
contact = 0
PHOTO_DIR = "patient_photos"
os.makedirs("uploads", exist_ok=True)

# ----------------- DB INIT -----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Doctors (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password_hash TEXT,
        name TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Patients (
        id INTEGER PRIMARY KEY,
        name TEXT,
        dob TEXT,
        gender TEXT,
        blood_group TEXT,
        contact TEXT,
        photo_path TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Encounters (
        id INTEGER PRIMARY KEY,
        doctor_id INTEGER,
        patient_id INTEGER,
        timestamp TEXT,
        transcript TEXT,
        FOREIGN KEY (doctor_id) REFERENCES Doctors(id),
        FOREIGN KEY (patient_id) REFERENCES Patients(id)
    )""")
    conn.commit()
    conn.close()

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def add_doctor(username, password, name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO Doctors (username,password_hash,name) VALUES (?,?,?)",
                    (username, hash_password(password), name))
        conn.commit()
        return "✅ Account created successfully!"
    except sqlite3.IntegrityError:
        return "⚠️ Username already exists."
    finally:
        conn.close()

def login_doctor(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id,name,password_hash FROM Doctors WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None, "❌ Doctor not found."
    did, name, pwhash = row
    if pwhash == hash_password(password):
        return {"id": did, "name": name}, f"👨‍⚕️ Welcome, Dr. {name}!"
    return None, "❌ Incorrect password."

def add_patient(name, dob, gender, blood_group,contact,photo_path):

    if not (name and gender and dob and contact and blood_group):
        return "⚠️ All fields are required"

    saved_photo_path = None
    if photo_path:
        os.makedirs(PHOTO_DIR, exist_ok=True)
        photo_filename = f"{name}_{int(datetime.datetime.now().timestamp())}.jpg"
        saved_photo_path = os.path.join(PHOTO_DIR, photo_filename)
        shutil.copy(photo_path, saved_photo_path)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO Patients (name,dob,gender,blood_group,contact,photo_path) VALUES (?,?,?,?,?,?)", (name, dob, gender, blood_group, contact, saved_photo_path))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return f"✅ Patient added with ID: {pid}"

def search_patients(q):
    global contact_p
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if str(q).isdigit():
        cur.execute("SELECT * FROM Patients WHERE id=?", (int(q),))
    else:
        cur.execute("SELECT * FROM Patients WHERE name LIKE ? OR dob LIKE ?", (f"%{q}%", f"%{q}%"))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return [], gr.update(visible=False)
    
    contact_p = rows[0][5]
    photo_path = rows[0][6] if rows else None  # 6 = photo_path column
    photo_elem = gr.update(value=photo_path, visible=bool(photo_path))
    return rows, photo_elem, gr.update(visible=True)

def save_encounter(doctor_id, patient_id, transcript):
    a=send_prescription(contact_p, transcript)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO Encounters (doctor_id,patient_id,timestamp,transcript) VALUES (?,?,?,?)",
                (doctor_id, patient_id, datetime.datetime.now().isoformat(), transcript))
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid,a

# ----------------- GRADIO UI -----------------
init_db()

with gr.Blocks(title="AI Medical Scribe") as app:
    gr.Markdown("# 🏥 AI Medical Scribe\nRecord, Transcribe & Generate SOAP Notes")

    state = gr.State({"doctor": None})

    # ---- Login/Signup ----
    with gr.Tab("👨‍⚕️ Doctor Access"):

        # -------- PAGE 1: Login + Signup --------
        with gr.Group(visible=True) as doctor1:
            gr.Markdown("---\n### 🔐 Login")
            l_user = gr.Textbox(label="Username")
            l_pass = gr.Textbox(label="Password", type="password")
            login_btn = gr.Button("Login")
            login_msg = gr.Markdown("")

            gr.Markdown("### 🩺 Sign Up")
            d_name = gr.Textbox(label="Full Name")
            d_user = gr.Textbox(label="Username")
            d_pass = gr.Textbox(label="Password", type="password")
            signup_btn = gr.Button("Create Account")
            signup_msg = gr.Markdown("")

            signup_btn.click(add_doctor, [d_user, d_pass, d_name], [signup_msg])

        # -------- PAGE 2: Doctor Dashboard --------
        with gr.Group(visible=False) as doctor2:
            doctor_name_md = gr.Markdown("### 🩺 Dr. <PRIVATE>")
            gr.Markdown("")

            # --- Patient Search ---
            pid = gr.Number(label="Patient ID", precision=0)
            s_btn = gr.Button("Search")
            patient_photo = gr.Image(label="Patient Photo", type="filepath", visible=False)
            s_out = gr.Dataframe(headers=["ID", "Name", "DOB", "Gender", "Blood Group","Contact","Photo"]) 
            s_btn.click(search_patients, [pid], [s_out, patient_photo])

            # --- Audio Processing ---
            audio_input = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="🎙️ Record or Upload Audio"
            )
            trans_btn = gr.Button("Transcribe & Generate Note")
            transcript_box = gr.Textbox(label="Transcript", lines=6, interactive=True)
            save_btn = gr.Button("Save Encounter")
            save_msg = gr.Markdown("")

             # --- View Visit History ---
            view_hist_btn = gr.Button("📜 View Visit History")
            hist_box = gr.Textbox(label="Visit History", lines=8, interactive=False, visible=False)

            def fetch_history(pid):
                if not pid:
                    return gr.update(value="⚠️ Please enter a valid Patient ID.", visible=True)
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT timestamp, transcript FROM Encounters WHERE patient_id=? ORDER BY timestamp DESC", (pid,))
                rows = cur.fetchall()
                conn.close()

                if not rows:
                    return gr.update(value=f"⚠️ No visit history found for Patient ID {pid}.", visible=True)
        
                # Format the visit history neatly
                history_text = f"📋 Visit History for Patient ID {pid}:\n\n"
                for ts, trans in rows:
                    history_text += f"🕒 {ts}\n{trans}\n\n---\n\n"

                return gr.update(value=history_text, visible=True)

            view_hist_btn.click(fetch_history, [pid], [hist_box])

            logout_btn = gr.Button("🚪 Logout")

        # -------- LOGIC FUNCTIONS --------
        def login_action(u, p, s):
            doc, msg = login_doctor(u, p)
            if doc:
                s["doctor"] = doc
                # Update doctor name dynamically
                return (
                    msg,
                    s,
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(value=f"### 🩺 Dr. {doc['name']}")
                )
            else:
                return msg, s, gr.update(), gr.update(), gr.update()

        def process_encounter(audio_path, pid, s):
            if not audio_path:
                return gr.update(value="⚠️ No audio input found.", interactive=True), s

            text = audio_pres(audio_path)  # your transcription function
            doc = s.get("doctor")
            dname = doc["name"] if doc else "Unknown"
            text = f"🩺 Dr. {dname}\n" + text

            s["last"] = {"pid": pid, "trans": text}
            return gr.update(value=text, interactive=True), s

        def save_enc(pid, final_text, s):
            doc = s.get("doctor")
            if not doc:
                return "⚠️ Please log in first."
            if not final_text.strip():
                return "⚠️ Transcript is empty or not saved yet."

            # Save to database
            eid, a = save_encounter(doc["id"], pid, final_text)

            # Optionally store in session for WhatsApp sending
            s["last_saved"] = {"pid": pid, "text": final_text}

            return f"✅ Encounter saved with ID {eid} ({a})"

        def logout_action(s):
            s["doctor"] = None
            s["last"] = None
            return s, gr.update(visible=True), gr.update(visible=False), gr.update(value="### 🩺 Dr. <PRIVATE>")

        # -------- BUTTON CONNECTIONS --------
        login_btn.click(
            login_action,
            [l_user, l_pass, state],
            [login_msg, state, doctor1, doctor2, doctor_name_md],
        )

        trans_btn.click(process_encounter, [audio_input, pid, state], [transcript_box, state])
        save_btn.click(save_enc, [pid, transcript_box, state], [save_msg])
        logout_btn.click(logout_action, [state], [state, doctor1, doctor2, doctor_name_md])

    # ---- Patients ----
    with gr.Tab("🧑‍⚕️ Patients"):
        gr.Markdown("### Add Patient")
        p_name = gr.Textbox(label="Patient Name")
        p_dob = gr.Textbox(label="DOB (YYYY-MM-DD)")
        p_gender = gr.Radio(["Male", "Female", "Other"], label="Gender")
        p_blood = gr.Radio(["O+", "O-", "A+", "A-", "B+","B-","AB+","AB-" ], label="Blood Group")
        p_contact = gr.Textbox(label="Contact Number")
        p_photo = gr.Image(label="Upload Patient Photo", type="filepath")
        addp_btn = gr.Button("Add Patient")
        addp_msg = gr.Markdown("")
        addp_btn.click(add_patient, [p_name, p_dob, p_gender,p_blood,p_contact,p_photo], [addp_msg])

        gr.Markdown("### Search Patients")
        s_query = gr.Textbox(label="Patient ID")
        s_btn = gr.Button("Search")
        s_out = gr.Dataframe(headers=["ID", "Name", "DOB", "Gender", "Blood Group","Contact","Photo"])
        patient_photo = gr.Image(label="Patient Photo", type="filepath", visible=False) 
        s_btn.click(search_patients, [s_query], [s_out, patient_photo])



    # ---- Reports ----
    with gr.Tab("📄 Reports"):
        gr.Markdown("### Upload Patient Scanning Reports")
    
        # Input: Patient ID and file upload
        report_pid = gr.Number(label="Patient ID", precision=0)
        # search
        s_btn = gr.Button("Search")
        s_out = gr.Dataframe(headers=["ID", "Name", "DOB", "Gender", "Blood Group","Contact","Photo"])
        patient_photo = gr.Image(label="Patient Photo", type="filepath", visible=False) 
        s_btn.click(search_patients, [report_pid], [s_out, patient_photo])


        #view reports

        view_btn = gr.Button("👁️ View Reports")
        report_html = gr.HTML(label="Patient Reports", visible=False)
        no_report_msg = gr.Markdown("", visible=False)

        def fetch_reports(pid):
            if not pid:
                return gr.update(visible=False)

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT timestamp, file_path FROM Reports WHERE patient_id=? ORDER BY timestamp DESC", (pid,))
            rows = cur.fetchall()
            conn.close()

            if not rows:
                return gr.update(visible=False), gr.update(value="⚠️ No reports found for this patient.", visible=True)

            # Build HTML for images with timestamps (base64)
            html_content = '<div style="display:flex; flex-wrap:wrap; gap:10px; max-height:500px; overflow:auto;">'
            for ts, fp in rows:
                ext = os.path.splitext(fp)[1].lower()
                if ext in [".jpg", ".jpeg", ".png"]:
                    try:
                        with open(fp, "rb") as f:
                            encoded = base64.b64encode(f.read()).decode()
                        html_content += f'''
                <div style="text-align:center; width:300px;">  <!-- Bigger container -->
                    <img src="data:image/{ext[1:]};base64,{encoded}" 
                         style="max-width:100%; height:auto; border:1px solid #ccc;"/>  <!-- Scales to container -->
                    <br><small>{ts}</small>
                </div>
            '''
                    except Exception as e:
                        html_content += f"<div style='color:red;'>Failed to load {fp}: {e}</div>"
            html_content += '</div>'
            return gr.update(value=html_content, visible=True),gr.update(visible=False)

        view_btn.click(fetch_reports, [report_pid], [report_html, no_report_msg])


        #---------------------

        report_file = gr.File(label="Upload Report (PDF/Image)", file_types=[".pdf", ".jpg", ".png"])
        upload_btn = gr.Button("Upload Report")
        upload_msg = gr.Markdown("")
    
        REPORTS_DIR = "patient_reports"
        os.makedirs(REPORTS_DIR, exist_ok=True)
    
        def upload_report(pid, file):
            if not pid or not file:
                return "⚠️ Patient ID and file are required."
        
            # Save file with patient ID and timestamp
            filename = f"PID{pid}_{int(datetime.datetime.now().timestamp())}_{os.path.basename(file.name)}"
            save_path = os.path.join(REPORTS_DIR, filename)
            shutil.copy(file.name, save_path)
        
            # Optionally: Save path in the database if you want
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Reports (
                    id INTEGER PRIMARY KEY,
                    patient_id INTEGER,
                    file_path TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (patient_id) REFERENCES Patients(id)
                )
                """)
            cur.execute("INSERT INTO Reports (patient_id, file_path, timestamp) VALUES (?,?,?)",
                        (pid, save_path, datetime.datetime.now().isoformat()))
            conn.commit()
            conn.close()
        
            return f"✅ Report uploaded successfully for Patient ID {pid}!"
    
        upload_btn.click(upload_report, [report_pid, report_file], [upload_msg])


if __name__ == "__main__":
    app.launch()
