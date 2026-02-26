import streamlit as st
import json
import requests
import random
import string
import boto3
import time
import re
from botocore.exceptions import ClientError
from streamlit_local_storage import LocalStorage 
from datetime import datetime

# --- GROQ AI VALIDATOR ---
class GroqMedicalScribe:
    def __init__(self, api_key, model="llama-3.3-70b-versatile"): 
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.api_key = api_key
        self.model = model

    def validate_step(self, step_name, rules, step_data):
        if not self.api_key:
            return "Groq API Key missing in Secrets."
            
        prompt = f"""
        You are a strict medical data validation AI. Review the VETERAN'S INPUT against the VALIDATION RULES.
        
        SECTION: {step_name}
        VETERAN'S INPUT: {json.dumps(step_data)}
        RULES: {rules}
        
        You must output ONLY a valid JSON object.
        Format exactly like this:
        {{
          "status": "PASS" or "FAIL",
          "hint": "If FAIL, write your 1-2 sentence hint here explaining what needs correction. If PASS, leave empty."
        }}
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a literal data validator returning only JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0
        }
        
        try:
            res = requests.post(self.url, json=payload, headers=headers, timeout=25)
            if res.status_code != 200:
                return f"API Error: {res.text}"
                
            response_text = res.json()['choices'][0]['message']['content'].strip()
            
            try:
                parsed_json = json.loads(response_text)
                if parsed_json.get("status") == "PASS":
                    return "PASS"
                else:
                    return parsed_json.get("hint", "Missing information. Please check your inputs.")
            except json.JSONDecodeError:
                return f"Model error. Raw output: {response_text}"
                
        except Exception as e:
            return f"Cannot connect to Groq server. Error: {str(e)}"

# --- AWS S3 FUNCTIONS ---
def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=st.secrets["aws"]["ACCESS_KEY"],
        aws_secret_access_key=st.secrets["aws"]["SECRET_KEY"],
    )

def upload_to_source(json_data, filename):
    try:
        s3 = get_s3_client()
        bucket_name = st.secrets["aws"]["BUCKET_NAME"]
        s3_key = f"source_files/{filename}"
        
        s3.put_object(
            Bucket=bucket_name, Key=s3_key, Body=json_data, ContentType='application/json'
        )
        return True
    except Exception as e:
        st.error(f"S3 Upload Error: {e}")
        return False

def poll_output_bucket(filename, initial_wait=30, timeout=180):
    s3 = get_s3_client()
    output_bucket = st.secrets["aws"]["OUTPUT_BUCKET_NAME"]
    
    placeholder = st.empty()
    for i in range(initial_wait, 0, -1):
        placeholder.info(f"Processing... polling will start in {i} seconds.")
        time.sleep(1)
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            placeholder.info(f"Checking S3 for result... ({int(time.time() - start_time)}s elapsed)")
            response = s3.get_object(Bucket=output_bucket, Key=filename)
            file_content = response['Body'].read().decode('utf-8')
            placeholder.success("Processing Complete! Result received.")
            return json.loads(file_content)
        except ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                time.sleep(5) 
            else:
                placeholder.error(f"S3 Error: {e}")
                return None
        except Exception as e:
            placeholder.error(f"Error: {e}")
            return None
            
    placeholder.error("Timeout: too long to process the file.")
    return None

# --- KEY MAPPING ---
ALL_KEYS_ORDERED = [
    "Sinusitis__c.Sinusitis_1a__c", "Sinusitis__c.Sinus_Q10c__c", "Sinusitis__c.Sinus_Q11__c",
    "Sinusitis__c.Sinus_Q11a__c", "Sinusitis__c.Sinus_Q11aaa__c", "Sinusitis__c.Sinus_Q11aab__c",
    "Sinusitis__c.Sinus_Q11aac__c", "Sinusitis__c.Sinus_Q11aba__c", "Sinusitis__c.Sinus_Q11abb__c",
    "Sinusitis__c.Sinus_Q11abc__c", "Sinusitis__c.Sinus_Q11aca__c", "Sinusitis__c.Sinus_Q11acb__c",
    "Sinusitis__c.Sinus_Q11acc__c", "Sinusitis__c.Sinus_Q11b__c", "Sinusitis__c.Sinus_Q48__c",
    "Sinusitis__c.Sinus_Q34__c", "Sinusitis__c.Sinus_Q12__c", "Sinusitis__c.Sinus_Q13__c",
    "Sinusitis__c.Sinus_Q14__c", "Sinusitis__c.Sinus_Q15__c", "Sinusitis__c.Sinus_Q16__c",
    "Sinusitis__c.Sinus_Q17__c", "Sinusitis__c.Sinus_Q17a__c", 
    "Sinusitis__c.Sinus_Q17aaa__c", "Sinusitis__c.Sinus_Q17aaa1__c", "Sinusitis__c.Sinus_Q17aab__c", 
    "Sinusitis__c.Sinus_Q17aba__c", "Sinusitis__c.Sinus_Q17aba1__c", "Sinusitis__c.Sinus_Q17abb__c", 
    "Sinusitis__c.Sinus_Q17abc__c", "Sinusitis__c.Sinus_Q17abc1__c", "Sinusitis__c.Sinus_Q17aca__c", 
    "Sinusitis__c.Sinus_Q17acb__c", "Sinusitis__c.Sinus_Q17acb1__c", "Sinusitis__c.Sinus_Q17acc__c", 
    "Sinusitis__c.Sinus_Q17b__c", "Sinusitis__c.Sinus_Q17c__c", "Sinusitis__c.Sinus_Q17d__c", 
    "Sinusitis__c.Sinus_Q20__c", "Sinusitis__c.Sinus_Q20a__c", "Sinusitis__c.Sinus_Q20b__c", "Sinusitis__c.Sinus_Q20c__c",
    "Sinusitis__c.Sinus_Q20d__c", "Sinusitis__c.Sinus_Q35__c", "Sinusitis__c.Sinus_Q35a__c",
    "Sinusitis__c.Sinus_Q35b__c", "Sinusitis__c.Sinus_Q35c__c", "Sinusitis__c.Sinus_Q36__c",
    "Sinusitis__c.Sinus_Q36a__c", "Sinusitis__c.Sinus_Q36b__c", "Sinusitis__c.Sinus_Q36c__c",
    "Sinusitis__c.Sinus_Q36d__c", "Sinusitis__c.Sinus_Q36e__c", "Sinusitis__c.Sinus_Q36f__c",
    "Sinusitis__c.Sinus_Q36g__c", "Sinusitis__c.Sinus_Q36h__c", "Sinusitis__c.Sinus_Q37__c",
    "Sinusitis__c.Sinus_Q37a__c", "Sinusitis__c.Sinus_Q38__c", "Sinusitis__c.Sinus_Q38a__c",
    "Sinusitis__c.Sinus_Q39__c", "Sinusitis__c.Sinus_Q39a__c", "Sinusitis__c.Sinus_Q39b__c",
    "Sinusitis__c.Sinus_Q39c__c", "Sinusitis__c.Sinus_Q39d__c", "Sinusitis__c.Sinus_Q30__c",
    "Sinusitis__c.Sinus_Q31__c", "Sinusitis__c.Sinus_Q40__c", "Sinusitis__c.Sinus_Q41__c",
    "Sinusitis__c.Sinus_Q32__c", "Sinusitis__c.Sinus_Q43__c", "Sinusitis__c.Sinus_Q42__c",
    "Sinusitis__c.Sinus_Q49__c", "Sinusitis__c.Sinus_Q50__c", "Sinusitis__c.Sinus_Q51__c",
    "Sinusitis__c.Sinus_Q52__c", "Sinusitis__c.Sinus_Q44__c", "Sinusitis__c.Sinus_Q53__c",
    "Sinusitis__c.Sinus_Q54__c", "Sinusitis__c.Sinus_Q55__c", "Sinusitis__c.Sinus_Q56__c",
    "Sinusitis__c.Sinus_Q45__c", "Sinusitis__c.Sinus_Q46__c", "Sinusitis__c.Sinus_Q47__c",
    "Sinusitis__c.Sinus_Q42e__c", "Sinusitis__c.Sinus_Q21__c", "Sinusitis__c.DBQ__c.Veteran_Name_Text__c",
    "Sinusitis__c.Date_Submitted__c"
]

QUESTION_MAP = {
    "Sinusitis_1a__c": "Initial claim or re-evaluation?",
    "Sinus_Q10c__c": "Brief history of sinus condition",
    "Sinus_Q11__c": "Do you currently take any medication?",
    "Sinus_Q11a__c": "How many medications?",
    "Sinus_Q11aaa__c": "Medication #1 Name", "Sinus_Q11aba__c": "Medication #2 Name", "Sinus_Q11aca__c": "Medication #3 Name",
    "Sinus_Q48__c": "Seeking service connection?",
    "Sinus_Q34__c": "Indicate the sinus/type of sinusitis affected",
    "Sinus_Q15__c": "Number of non-incapacitating episodes (last 12 months)",
    "Sinus_Q16__c": "Number of incapacitating episodes (last 12 months)",
    "Sinus_Q12__c": "Symptoms checklist",
    "Sinus_Q14__c": "Detailed symptom description",
    "Sinus_Q17__c": "Ever had sinus surgery?",
    "Sinus_Q17a__c": "How many sinus surgeries?",
    "Sinus_Q17aaa__c": "Surgery #1 Date", "Sinus_Q17aaa1__c": "Surgery #1 Type", "Sinus_Q17aab__c": "Surgery #1 Findings",
    "Sinus_Q17aba__c": "Surgery #2 Date", "Sinus_Q17aba1__c": "Surgery #2 Type", "Sinus_Q17abb__c": "Surgery #2 Findings",
    "Sinus_Q17abc__c": "Surgery #3 Date", "Sinus_Q17abc1__c": "Surgery #3 Type", "Sinus_Q17aca__c": "Surgery #3 Findings",
    "Sinus_Q17acb__c": "Surgery #4 Date", "Sinus_Q17acb1__c": "Surgery #4 Type", "Sinus_Q17acc__c": "Surgery #4 Findings",
    "Sinus_Q17b__c": "Which sinus was operated on?",
    "Sinus_Q17c__c": "Which side of your sinuses were operated on?",
    "Sinus_Q17d__c": "Additional Surgeries (>4) Details",
    "Sinus_Q21__c": "Occupational Impact"
}
# --- APP CONFIG ---
st.set_page_config(page_title="Sinusitis DBQ Validation", layout="centered")

# --- CUSTOM CSS DLA FIRMOWYCH KOLORÓW I CZCIONKI REE MEDICAL ---
st.markdown("""
    <style>
        /* Wymuszenie Avenir na głównych elementach tekstowych */
        .stApp, p, h1, h2, h3, h4, h5, h6, label, input, textarea, select, li {
            font-family: 'Avenir', 'Avenir Next', sans-serif !important;
        }
        
        /* TWARDA OCHRONA IKON STREAMLITA (Naprawia 'keyboard_double') */
        span.material-symbols-rounded, 
        .material-symbols-rounded, 
        i.material-icons {
            font-family: 'Material Symbols Rounded', 'Material Icons' !important;
        }

        /* Żółte przyciski REE Medical z granatowym tekstem */
        div.stButton > button {
            background-color: #fbc049 !important;
            color: #003048 !important; /* Granatowy tekst na przycisku */
            border: 1px solid #fbc049 !important;
            font-weight: bold !important; /* Pogrubienie tekstu dla lepszego kontrastu */
            font-family: 'Avenir', 'Avenir Next', sans-serif !important;
        }
        
        /* Efekt najechania myszką (leciutko ciemniejszy żółty) */
        div.stButton > button:hover {
            background-color: #e6ab3b !important; 
            color: #003048 !important;
            border: 1px solid #e6ab3b !important;
        }
    </style>
