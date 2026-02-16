import streamlit as st
import json
import requests

# --- GROQ AI AUDITOR ---
class GroqMedicalAuditor:
    def __init__(self, api_key, model="llama-3.3-70b-versatile"):
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.api_key = api_key
        self.model = model

    def cross_check_logic(self, data):
        if not self.api_key:
            return "❌ Groq API Key missing in Secrets."

        # The prompt specifically targets your typed history vs listed meds mismatch
        prompt = f"""
        [SYSTEM: VA CLAIMS AUDITOR. STRICT DATA RECONCILIATION ONLY.]
        
        INPUT DATA:
        {data}

        MANDATORY CHECKLIST:
        1. Mismatched Counts: Scan 'Sinus_Q10c__c' (History) for numbers (e.g. "two", "2"). Compare this to the count of medications provided in 'Sinus_Q11aaa__c', 'Sinus_Q11aba__c', 'Sinus_Q11aca__c'.
           - IF USER SAYS "I take two" BUT ONLY LISTS 0 OR 1, YOU MUST FLAG THIS.
        2. Unchecked Symptoms: If 'Sinus_Q14__c' mentions specific issues like 'pus', 'pain', or 'headaches', but those boxes are NOT checked in 'Sinus_Q12__c', flag it.
        3. Rating Trap: If 'Sinus_Q16__c' is '0' but text describes being unable to work or bed rest, warn the user.
        4. Empty Fields: If surgery is checked but 'Findings' text is empty, flag it.

        OUTPUT STRUCTURE:
        ### 🚩 LOGICAL CONFLICTS
        - [Specific mismatch]
        ### 💡 MISSING DETAILS
        - [Checked boxes with no text]
        ### 🩺 CLINICAL REFINEMENT
        - [User Term] -> [Clinical Term]
        """
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": "You are a literal data validator. No summaries."},
                         {"role": "user", "content": prompt}],
            "temperature": 0.0
        }
        try:
            res = requests.post(self.url, json=payload, headers=headers, timeout=25)
            return res.json()['choices'][0]['message']['content']
        except:
            return "❌ Groq Connection Error."

st.set_page_config(page_title="Complete Sinusitis DBQ", layout="wide")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
auditor = GroqMedicalAuditor(GROQ_API_KEY)

st.title("Chronic Sinusitis Questionnaire")

# --- YOUR ORIGINAL FORM START ---
claim_selection = st.selectbox(
    "Are you applying for an initial claim or a re-evaluation for an existing service-connected disability? *",
    ["--select an item--", "Initial Claim", "Re-evaluation for Existing"],
    key="Sinusitis__c.Sinusitis_1a__c"
)

