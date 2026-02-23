import streamlit as st
import json
import requests
import random
import string
import boto3
import time
from botocore.exceptions import ClientError

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
            "response_format": {"type": "json_object"}, # Forces Groq to output clean JSON
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
            Bucket=bucket_name, 
            Key=s3_key, 
            Body=json_data, 
            ContentType='application/json'
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
        placeholder.info(f"AWS is processing... polling will start in {i} seconds.")
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
            
    placeholder.error("Timeout: AWS took too long to process the file.")
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
    "Sinusitis__c.Sinus_Q17__c", "Sinusitis__c.Sinus_Q17a__c", "Sinusitis__c.Sinus_Q17aaa__c",
    "Sinusitis__c.Sinus_Q17aaa1__c", "Sinusitis__c.Sinus_Q17aab__c", "Sinusitis__c.Sinus_Q17aba__c",
    "Sinusitis__c.Sinus_Q17aba1__c", "Sinusitis__c.Sinus_Q17abb__c", "Sinusitis__c.Sinus_Q17abc__c",
    "Sinusitis__c.Sinus_Q17abc1__c", "Sinusitis__c.Sinus_Q17aca__c", "Sinusitis__c.Sinus_Q17acb__c",
    "Sinusitis__c.Sinus_Q17acb1__c", "Sinusitis__c.Sinus_Q17acc__c", "Sinusitis__c.Sinus_Q17b__c",
    "Sinusitis__c.Sinus_Q17c__c", "Sinusitis__c.Sinus_Q17d__c", "Sinusitis__c.Sinus_Q20__c",
    "Sinusitis__c.Sinus_Q20a__c", "Sinusitis__c.Sinus_Q20b__c", "Sinusitis__c.Sinus_Q20c__c",
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
    "Sinus_Q34__c": "Sinuses affected",
    "Sinus_Q12__c": "Symptoms checklist",
    "Sinus_Q14__c": "Detailed symptom description",
    "Sinus_Q15__c": "Non-incapacitating episodes (12mo)",
    "Sinus_Q16__c": "Incapacitating episodes (12mo)",
    "Sinus_Q17__c": "Ever had sinus surgery?",
    "Sinus_Q17a__c": "How many sinus surgeries?",
    "Sinus_Q21__c": "Occupational Impact"
}

# --- APP CONFIG ---
st.set_page_config(page_title="Sinusitis DBQ Validation", layout="centered")

# Initialize LLM with Groq Secrets
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
ai_auditor = GroqMedicalScribe(api_key=GROQ_API_KEY)

# --- STATE MANAGEMENT ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'form_data' not in st.session_state:
    st.session_state.form_data = {k: None for k in ALL_KEYS_ORDERED}

# 💡 ZMIANA: Pętla przywracająca stan formularza przy przechodzeniu "Wstecz"
for key, value in st.session_state.form_data.items():
    if value is not None and key not in st.session_state:
        st.session_state[key] = value

TOTAL_STEPS = 5

def save_step_data():
    for key in ALL_KEYS_ORDERED:
        if key in st.session_state:
            st.session_state.form_data[key] = st.session_state[key]

def get_readable_step_data():
    readable_data = {}
    for key in ALL_KEYS_ORDERED:
        if key in st.session_state and st.session_state[key] not in [None, "", "--select--", "--select an item--"]:
            core_key = key.replace("Sinusitis__c.", "")
            label = QUESTION_MAP.get(core_key, core_key)
            readable_data[label] = st.session_state[key]
    return readable_data

def handle_next_step(step_name, rules):
    save_step_data()
    step_data = get_readable_step_data()
    
    with st.spinner("Assistant is reviewing your answers..."):
        ai_response = ai_auditor.validate_step(step_name, rules, step_data)
        
    if ai_response == "PASS":
        st.session_state.step += 1
        st.rerun()
    else:
        st.error("Assistant's Suggestion:")
        st.info(ai_response)

def prev_step():
    save_step_data()
    st.session_state.step -= 1

