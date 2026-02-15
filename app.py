import streamlit as st
import requests

# --- CLOUD AGENT CONFIG (GROQ) ---
class ClinicalScribe:
    def __init__(self, api_key):
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.api_key = api_key

    def draft_history(self, prompt_text):
        if not self.api_key or self.api_key == "your_key_here":
            return "Error: API Key not configured in Streamlit Secrets."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile", # High-performance clinical reasoning
            "messages": [
                {"role": "system", "content": "You are a senior medical scribe specializing in VA Disability Benefits Questionnaires (DBQs)."},
                {"role": "user", "content": prompt_text}
            ],
            "temperature": 0.3
        }
        try:
            res = requests.post(self.url, json=payload, headers=headers, timeout=25)
            res.raise_for_status()
            return res.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"API Connection Error: {str(e)}"

# --- UI SETUP ---
st.set_page_config(page_title="VA Sinusitis Assistant", layout="wide")

# Securely fetch API key from Secrets
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "your_key_here")
scribe = ClinicalScribe(GROQ_API_KEY)

# Session state management
if 'history_output' not in st.session_state:
    st.session_state['history_output'] = ""
if 'show_final_field' not in st.session_state:
    st.session_state['show_final_field'] = False
if 'symptom_detail_output' not in st.session_state:
    st.session_state['symptom_detail_output'] = ""

# --- CALLBACKS FOR STABILITY ---
def generate_symptom_detail_callback(sinuses, symptoms, aq1, aq2, aq3):
    s_prompt = f"Draft a clinical detail paragraph for VA DBQ. Affected Areas: {sinuses}. Symptoms: {symptoms}. Discharge: {aq1}, {aq3}. Positional pain: {aq2}. Tone: 3rd person clinical."
    st.session_state["Sinusitis__c.Sinus_Q14__c"] = scribe.draft_history(s_prompt)

# --- MAIN FORM UI ---
st.title("Sinusitis Questionnaire")

claim_selection = st.selectbox(
    "Are you applying for an initial claim or a re-evaluation for an existing service-connected disability? *",
    ["--select an item--", "Initial Claim", "Re-evaluation for Existing"],
    key="claim_val"
)

if claim_selection != "--select an item--":
    # 2. Dynamic Instructions
    if claim_selection == "Initial Claim":
        label_text = "Briefly describe the history of your sinus condition, including how and when your symptoms began and the link between your injury and military service."
        inst_logic = "Describe history and nexus to service"
    else:
        label_text = "Briefly describe the history of your sinus condition, including how and when your symptoms began:"
        inst_logic = "Describe history and symptoms"

    st.markdown(f"**{label_text}**")

    # Assistant 1 (History)
    with st.expander("🪄 **GUIDED INTERVIEW: Help me draft my clinical history**", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            w_onset = st.text_input("Approximate Date of Onset:", placeholder="e.g., Spring 2014")
            w_trigger = st.selectbox("How did the condition begin?", ["Sudden trauma", "Infection", "Environmental exposure", "Gradual onset"])
        with c2:
            w_freq = st.select_slider("Frequency of Flare-ups:", options=["Occasional", "Monthly", "Weekly", "Near Constant"])
            w_impact = st.selectbox("Occupational Impact:", ["None", "Occasional missed work", "Significant impairment"])

        st.write("**Current Symptoms:**")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            s_pain = st.checkbox("Sinus pain")
            s_tend = st.checkbox("Sinus tenderness")
        with sc2:
            s_pus = st.checkbox("Pus discharge")
            s_head = st.checkbox("Sinus headaches")
        with sc3:
            s_crust = st.checkbox("Crusting")
            s_other = st.text_input("Other:")

        if st.button("Generate Professional Description"):
            active_symptoms = [s for s, b in {"pain": s_pain, "tenderness": s_tend, "pus": s_pus, "headaches": s_head, "crusting": s_crust}.items() if b]
            h_prompt = f"Claim: {claim_selection}. Onset: {w_onset}. Trigger: {w_trigger}. Freq: {w_freq}. Symptoms: {active_symptoms}. Instruction: {inst_logic}. Tone: 3rd person clinical."
            st.session_state['history_output'] = scribe.draft_history(h_prompt)
            st.session_state['show_final_field'] = True
            st.rerun()

    # History Output
    if st.session_state['show_final_field']:
        st.text_area(label="History Field", value=st.session_state['history_output'], height=250, label_visibility="collapsed")

        # Medication Section
        med_trigger = st.radio("Do you currently take any medication(s)? *", ["--select--", "Yes", "No"], horizontal=True, key="Q11")
        if med_trigger == "Yes":
            num_meds = st.selectbox("How many?", ["--select--", "1", "2", "3", "More than 3"], key="Q11a")
            if num_meds != "--select--":
                limit = 3 if num_meds == "More than 3" else int(num_meds)
                for i in range(1, limit + 1):
                    mc1, mc2, mc3 = st.columns(3)
                    with mc1: st.text_input(f"Medication #{i}:", key=f"med_n_{i}")
                    with mc2: st.text_input(f"Dosage:", key=f"med_d_{i}")
                    with mc3: st.text_input(f"Freq:", key=f"med_f_{i}")

        # Service Connection Section
        sc_trigger = st.radio("Are you service connected? *", ["--select--", "Yes", "No"], horizontal=True, key="Q48")
        if sc_trigger == "Yes":
            st.markdown("---")
            sel_sinuses = st.multiselect("Affected Sinuses *", ["Maxillary", "Frontal", "Ethmoid", "Sphenoid", "Pansinusitus"], key="Sinusitis__c.Sinus_Q34__c")
            sel_symptoms = st.multiselect("Symptoms Checklist:", ["Near constant", "Headaches", "Sinus pain", "Tenderness", "Pus", "Crusting"], key="Sinusitis__c.Sinus_Q12__c")

            if sel_sinuses and sel_symptoms:
                with st.expander("🪄 **AI ASSISTANT: Symptom Detail**", expanded=True):
                    aq1 = st.radio("Discharge frequency?", ["Constant", "Intermittent"], key="sq1")
                    aq2 = st.radio("Pain on leaning?", ["Yes", "No"], key="sq2")
                    aq3 = st.text_input("Consistency:", key="sq3")
                    st.button("Generate Symptom Detail", on_click=generate_symptom_detail_callback, args=(sel_sinuses, sel_symptoms, aq1, aq2, aq3))

            st.markdown("**Please describe the symptoms in detail: * **")
            st.text_area(label="Detail Output", height=200, label_visibility="collapsed", key="Sinusitis__c.Sinus_Q14__c")