if claim_selection != "--select an item--":
    h_label = "Briefly describe the history of your sinus condition, including how and when your symptoms began and the link between your injury and military service." if claim_selection == "Initial Claim" else "Briefly describe the history of your sinus condition, including how and when your symptoms began:"
    st.markdown(f"**{h_label}**")
    st.text_area("History Area", key="Sinusitis__c.Sinus_Q10c__c", label_visibility="collapsed")

    st.markdown("---")
    med_trigger = st.radio("Do you currently take any medication(s)? *", ["Yes", "No"], index=1, horizontal=True, key="Sinusitis__c.Sinus_Q11__c")
    if med_trigger == "Yes":
        num_meds = st.selectbox("How many medications? *", ["--select--", "1", "2", "3", "More than 3"], key="Sinusitis__c.Sinus_Q11a__c")
        if num_meds != "--select--":
            for i, (name_key, dose_key, freq_key) in enumerate([
                ("Sinusitis__c.Sinus_Q11aaa__c", "Sinusitis__c.Sinus_Q11aab__c", "Sinusitis__c.Sinus_Q11aac__c"),
                ("Sinusitis__c.Sinus_Q11aba__c", "Sinusitis__c.Sinus_Q11abb__c", "Sinusitis__c.Sinus_Q11abc__c"),
                ("Sinusitis__c.Sinus_Q11aca__c", "Sinusitis__c.Sinus_Q11acb__c", "Sinusitis__c.Sinus_Q11acc__c")
            ], 1):
                if num_meds in [str(x) for x in range(i, 4)] or num_meds == "More than 3":
                    st.write(f"**Medication #{i}**")
                    c1, c2, c3 = st.columns(3)
                    with c1: st.text_input("Name", key=name_key)
                    with c2: st.text_input("Dosage", key=dose_key)
                    with c3: st.text_input("Frequency", key=freq_key)
            if num_meds == "More than 3":
                st.text_area("List each additional medication(s) AND dosages/frequency:", key="Sinusitis__c.Sinus_Q11b__c")

    st.markdown("---")
    sc_trigger = st.radio("Are you service connected or seeking service connection for Sinusitis? *", ["Yes", "No"], index=1, horizontal=True, key="Sinusitis__c.Sinus_Q48__c")
    if sc_trigger == "Yes":
        st.multiselect("Indicate the sinus currently affected: *", ["Maxillary", "Frontal", "Ethmoid", "Sphenoid", "Pansinusitus", "Unknown"], key="Sinusitis__c.Sinus_Q34__c")
        symp_list = st.multiselect("Select all sinus symptoms that apply: *", ["Near Constant Sinusitis", "Headaches caused by sinusitis", "Sinus pain", "Sinus tenderness", "Discharge containing pus", "Crusting"], key="Sinusitis__c.Sinus_Q12__c")
        if "Near Constant Sinusitis" in symp_list:
            st.selectbox("Near constant sinusitis frequency: *", ["Daily", "5-6 days per week", "3-4 days per week"], key="Sinusitis__c.Sinus_Q13__c")
        st.text_area("Please describe the symptoms you selected in detail: *", key="Sinusitis__c.Sinus_Q14__c")
        st.selectbox("Non-incapacitating episodes (last 12 months): *", ["1", "2", "3", "4", "5", "6", "7 or more"], key="Sinusitis__c.Sinus_Q15__c")
        st.selectbox("Incapacitating episodes (last 12 months): *", ["0", "1", "2", "3 or more"], key="Sinusitis__c.Sinus_Q16__c")

        surg_trigger = st.radio("Have you ever had sinus surgery? *", ["Yes", "No"], index=1, horizontal=True, key="Sinusitis__c.Sinus_Q17__c")
        if surg_trigger == "Yes":
            num_surg = st.selectbox("How many sinus surgeries have you had?", ["1", "2", "3", "4", "More than 4"], key="Sinusitis__c.Sinus_Q17a__c")
            for i, (date_k, type_k, find_k) in enumerate([
                ("Sinusitis__c.Sinus_Q17aaa__c", "Sinusitis__c.Sinus_Q17aaa1__c", "Sinusitis__c.Sinus_Q17aab__c"),
                ("Sinusitis__c.Sinus_Q17aba__c", "Sinusitis__c.Sinus_Q17aba1__c", "Sinusitis__c.Sinus_Q17abb__c"),
                ("Sinusitis__c.Sinus_Q17abc__c", "Sinusitis__c.Sinus_Q17abc1__c", "Sinusitis__c.Sinus_Q17aca__c"),
                ("Sinusitis__c.Sinus_Q17acb__c", "Sinusitis__c.Sinus_Q17acb1__c", "Sinusitis__c.Sinus_Q17acc__c")
            ], 1):
                if num_surg in [str(x) for x in range(i, 5)] or num_surg == "More than 4":
                    st.write(f"**Surgery #{i}**")
                    c1, c2 = st.columns(2)
                    with c1: st.text_input("Date (MM/YYYY)", key=date_k)
                    with c2: st.selectbox("Type", ["Radical", "Endoscopic"], key=type_k)
                    st.text_area("Findings", key=find_k)
            if num_surg == "More than 4":
                st.text_area("List additional surgery details:", key="Sinusitis__c.Sinus_Q17b__c")
            st.multiselect("Sinus operated on:", ["Maxillary", "Frontal", "Ethmoid", "Sphenoid", "Pansinusitus", "Unknown"], key="Sinusitis__c.Sinus_Q17c__c")
            st.selectbox("Side operated on:", ["Left", "Right", "Both"], key="Sinusitis__c.Sinus_Q17d__c")

st.header("Rhinitis")
if st.radio("Seeking connection for rhinitis? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q20__c") == "Yes":
    st.radio("Blockage in >50% both nasal passages?", ["Yes", "No"], key="Sinusitis__c.Sinus_Q20a__c")
    st.selectbox("Complete blockage side?", ["No", "Yes, Right side", "Yes, Left side", "Yes, both"], key="Sinusitis__c.Sinus_Q20b__c")
    st.radio("Permanent enlargement of nasal turbinates?", ["Yes", "No"], key="Sinusitis__c.Sinus_Q20c__c")
    st.radio("Diagnosed with nasal polyps?", ["Yes", "No"], key="Sinusitis__c.Sinus_Q20d__c")

st.header("Larynx and Pharynx Conditions")
if st.radio("Do you have chronic laryngitis? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q35__c") == "Yes":
    lar_s = st.multiselect("Symptoms:", ["Hoarseness", "Inflammation", "Polyps", "Other"], key="Sinusitis__c.Sinus_Q35a__c")
    if "Hoarseness" in lar_s: st.text_area("Describe frequency:", key="Sinusitis__c.Sinus_Q35b__c")
    if "Other" in lar_s: st.text_area("Describe other:", key="Sinusitis__c.Sinus_Q35c__c")

if st.radio("Ever had a laryngectomy? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q36__c") == "Yes":
    ly_t = st.selectbox("Type:", ["Total", "Partial"], key="Sinusitis__c.Sinus_Q36a__c")
    if ly_t == "Partial": st.text_area("Describe residuals:", key="Sinusitis__c.Sinus_Q36b__c")

st.radio("Laryngeal stenosis or trauma residuals? *", ["Yes", "No"], key="Sinusitis__c.Sinus_Q36c__c")