""", unsafe_allow_html=True)
# Initialize local storage
localS = LocalStorage()
# Initialize LLM
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
ai_auditor = GroqMedicalScribe(api_key=GROQ_API_KEY)

# --- STATE MANAGEMENT ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'form_data' not in st.session_state:
    st.session_state.form_data = {k: None for k in ALL_KEYS_ORDERED}
if 'current_warning' not in st.session_state:
    st.session_state.current_warning = None
if 'aws_upload_started' not in st.session_state:
    st.session_state.aws_upload_started = False
if 'force_restore' not in st.session_state:
    st.session_state.force_restore = False
if 'step_validation_passed' not in st.session_state:
    st.session_state.step_validation_passed = False
if 'step_validation_passed' not in st.session_state:
    st.session_state.step_validation_passed = False
if 'validated_step_data' not in st.session_state:
    st.session_state.validated_step_data = None

# POTĘŻNY FIX: Wymuszone przywracanie stanu z sejfu (form_data) przy zmianie strony lub po załadowaniu draftu
if st.session_state.force_restore:
    for key, value in st.session_state.form_data.items():
        if value is not None:
            st.session_state[key] = value
    st.session_state.force_restore = False
else:
    for key, value in st.session_state.form_data.items():
        if value is not None and key not in st.session_state:
            st.session_state[key] = value

TOTAL_STEPS = 5

def save_step_data():
    for key in ALL_KEYS_ORDERED:
        if key in st.session_state:
            st.session_state.form_data[key] = st.session_state[key]
# ==========================================
# 💾 SIDEBAR:(LOCAL STORAGE)
# ==========================================
with st.sidebar:
    # --- LOGO FIRMOWE ---
    st.image("https://reemedical.com/wp-content/uploads/2025/05/REE-Medical-Header-Logo.png", use_container_width=True)
    st.divider() # Delikatna linia oddzielająca logo od reszty
    
    st.header("💾 Save & Resume")
    st.info("Save your progress to this browser and return later.")

    
    if st.button("Save Progress", use_container_width=True, type="primary"):
        save_step_data()
        draft_payload = {
            "step": st.session_state.step,
            "form_data": st.session_state.form_data
        }
        # Zapis do przeglądarki
        localS.setItem("dbq_draft", json.dumps(draft_payload))
        st.success("✅ Progress saved! You can safely close this tab.")
        
    st.divider()
    
    if st.button("Load Saved Progress", use_container_width=True):
        saved_draft = localS.getItem("dbq_draft")
        if saved_draft:
            try:
                # Parsowanie danych
                draft_dict = json.loads(saved_draft) if isinstance(saved_draft, str) else saved_draft
                
                # Wstrzyknięcie do sesji
                st.session_state.step = draft_dict.get("step", 1)
                st.session_state.form_data = draft_dict.get("form_data", {})
                st.session_state.current_warning = None
                st.session_state.aws_upload_started = False
                st.session_state.force_restore = True # <--- Dodana wymuszona odnowa
                
                st.success("✅ Draft loaded successfully!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error("Failed to load draft. Data might be corrupted.")
        else:
            st.warning("No saved progress found on this browser.")
            
    if st.button("Clear Current Answers", type="secondary", use_container_width=True):
        localS.deleteAll()
        st.session_state.clear()
        st.rerun()

# --- HELPER FUNCTIONS ---
def get_readable_step_data(global_fetch=False):
    readable_data = {}
    for key in ALL_KEYS_ORDERED:
        val = st.session_state.form_data.get(key) if global_fetch else st.session_state.get(key)
        if val not in [None, "", "--select--", "--select an item--"]:
            core_key = key.replace("Sinusitis__c.", "")
            label = QUESTION_MAP.get(core_key, core_key)
            readable_data[label] = val
    return readable_data

def proceed_to_next():
    save_step_data()
    st.session_state.current_warning = None
    st.session_state.step_validation_passed = False
    st.session_state.validated_step_data = None # Reset zdjęcia
    st.session_state.step += 1
    st.session_state.force_restore = True 

def prev_step():
    save_step_data()
    st.session_state.current_warning = None
    st.session_state.step_validation_passed = False
    st.session_state.validated_step_data = None # Reset zdjęcia
    st.session_state.step -= 1
    st.session_state.force_restore = True 

def attempt_validation(step_name, rules):
    save_step_data()
    step_data = get_readable_step_data()
    with st.spinner("Assistant is reviewing your answers..."):
        ai_response = ai_auditor.validate_step(step_name, rules, step_data)
        
    if ai_response == "PASS":
        st.session_state.current_warning = None
        st.session_state.step_validation_passed = True
        st.session_state.validated_step_data = step_data # <--- ROBIMY ZDJĘCIE POPRAWNYCH DANYCH
        st.rerun()
    else:
        st.session_state.current_warning = ai_response
        st.session_state.step_validation_passed = False
        st.session_state.validated_step_data = None
        st.rerun()

def render_navigation(step_name, rules, python_validation=None):
    st.divider()
    
    # --- MECHANIZM ODBIERANIA PRZEPUSTKI ---
    if st.session_state.get('step_validation_passed'):
        save_step_data() # Zaciągamy to, co weteran ma teraz na ekranie
        current_data = get_readable_step_data()
        # Jeśli obecne dane różnią się od zwalidowanego "zdjęcia", zabieramy przycisk
        if current_data != st.session_state.get('validated_step_data'):
            st.session_state.step_validation_passed = False
            st.session_state.validated_step_data = None
            st.session_state.current_warning = None # Czyścimy stare błędy, by zacząć na czysto
    # ---------------------------------------

    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.session_state.step > 1:
            st.button("Back", on_click=prev_step, use_container_width=True)
            
    with col2:
        if st.session_state.current_warning:
            st.warning(f"**Warning:**\n\n{st.session_state.current_warning}")
            st.info("You can fix the error and click 'Validate Again', or force continue.")
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Validate Again", type="primary", use_container_width=True):
                    if python_validation:
                        err = python_validation()
                        if err:
                            st.error(f"🛑 **Required Field Missing:** {err}")
                            return
                    attempt_validation(step_name, rules)
            with btn_col2:
                if st.button("Continue Anyway", type="secondary", use_container_width=True):
                    if python_validation:
                        err = python_validation()
                        if err:
                            st.error(f"🛑 **Cannot bypass:** {err}")
                            return
                    proceed_to_next()
                    st.rerun()
        else:
            if st.session_state.step_validation_passed:
                st.success("✅ Validation passed! Everything looks good.")
                if st.button("Proceed to Next Step", type="primary", use_container_width=True):
                    proceed_to_next()
                    st.rerun()
            else:
                if st.button("Validate Step", type="primary", use_container_width=True):
                    if python_validation:
                        err = python_validation()
                        if err:
                            st.error(f"🛑 **Required Field Missing:** {err}")
                            return
                    attempt_validation(step_name, rules)
# ==========================================
# STEP 1: INTRODUCTION & HISTORY
# ==========================================
if st.session_state.step == 1:
    st.title("Sinusitis DBQ: Introduction and History")
    
    st.info("""
    **Guidance for this section:**
    When writing your medical history, it is crucial to establish a timeline. 
    Be sure to mention:
    * **When** your symptoms first began (approximate year or deployment).
    * **How** the condition started and progressed.
    * **Link to service:** Where you were or what you were exposed to (e.g., burn pits, specific base).
    """)
    
    claim_selection = st.selectbox(
        "Are you applying for an initial claim or a re-evaluation?",
        ["--select an item--", "Initial Claim", "Re-evaluation for Existing"],
        key="Sinusitis__c.Sinusitis_1a__c"
    )

    if claim_selection != "--select an item--":
        st.markdown("Briefly describe the history of your sinus condition:")
        st.text_area(
            "History Area", 
            key="Sinusitis__c.Sinus_Q10c__c", 
            label_visibility="collapsed", 
            height=200
        )

    rules = """
    1. The user MUST select either "Initial Claim" or "Re-evaluation for Existing". If not selected, FAIL.
    2. If "Initial Claim" is selected, the 'Brief history' text MUST explicitly contain ALL THREE of these elements:
       - HOW the symptoms began (origin/progression).
       - WHEN the symptoms began (a date, year, or deployment period).
       - The LINK to military service (e.g., burn pits, a specific base, active duty).
    3. If "Re-evaluation for Existing" is selected, the 'Brief history' text MUST explicitly contain ALL TWO of these elements:
       - HOW the symptoms began.
       - WHEN the symptoms began.
    If ANY of the required elements based on their claim type are missing, FAIL and list exactly which elements are missing.
    """
    
    def validate_step_1():
        if st.session_state.get("Sinusitis__c.Sinusitis_1a__c") in [None, "--select an item--"]:
            return "You must select whether this is an Initial Claim or a Re-evaluation."
        if not st.session_state.get("Sinusitis__c.Sinus_Q10c__c", "").strip():
            return "The History Area cannot be entirely empty."
        return None

    if claim_selection != "--select an item--":
        render_navigation("History", rules, python_validation=validate_step_1)


# ==========================================
# STEP 2: MEDICATIONS
# ==========================================
elif st.session_state.step == 2:
    st.title("Medications")
    
    st.info("""
    **Guidance for this section:**
    List all medications you currently take for your sinus condition. This includes:
    * Prescription medications (e.g., antibiotics, strong steroids).
    * Over-the-counter (OTC) drugs (e.g., Flonase, Zyrtec, Claritin).
    
    Make sure to provide the exact Name, the Dosage (e.g., 50mcg, 10mg), and the Frequency (e.g., twice a day, as needed). Accuracy here demonstrates the severity of your ongoing treatment.
    """)
    
    med_trigger = st.radio("Do you currently take any medication(s)?", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q11__c")
    
    med_keys = [
        ("Sinusitis__c.Sinus_Q11aaa__c", "Sinusitis__c.Sinus_Q11aab__c", "Sinusitis__c.Sinus_Q11aac__c"),
        ("Sinusitis__c.Sinus_Q11aba__c", "Sinusitis__c.Sinus_Q11abb__c", "Sinusitis__c.Sinus_Q11abc__c"),
        ("Sinusitis__c.Sinus_Q11aca__c", "Sinusitis__c.Sinus_Q11acb__c", "Sinusitis__c.Sinus_Q11acc__c")
    ]
    
    if med_trigger == "Yes":
        num_meds = st.selectbox(
            "How many medications?", 
            ["--select--", "1", "2", "3", "More than 3"], 
            key="Sinusitis__c.Sinus_Q11a__c"
        )
        if num_meds != "--select--":
            for i, (name_key, dose_key, freq_key) in enumerate(med_keys, 1):
                if num_meds in [str(x) for x in range(i, 4)] or num_meds == "More than 3":
                    st.write(f"**Medication #{i}**")
                    c1, c2, c3 = st.columns(3)
                    with c1: st.text_input("Name", key=name_key)
                    with c2: st.text_input("Dosage", key=dose_key)
                    with c3: st.text_input("Frequency", key=freq_key)
            
            if num_meds == "More than 3":
                st.text_area("List additional medications (include Name, Dosage, and Frequency):", key="Sinusitis__c.Sinus_Q11b__c")

    def py_validate_meds():
        if st.session_state.get("Sinusitis__c.Sinus_Q11__c") == "Yes":
            n_meds = st.session_state.get("Sinusitis__c.Sinus_Q11a__c")
            if n_meds == "--select--":
                return "Please select the number of medications."
            
            count = 4 if n_meds == "More than 3" else int(n_meds)
            check_limit = min(count, 3)
            
            for i in range(check_limit):
                med_name = st.session_state.get(med_keys[i][0], "").strip()
                med_dose = st.session_state.get(med_keys[i][1], "").strip()
                med_freq = st.session_state.get(med_keys[i][2], "").strip()

                # Twarda walidacja nazwy
                if len(med_name) < 2: 
                    return f"Medication #{i+1} Name is missing or too short."
                
                # Twarda walidacja dawki
                if not med_dose: 
                    return f"Medication #{i+1} Dosage is missing."
                if med_dose.isdigit():
                    return f"Medication #{i+1} Dosage '{med_dose}' is invalid. You must include a unit (e.g., '10mg', '1 pill')."
                if len(med_dose) < 2:
                    return f"Medication #{i+1} Dosage '{med_dose}' is too short."

                # Twarda walidacja częstotliwości
                if not med_freq: 
                    return f"Medication #{i+1} Frequency is missing."
                if med_freq.isdigit():
                    return f"Medication #{i+1} Frequency cannot be just a number."
                if len(med_freq) < 3:
                     return f"Medication #{i+1} Frequency '{med_freq}' is too short. Please specify (e.g., 'daily', 'as needed')."
            
            if count == 4 and not st.session_state.get("Sinusitis__c.Sinus_Q11b__c", "").strip():
                 return "You selected 'More than 3' medications. Please list the additional ones in the text area."
        return None

    rules = """
    First, check if the Veteran answered "No" to 'Do you currently take any medication?'. If "No", output PASS immediately.
    
    If they answered "Yes", your ONLY job is to check the Medication Name:
    1. The Name MUST be a plausible, real-world medication, drug, or supplement (e.g., Tylenol, Lisinopril, Flonase, Vitamin C, Aspirin). 
    2. DO NOT judge if the medication is used for sinusitis. We accept ANY real medication.
    3. FAIL ONLY if the Name is obvious keyboard smash or completely fake (like 'asd', 'qwe', '123').
    4. Ignore strict rules for Dosage and Frequency. As long as the Name is a real-world drug/supplement, output PASS.
    """
    
    render_navigation("Medications", rules, python_validation=py_validate_meds)
# ==========================================
# STEP 3: SYMPTOMS & RATING SCHEDULE
# ==========================================
elif st.session_state.step == 3:
    st.title("Symptoms and Severity")
    
    st.info("""
    **Guidance for this section:**
    This section directly impacts your rating. 
    * **Symptoms & Affected Sinuses:** Select all that apply.
    * **Detailed Description:** You must write a paragraph explaining *every single symptom* and *affected sinus* you checked. Describe how the pain feels, how often the discharge occurs, etc.
    * **Non-incapacitating episodes:** Typical flare-ups (headaches, pain, discharge) that DO NOT require prolonged antibiotics or bed rest.
    * **Incapacitating episodes:** The VA defines this very strictly. It means requiring **bed rest prescribed by a physician AND treatment with antibiotics for 4 to 6 weeks**. If you just stayed home from work but did not require prolonged antibiotics, do not overstate this count.
    """)
    
    sc_trigger = st.radio("Are you service connected or seeking service connection for Sinusitis?", ["Yes", "No"], index=0, key="Sinusitis__c.Sinus_Q48__c")
    
    if sc_trigger == "Yes":
        st.multiselect(
            "Indicate the sinus/type of sinusitis currently affected by the chronic sinusitis:",
            ["Maxillary", "Frontal", "Ethmoid", "Sphenoid", "Pansinusitis", "Unknown"],
            key="Sinusitis__c.Sinus_Q34__c"
        )
        
        st.multiselect(
            "Select all sinus symptoms that apply:", 
            ["Crusting", "Discharge containing pus", "Headaches caused by sinusitis", "Near Constant Sinusitis", "Sinus pain", "Sinus tenderness"], 
            key="Sinusitis__c.Sinus_Q12__c"
        )
        
        st.markdown("**Please describe the symptoms you selected in detail:**")
        st.text_area(
            "Detailed Description Area", 
            key="Sinusitis__c.Sinus_Q14__c",
            label_visibility="collapsed",
            height=150
        )
        
        st.selectbox("Number of non-incapacitating episodes (headaches, pain, discharge, crusting) during the last 12 months:", ["--select--", "0", "1", "2", "3", "4", "5", "6", "7 or more"], key="Sinusitis__c.Sinus_Q15__c")
        st.selectbox("Number of incapacitating episodes (requiring 4-6 weeks of antibiotics) over the last 12 months:", ["--select--", "0", "1", "2", "3 or more"], key="Sinusitis__c.Sinus_Q16__c")

    rules = """
    Focus strictly on Symptoms and Severity. IGNORE ANY MENTIONS OF SURGERY IN THIS STEP.
    1. Cross-reference the 'Brief history' from Step 1. If 'Brief history' describes ongoing symptoms, but they selected "No" for 'Seeking service connection' or didn't check any symptoms here, FAIL.
    2. SYMPTOMS & SINUS CROSS-CHECK: Every symptom and affected sinus checked in the multiselects MUST be explicitly supported or described in the 'Detailed symptom description'. If a checked symptom or specific sinus (e.g., "Maxillary") is completely ignored in the text, or if the text contradicts the selected sinuses, FAIL.
    3. VAGUE ANSWER DETECTION: If the description is too generic (e.g., "I get bad headaches", "It hurts", "They are severe") without specific context like frequency, duration, or triggers, FAIL. Demand more specific functional details.
    4. EPISODES CROSS-CHECK: 
       - If the user selects > 0 for 'Incapacitating episodes', the text MUST explicitly mention physician-prescribed bed rest AND treatment with antibiotics for 4-6 weeks. If missing, FAIL.
       - If the user selects > 0 for 'Non-incapacitating episodes', the text MUST describe these regular flare-ups (headaches, discharge, etc.).
       - If they select '0' for both but describe constant severe flare-ups, or if they select multiple episodes but write "I feel fine", FAIL due to contradiction.
    5. GIBBERISH: If ANY text field contains gibberish ('asd', 'qwe'), FAIL.
    """
    
    def validate_step_3():
        sc_trig = st.session_state.get("Sinusitis__c.Sinus_Q48__c", "--select--")
        if sc_trig == "--select--":
            return "Please answer if you are seeking service connection."
            
        if sc_trig == "Yes":
            if not st.session_state.get("Sinusitis__c.Sinus_Q34__c"):
                return "Please indicate at least one affected sinus/type of sinusitis."
            if not st.session_state.get("Sinusitis__c.Sinus_Q12__c"):
                return "Please select at least one symptom."
            if not st.session_state.get("Sinusitis__c.Sinus_Q14__c", "").strip():
                return "Please describe your symptoms in detail."
            if st.session_state.get("Sinusitis__c.Sinus_Q15__c", "--select--") == "--select--":
                return "Please select the number of non-incapacitating episodes."
            if st.session_state.get("Sinusitis__c.Sinus_Q16__c", "--select--") == "--select--":
                return "Please select the number of incapacitating episodes."
        return None

    render_navigation("Symptoms", rules, python_validation=validate_step_3)
# ==========================================
# STEP 4: SURGERIES
# ==========================================
elif st.session_state.step == 4:
    st.title("Sinus Surgery")
    
    st.info("""
    **Guidance for this section:**
    If you have undergone any surgical procedures for your sinuses, document them here.
    * **Date:** An approximate Month and Year is sufficient if you do not remember the exact day.
    * **Findings:** Briefly explain what the surgeon did or discovered.
    """)
    
    surg_trigger = st.radio("Have you ever had sinus surgery?", [ "Yes", "No"], index=0, key="Sinusitis__c.Sinus_Q17__c")
    
    # Mapa kluczy TYLKO dla detali operacji (Date, Type, Findings)
    surg_keys = [
        ("Sinusitis__c.Sinus_Q17aaa__c", "Sinusitis__c.Sinus_Q17aaa1__c", "Sinusitis__c.Sinus_Q17aab__c"),
        ("Sinusitis__c.Sinus_Q17aba__c", "Sinusitis__c.Sinus_Q17aba1__c", "Sinusitis__c.Sinus_Q17abb__c"),
        ("Sinusitis__c.Sinus_Q17abc__c", "Sinusitis__c.Sinus_Q17abc1__c", "Sinusitis__c.Sinus_Q17aca__c"),
        ("Sinusitis__c.Sinus_Q17acb__c", "Sinusitis__c.Sinus_Q17acb1__c", "Sinusitis__c.Sinus_Q17acc__c")
    ]
    
    if surg_trigger == "Yes":
        num_surg = st.selectbox("How many sinus surgeries?", ["--select--", "1", "2", "3", "4", "More than 4"], key="Sinusitis__c.Sinus_Q17a__c")
        
        if num_surg != "--select--":
            count = 4 if num_surg == "More than 4" else int(num_surg)
            
            # Pętla generująca TYLKO operacje
            for i in range(count):
                date_key, type_key, findings_key = surg_keys[i]
                
                st.markdown(f"### Surgery #{i+1}")
                c1, c2 = st.columns(2)
                with c1: st.text_input("Date (MM/YYYY)", key=date_key, help="Must be exactly MM/YYYY (e.g., 05/2015)")
                with c2: st.selectbox("Type", ["--select--", "Radical", "Endoscopic"], key=type_key)
                
                st.markdown("Findings / Description:")
                st.text_area(f"Findings Area #{i+1}", key=findings_key, label_visibility="collapsed", height=68)
                st.divider()
                
            if num_surg == "More than 4":
                st.markdown("### Additional Surgeries")
                st.markdown("**Type of Sinus Surgery:**")
                st.markdown("If you have had more than four sinus surgeries please provide the following for each: Type of surgery and surgery date (month/year):")
                st.text_area("Additional Surgeries Area", key="Sinusitis__c.Sinus_Q17d__c", label_visibility="collapsed", height=100)
                st.divider()
            
            # GLOBALNE PYTANIA NA SAMYM DOLE SEKCJI OPERACJI
            st.markdown("### General Surgery Details")
            col_a, col_b = st.columns(2)
            with col_a: 
                st.selectbox("If known, what sinus was operated on?", ["--select--", "Maxillary", "Frontal", "Ethmoid", "Sphenoid", "Unknown"], key="Sinusitis__c.Sinus_Q17b__c")
            with col_b: 
                st.selectbox("Which side of your sinuses were operated on?", ["--select--", "Right", "Left", "Both"], key="Sinusitis__c.Sinus_Q17c__c")

    rules = """
    Focus strictly on Surgeries and perform a deep logical audit.
    1. HISTORY CHECK: If the Veteran explicitly mentioned sinus surgery or polyp removal in their 'Brief history' (Step 1), but selected "No" here, FAIL.
    2. CONTRADICTION CHECK (TYPE vs FINDINGS): Cross-reference the selected 'Type' (Radical or Endoscopic) with the text in 'Findings / Description' for EACH surgery. If the dropdown is 'Radical' but the text says 'endoscopic' (or vice versa), output FAIL and point out the exact contradiction.
    3. GLOBAL DROPDOWN CONSISTENCY: Look at the global answers for "Which sinus was operated on?" and "Which side...". If the individual 'Findings' texts mention specific sinuses or sides (e.g., "maxillary", "right side") that CONTRADICT the global dropdown selections, output FAIL.
    4. ADDITIONAL SURGERIES DETAILS: If 'More than 4' surgeries were selected, the 'Additional Surgeries (>4) Details' text MUST explicitly list both the 'Type' (e.g., endoscopic/radical) AND 'Date' (month/year) for the extra surgeries. If it only contains vague text without dates and types, FAIL.
    5. GIBBERISH: If ANY text field contains gibberish ('asd', 'qwe'), FAIL.
    """
    
    def validate_step_4():
        surg_trig = st.session_state.get("Sinusitis__c.Sinus_Q17__c", "--select--")
        if surg_trig == "--select--":
            return "Please answer if you have ever had sinus surgery."
            
        if surg_trig == "Yes":
            num_surg = st.session_state.get("Sinusitis__c.Sinus_Q17a__c", "--select--")
            if num_surg == "--select--":
                return "Please select how many sinus surgeries you have had."
                
            count = 4 if num_surg == "More than 4" else int(num_surg)
            
            for i in range(count):
                date_key, type_key, findings_key = surg_keys[i]
                
                date_str = st.session_state.get(date_key, "").strip()
                if not date_str:
                    return f"Surgery #{i+1} Date is required."
                if not re.match(r"^(0[1-9]|1[0-2])\/\d{4}$", date_str):
                    return f"Surgery #{i+1} Date MUST be strictly in MM/YYYY format (e.g., 05/2015)."
                    
                s_type = st.session_state.get(type_key, "--select--")
                if s_type == "--select--":
                    return f"Surgery #{i+1} Type is required. Please select Radical or Endoscopic."
                    
                if not st.session_state.get(findings_key, "").strip():
                    return f"Surgery #{i+1} Findings description cannot be empty."
                    
            if num_surg == "More than 4":
                if not st.session_state.get("Sinusitis__c.Sinus_Q17d__c", "").strip():
                    return "You selected 'More than 4' surgeries. Please provide details in the Additional Surgeries text area."
            
            # NOWE: Twarda walidacja globalnych dropdownów na dole
            if st.session_state.get("Sinusitis__c.Sinus_Q17b__c", "--select--") == "--select--":
                return "Please select which sinus was operated on (or select 'Unknown')."
            if st.session_state.get("Sinusitis__c.Sinus_Q17c__c", "--select--") == "--select--":
                return "Please select which side of your sinuses were operated on."
                
        return None

    render_navigation("Surgeries", rules, python_validation=validate_step_4)
# ==========================================
# STEP 5: FINAL DETAILS & SUBMIT
# ==========================================
elif st.session_state.step == 5:
    st.title("Final Details and Submission")
    
    st.info("""
    **Guidance for this section:**
    The Occupational Impact section is critical for establishing how your condition affects your daily life and livelihood. 
    Do not just write "It hurts." Explain:
    * If you have to take sick days.
    * If headaches prevent you from looking at screens or focusing.
    * If environmental factors at work (dust, AC, chemicals) exacerbate your symptoms.
    """)
    
    st.markdown("Regardless of your current employment status, how does your sinus condition affect your ability to work?")
    st.text_area("Occupational Impact Area", key="Sinusitis__c.Sinus_Q21__c", label_visibility="collapsed", height=150)
    
    # --- AUTO-WYPEŁNIANIE DATY ---
    today_str = datetime.now().strftime("%m/%d/%Y")
    # Jeśli pole daty jest puste (weteran wszedł tu pierwszy raz), wklejamy dzisiejszą datę
    if not st.session_state.get("Sinusitis__c.Date_Submitted__c"):
        st.session_state["Sinusitis__c.Date_Submitted__c"] = today_str
        st.session_state.form_data["Sinusitis__c.Date_Submitted__c"] = today_str

    st.text_input("Veteran Name:", key="Sinusitis__c.DBQ__c.Veteran_Name_Text__c", help="Enter your full legal name (First and Last).")
    st.text_input("Date Submitted (MM/DD/YYYY):", key="Sinusitis__c.Date_Submitted__c", help="This is automatically set to today's date.")
    
    st.divider()
    
    # Inicjalizacja flagi sterującej pełnoekranowym uploadem
    # Inicjalizacja flagi sterującej pełnoekranowym uploadem
    if 'aws_upload_triggered' not in st.session_state:
        st.session_state.aws_upload_triggered = False
        
    # NOWA FLAGA: Blokuje przycisk Submit do czasu udanej walidacji
    if 'final_validation_passed' not in st.session_state:
        st.session_state.final_validation_passed = False

    def generate_tailored_json():
        case_id = ''.join(random.choices(string.digits, k=6))
        output = {"caseID": case_id, "DBQType": "sinus", "DPA": {}}
        for key in ALL_KEYS_ORDERED:
            core_key = key.replace("Sinusitis__c.", "")
            value = st.session_state.form_data.get(key, None)
            output["DPA"][core_key] = {"Question": QUESTION_MAP.get(core_key, core_key), "Answer": value}
        return json.dumps(output, indent=4)

    # TWARDA WALIDACJA KROKU 5
    def validate_step_5():
        # Walidacja Imienia i Nazwiska
        name = st.session_state.get("Sinusitis__c.DBQ__c.Veteran_Name_Text__c", "").strip()
        if not name:
            return "Veteran Name is strictly required to sign and submit this document."
        
        # Sprawdzamy, czy są minimum 2 słowa i czy są to tylko litery/myślniki/apostrofy (bez cyfr i znaków specjalnych)
        if len(name.split()) < 2 or not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\-\' ]+$", name):
            return "Please enter your full legal name (First and Last Name). Numbers or special characters are not allowed."

        # Walidacja Daty
        date_str = st.session_state.get("Sinusitis__c.Date_Submitted__c", "").strip()
        if not date_str:
            return "Date Submitted is strictly required."
            
        # Twarde wymuszenie samego formatu MM/DD/YYYY (żeby regex nie przepuścił bzdur)
        if not re.match(r"^(0[1-9]|1[0-2])\/(0[1-9]|[12]\d|3[01])\/\d{4}$", date_str):
            return "Date Submitted MUST be exactly in MM/DD/YYYY format (e.g., 12/25/2024)."
            
        # Twarde wymuszenie DZISIEJSZEJ daty
        today_str = datetime.now().strftime("%m/%d/%Y")
        if date_str != today_str:
            return f"Date Submitted MUST be exactly today's date ({today_str}). Past or future dates are invalid."
            
        return None

    # 1. POKAZUJEMY PRZYCISKI TYLKO, JEŚLI WYSYŁKA JESZCZE NIE RUSZYŁA
    if not st.session_state.aws_upload_triggered:
        col1, col2 = st.columns([1, 4])
        with col1: 
            if st.button("Back", use_container_width=True):
                st.session_state.final_validation_passed = False # Resetujemy flagę przy cofaniu
                prev_step()
                st.rerun()
                
        with col2:
            if st.session_state.current_warning:
                st.warning(f"**Consistency Check Warning:**\n\n{st.session_state.current_warning}")
                st.info("You can go back to fix the errors, or submit the form anyway.")
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("Re-evaluate Full Form", type="primary", use_container_width=True):
                        err = validate_step_5()
                        if err:
                            st.error(f"🛑 {err}")
                        else:
                            st.session_state.current_warning = None
                            st.session_state.final_validation_passed = False
                            st.rerun()
                with btn_col2:
                    if st.button("Submit Anyway", type="secondary", use_container_width=True):
                        err = validate_step_5()
                        if err:
                            st.error(f"🛑 Cannot bypass: {err}")
                        else:
                            st.session_state.aws_upload_triggered = True
                            st.rerun()
            else:
                # TUTAJ ZASZŁA ZMIANA: Podział na Validate i Submit
                if st.session_state.final_validation_passed:
                    st.success("✅ Audit passed! No logical contradictions found. Your form is ready.")
                    if st.button("Submit", type="primary", use_container_width=True):
                        st.session_state.aws_upload_triggered = True
                        st.rerun()
                else:
                    if st.button("Validate Full Form", type="primary", use_container_width=True):
                        err = validate_step_5()
                        if err:
                            st.error(f"🛑 **Required Field Missing:** {err}")
                        else:
                            save_step_data()
                            
                            # GLOBAL VALIDATION
                            # GLOBAL VALIDATION
                            global_rules = """
                            You are performing a STRICT global consistency audit across all form sections. Cross-reference the narrative in 'Brief history' with the answers in the rest of the form.
                            
                            CRITICAL CHECKS:
                            1. VAGUE OCCUPATIONAL IMPACT (CRITICAL): Evaluate the text in 'Occupational Impact'. If the answer is generic, extremely short, or gibberish (e.g., "It hurts", "asd", "bad", "no impact"), you MUST output FAIL. Demand that the Veteran explain exactly how the symptoms (like sick days, lack of focus, environmental triggers) affect their daily ability to work.
                            2. SYMPTOMS CONTRADICTION: If the Veteran selected "No" for 'Seeking service connection?' or listed no symptoms, but their 'Brief history' explicitly describes ongoing pain, congestion, or other symptoms, output FAIL and warn them.
                            3. SURGERY CONTRADICTION: If the Veteran selected "No" for 'Ever had sinus surgery?', but their 'Brief history' mentions having an operation or sinus surgery, output FAIL.
                            4. SEVERITY CONTRADICTION: Check if the 'Occupational Impact' contradicts the 'Incapacitating episodes' (e.g., claiming 0 episodes but stating they are completely bedridden for weeks in the impact section).
                            
                            If ANY of these logical contradictions or vague answers are found, output FAIL and explicitly state what needs correction. Otherwise, output PASS.
                            """
                            
                            with st.spinner("AI is performing a final global consistency check..."):
                                full_form_data = get_readable_step_data(global_fetch=True)
                                ai_response = ai_auditor.validate_step("Global Full Form Audit", global_rules, full_form_data)
                            
                            if ai_response == "PASS":
                                st.session_state.final_validation_passed = True
                                st.rerun()
                            else:
                                st.session_state.current_warning = ai_response
                                st.rerun()

    # 2. LOGIKA WYSYŁKI AWS NA PEŁNEJ SZEROKOŚCI EKRANU (Poza kolumnami)
    if st.session_state.aws_upload_triggered:
        save_step_data()
        json_string = generate_tailored_json()
        
        with st.status("Uploading...", expanded=True) as status:
            filename = f"DBQ_Sinus_{json.loads(json_string)['caseID']}.json"
            success = upload_to_source(json_string, filename)
            
            if success:
                status.write("Upload complete. Triggering job...")
                result_data = poll_output_bucket(filename)
                
                if result_data:
                    status.update(label="Processing Complete!", state="complete", expanded=False)
                    st.divider()
                    st.subheader("🎉 Processing Result")
                    # Wynik z AWS zostawiamy w czytelnym bloku kodu na całą szerokość
                    formatted_result = json.dumps(result_data, indent=4)
                    st.code(formatted_result, language="json")
                else:
                    status.update(label="Processing Failed or Timed Out", state="error")
            else:
                status.update(label="Upload Failed", state="error")
                
        # Zawsze dobrze dać użytkownikowi opcję zresetowania stanu po wysyłce
        st.divider()
        if st.button("Start New Form"):
            st.session_state.clear()
            st.rerun()