st.progress(st.session_state.step / TOTAL_STEPS)

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
    * **Where** you were or what you were exposed to (e.g., burn pits, specific base).
    * **How** the condition has progressed since your service.
    
    A strong, detailed narrative here forms the foundation of your claim.
    """)
    
    claim_selection = st.selectbox(
        "Are you applying for an initial claim or a re-evaluation? *",
        ["--select an item--", "Initial Claim", "Re-evaluation for Existing"],
        key="Sinusitis__c.Sinusitis_1a__c"
    )

    if claim_selection != "--select an item--":
        st.markdown("**Briefly describe the history of your sinus condition:**")
        st.text_area(
            "History Area", 
            key="Sinusitis__c.Sinus_Q10c__c", 
            label_visibility="collapsed", 
            height=200
        )

    st.divider()
    if st.button("Next Step", type="primary"):
        rules = """
        1. The user must select either "Initial Claim" or "Re-evaluation".
        2. The 'Brief history of sinus condition' must contain a coherent narrative detailing the origin or progression of the condition. It cannot be just 1-2 words.
        """
        handle_next_step("History", rules)

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
    
    med_trigger = st.radio("Do you currently take any medication(s)? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q11__c")
    
    med_keys = [
        ("Sinusitis__c.Sinus_Q11aaa__c", "Sinusitis__c.Sinus_Q11aab__c", "Sinusitis__c.Sinus_Q11aac__c"),
        ("Sinusitis__c.Sinus_Q11aba__c", "Sinusitis__c.Sinus_Q11abb__c", "Sinusitis__c.Sinus_Q11abc__c"),
        ("Sinusitis__c.Sinus_Q11aca__c", "Sinusitis__c.Sinus_Q11acb__c", "Sinusitis__c.Sinus_Q11acc__c")
    ]
    
    if med_trigger == "Yes":
        num_meds = st.selectbox(
            "How many medications? *", 
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

    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1: st.button("Back", on_click=prev_step)
    with col2:
        if st.button("Next Step", type="primary"):
            save_step_data()
            
            # Hard Python Validation
            validation_passed = True
            error_msg = ""
            
            if st.session_state.get("Sinusitis__c.Sinus_Q11__c") == "Yes":
                n_meds = st.session_state.get("Sinusitis__c.Sinus_Q11a__c")
                if n_meds == "--select--":
                    validation_passed = False
                    error_msg = "Please select the number of medications."
                else:
                    count = 4 if n_meds == "More than 3" else int(n_meds)
                    check_limit = min(count, 3)
                    
                    for i in range(check_limit):
                        name_val = st.session_state.get(med_keys[i][0], "").strip()
                        dose_val = st.session_state.get(med_keys[i][1], "").strip()
                        freq_val = st.session_state.get(med_keys[i][2], "").strip()
                        
                        if not name_val:
                            validation_passed = False
                            error_msg = f"Medication #{i+1} Name is missing."
                            break
                        if not dose_val:
                            validation_passed = False
                            error_msg = f"Medication #{i+1} Dosage is missing. Please specify the amount."
                            break
                        if not freq_val:
                            validation_passed = False
                            error_msg = f"Medication #{i+1} Frequency is missing. Please specify how often it is taken."
                            break
                    
                    if validation_passed and count == 4:
                        if not st.session_state.get("Sinusitis__c.Sinus_Q11b__c", "").strip():
                             validation_passed = False
                             error_msg = "You selected 'More than 3' medications. Please list the additional ones in the text area."

            if not validation_passed:
                st.error("Form Validation Error:")
                st.info(error_msg)
            else:
                step_data = get_readable_step_data()
                rules = """
                Check if the provided medication names, dosages, and frequencies sound like valid medical treatments. 
                If they wrote absolute gibberish (e.g., Name: 'asd', Dosage: 'xyz'), output an error hint.
                Otherwise, PASS.
                """
                
                with st.spinner("Assistant is reviewing your answers..."):
                    ai_response = ai_auditor.validate_step("Medications", rules, step_data)
                    
                if ai_response == "PASS":
                    st.session_state.step += 1
                    st.rerun()
                else:
                    st.error("Assistant's Suggestion:")
                    st.info(ai_response)
                    
# ==========================================
# STEP 3: SYMPTOMS & RATING SCHEDULE
# ==========================================
elif st.session_state.step == 3:
    st.title("Symptoms and Severity")
    
    st.info("""
    **Guidance for this section:**
    This section directly impacts your rating. 
    * **Symptoms Checklist:** Only select symptoms you currently experience.
    * **Detailed Description:** You must write a paragraph explaining *every single symptom* you checked above. Describe how the pain feels, how often the discharge occurs, etc.
    * **Incapacitating Episodes:** The VA defines "incapacitating" very strictly. It means requiring **bed rest prescribed by a physician AND treatment with antibiotics for 4 to 6 weeks**. If you just stayed home from work but did not require prolonged antibiotics, do not overstate this count.
    """)
    
    sc_trigger = st.radio("Are you seeking service connection for Sinusitis? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q48__c")
    if sc_trigger == "Yes":
        st.multiselect(
            "Select all sinus symptoms that apply: *", 
            ["Near Constant Sinusitis", "Headaches caused by sinusitis", "Sinus pain", "Discharge containing pus", "Crusting"], 
            key="Sinusitis__c.Sinus_Q12__c"
        )
        st.markdown("**Please describe the symptoms you selected in detail: ***")
        st.text_area(
            "Detailed Description Area", 
            key="Sinusitis__c.Sinus_Q14__c",
            label_visibility="collapsed",
            height=150
        )
        
        st.selectbox("Incapacitating episodes (last 12 months): *", ["0", "1", "2", "3 or more"], key="Sinusitis__c.Sinus_Q16__c")

    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1: st.button("Back", on_click=prev_step)
    with col2:
        if st.button("Next Step", type="primary"):
            rules = """
            1. Every symptom checked in the 'Symptoms checklist' MUST be explicitly mentioned or described in the 'Detailed symptom description' text area. If a checked symptom is missing from the description, ask them to add it.
            2. Check for contradictions regarding incapacitating episodes. If the text description mentions "staying in bed", "bed rest", or "missing weeks of work", but 'Incapacitating episodes' is '0', warn them that their text implies incapacitation while their numerical selection is 0.
            """
            handle_next_step("Symptoms", rules)

# ==========================================
# STEP 4: SURGERIES
# ==========================================
elif st.session_state.step == 4:
    st.title("Sinus Surgery")
    
    st.info("""
    **Guidance for this section:**
    If you have undergone any surgical procedures for your sinuses, document them here.
    * **Date:** An approximate Month and Year is sufficient if you do not remember the exact day.
    * **Findings:** Briefly explain what the surgeon did or discovered (e.g., "Removed nasal polyps and widened the sinus passages"). This shows the severity of the intervention required.
    """)
    
    surg_trigger = st.radio("Have you ever had sinus surgery? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q17__c")
    if surg_trigger == "Yes":
        num_surg = st.selectbox("How many sinus surgeries?", ["1", "2", "3", "4", "More than 4"], key="Sinusitis__c.Sinus_Q17a__c")
        c1, c2 = st.columns(2)
        with c1: st.text_input("Date (MM/YYYY)", key="Sinusitis__c.Sinus_Q17aaa__c")
        with c2: st.selectbox("Type", ["Radical", "Endoscopic"], key="Sinusitis__c.Sinus_Q17aaa1__c")
        
        st.markdown("**Findings:**")
        st.text_area(
            "Findings Area", 
            key="Sinusitis__c.Sinus_Q17aab__c",
            label_visibility="collapsed"
        )

    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1: st.button("Back", on_click=prev_step)
    with col2:
        if st.button("Next Step", type="primary"):
            rules = "If the Veteran selected 'Yes' for surgery, they MUST provide the surgery Date, Type, and write a coherent description in 'Findings'. If 'Findings' is empty or too short, ask them to describe the outcome of the surgery."
            handle_next_step("Surgeries", rules)

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
    
    st.markdown("**Regardless of your current employment status, how does your sinus condition affect your ability to work? ***")
    st.text_area(
        "Occupational Impact Area", 
        key="Sinusitis__c.Sinus_Q21__c", 
        label_visibility="collapsed",
        height=150
    )
    st.text_input("Veteran Name: *", key="Sinusitis__c.DBQ__c.Veteran_Name_Text__c")
    st.text_input("Date Submitted (MM/DD/YYYY): *", key="Sinusitis__c.Date_Submitted__c")
    
    st.divider()
    
    def generate_tailored_json():
        case_id = ''.join(random.choices(string.digits, k=6))
        output = {"caseID": case_id, "DBQType": "sinus", "DPA": {}}
        for key in ALL_KEYS_ORDERED:
            core_key = key.replace("Sinusitis__c.", "")
            value = st.session_state.form_data.get(key, None)
            output["DPA"][core_key] = {"Question": QUESTION_MAP.get(core_key, core_key), "Answer": value}
        return json.dumps(output, indent=4)

    col1, col2 = st.columns([1, 4])
    with col1: 
        st.button("Back", on_click=prev_step)
    
    if st.session_state.get("Sinusitis__c.Sinus_Q21__c") and st.session_state.get("Sinusitis__c.DBQ__c.Veteran_Name_Text__c"):
        json_string = generate_tailored_json()
        
        if st.button("Validate and Submit to AWS", type="primary"):
            with st.status("Final Validation and Upload...", expanded=True) as status:
                rules = "The Occupational Impact must explain how the condition affects work. The Veteran Name and Date must be filled."
                ai_response = ai_auditor.validate_step("Final Details", rules, get_readable_step_data())
                
                if ai_response == "PASS":
                    status.write("AI Validation Passed.")
                    status.write("Uploading to S3...")
                    
                    filename = f"DBQ_Sinus_{json.loads(json_string)['caseID']}.json"
                    success = upload_to_source(json_string, filename)
                    
                    if success:
                        status.write("Upload complete. Triggering AWS job...")
                        status.write(f"Polling output bucket for '{filename}'...")
                        
                        result_data = poll_output_bucket(filename)
                        
                        if result_data:
                            status.update(label="Processing Complete!", state="complete", expanded=False)
                            st.divider()
                            st.subheader("AWS Processing Result")
                            st.json(result_data)
                        else:
                            status.update(label="Processing Failed or Timed Out", state="error")
                    else:
                        status.update(label="Upload Failed", state="error")
                else:
                    status.update(label="Validation Error", state="error")
                    st.error("Assistant's Suggestion:")
                    st.info(ai_response)