if st.radio("Complete organic aphonia? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q36d__c") == "Yes":
    ap_s = st.multiselect("Symptoms:", ["Inability to whisper", "Inability to communicate", "Other"], key="Sinusitis__c.Sinus_Q36e__c")
    if "Other" in ap_s: st.text_area("Describe other aphonia residuals:", key="Sinusitis__c.Sinus_Q36f__c")

if st.radio("Incomplete organic aphonia? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q36g__c") == "Yes":
    iap_s = st.multiselect("Symptoms checklist:", ["Hoarseness", "Inflammation", "Nodules", "Other"], key="Sinusitis__c.Sinus_Q36h__c")
    if "Hoarseness" in iap_s: st.text_area("Describe frequency:", key="Sinusitis__c.Sinus_Q37__c")
    if "Other" in iap_s: st.text_area("Describe other residuals:", key="Sinusitis__c.Sinus_Q37a__c")

if st.radio("Permanent tracheostomy? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q38__c") == "Yes":
    st.text_area("Describe reason/potential reversal:", key="Sinusitis__c.Sinus_Q38a__c")

if st.radio("Injury to pharynx? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q39__c") == "Yes":
    st.multiselect("Symptoms:", ["Obstruction", "Stricture", "Speech impairment", "Other"], key="Sinusitis__c.Sinus_Q39a__c")
    st.radio("Vocal cord paralysis? *", ["Yes", "No"], key="Sinusitis__c.Sinus_Q39c__c")

st.header("Deviated Septum")
if st.radio("Seeking connection for deviated septum? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q30__c") == "Yes":
    st.radio("Is it traumatic?", ["Yes", "No"], key="Sinusitis__c.Sinus_Q31__c")
    st.radio("Complete obstruction Left side?", ["Yes", "No"], key="Sinusitis__c.Sinus_Q40__c")
    st.radio("Complete obstruction Right side?", ["Yes", "No"], key="Sinusitis__c.Sinus_Q41__c")
    st.radio(">50% obstruction both sides?", ["Yes", "No"], key="Sinusitis__c.Sinus_Q32__c")

st.header("Tumors/Neoplasms")
if st.radio("Tumors related to above conditions? *", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q43__c") == "Yes":
    tum_state = st.selectbox("State:", ["Benign", "Malignant"], key="Sinusitis__c.Sinus_Q42__c")
    if tum_state == "Malignant":
        st.selectbox("Status:", ["Active", "Remission"], key="Sinusitis__c.Sinus_Q49__c")
        if st.selectbox("Type:", ["Primary", "Secondary"], key="Sinusitis__c.Sinus_Q50__c") == "Secondary":
            st.text_area("Primary site:", key="Sinusitis__c.Sinus_Q51__c")
    tr_status = st.selectbox("Treatment status:", ["Yes - Current", "Yes - Completed", "No"], key="Sinusitis__c.Sinus_Q52__c")
    if tr_status != "No":
        t_t = st.multiselect("Treatments:", ["Radiation", "Chemotherapy", "X-ray", "Other"], key="Sinusitis__c.Sinus_Q44__c")
        if "Radiation" in t_t: 
            st.date_input("Recent radiation", key="Sinusitis__c.Sinus_Q53__c")
            st.date_input("Radiation completion", key="Sinusitis__c.Sinus_Q54__c")
        if "Antineoplastic chemotherapy" in t_t:
            st.date_input("Recent chemo", key="Sinusitis__c.Sinus_Q55__c")
            st.date_input("Chemo completion", key="Sinusitis__c.Sinus_Q56__c")
        if "Other" in t_t: st.text_area("Describe other treatments:", key="Sinusitis__c.Sinus_Q45__c")
    if st.radio("Had surgery on neoplasm?", ["Yes", "No"], index=1, key="Sinusitis__c.Sinus_Q46__c") == "Yes":
        st.text_area("Neoplasm surgery description:", key="Sinusitis__c.Sinus_Q47__c")

st.header("Final Details")
st.text_area("List residuals/complications of tumors:", key="Sinusitis__c.Sinus_Q42e__c")
st.text_area("Sinusitis impact on occupational tasks: *", key="Sinusitis__c.Sinus_Q21__c")
st.text_input("Veteran Name: *", key="Sinusitis__c.DBQ__c.Veteran_Name_Text__c")
st.text_input("Date Submitted (MM/DD/YYYY): *", key="Sinusitis__c.Date_Submitted__c")

# --- YOUR ORIGINAL FORM END ---

st.divider()
if st.button("🔍 Run Logical Cross-Check (Groq AI)"):
    all_form_data = {k: v for k, v in st.session_state.items() if "Sinusitis__c" in str(k)}
    with st.spinner("Analyzing for contradictions..."):
        audit_feedback = auditor.cross_check_logic(all_form_data)
        st.sidebar.markdown("### 🩺 Auditor Results")
        st.sidebar.markdown(audit_feedback)

form_data = {k: v for k, v in st.session_state.items() if "Sinusitis__c" in str(k)}
st.download_button("📥 Download JSON", json.dumps(form_data, indent=4), "sinus_dbq.json", "application/json")
