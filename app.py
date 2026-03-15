import streamlit as st
import requests
from PIL import Image
import pandas as pd # Essential for the visual distribution charts

# ==========================================
# CONFIGURATION & SETUP
# ==========================================
st.set_page_config(
    page_title="Pro Plant Doctor AI",
    page_icon="🌿",
    layout="wide", # Full screen width for high-density information
    initial_sidebar_state="expanded"
)

# API Keys and Endpoints
PLANTNET_API_KEY = "2b104IxrPENdTjiJSEJNqhqO" 
DISEASE_URL = "https://my-api.plantnet.org/v2/diseases/identify"
SPECIES_URL = "https://my-api.plantnet.org/v2/identify/all"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_remedy_for_disease(disease_name):
    """Expanded mapping database with specific biological treatments."""
    disease_lower = str(disease_name).lower()
    
    remedies_db = {
        "powdery mildew": "Remove infected leaves. Apply a fungicide with sulfur or neem oil. Increase spacing for airflow.",
        "rust": "Avoid overhead watering. Remove infected parts immediately. Use copper-based fungicides.",
        "early blight": "Remove lower infected leaves. Apply copper spray. Mulch around the base to prevent soil splash.",
        "late blight": "Urgent: Destroy infected plants if severe. Apply Chlorothalonil or Copper fungicide weekly.",
        "canker": "Prune infected branches 6 inches below the canker during dry weather. Sterilize tools.",
        "aphids": "Blast with water or use insecticidal soap. Encourage ladybugs/natural predators.",
        "leaf spot": "Reduce leaf wetness. Apply protective fungicide containing chlorothalonil or mancozeb."
    }
    
    for key, remedy in remedies_db.items():
        if key in disease_lower:
            return remedy
            
    return (
        "1. Isolate the plant immediately to prevent spreading.\n"
        "2. Prune heavily affected areas with sterilized tools.\n"
        "3. Check soil moisture and light levels.\n"
        "4. Take a sample to a local expert if the condition worsens."
    )

def analyze_plant_health(image_bytes, file_name):
    """
    Dual-stream analysis: Identifies the plant species AND the disease
    to ensure the diagnosis actually makes sense for that specific plant.
    """
    params = {"api-key": PLANTNET_API_KEY, "lang": "en"}
    files = [
        ('images', (file_name, image_bytes, 'image/jpeg')),
        ('organs', (None, 'leaf'))
    ]
    
    try:
        # Step 1: Identify Species (Context)
        species_req = requests.post(SPECIES_URL, params=params, files=files)
        species_req.raise_for_status()
        species_data = species_req.json()

        # Step 2: Identify Disease (Pathology)
        disease_req = requests.post(DISEASE_URL, params=params, files=files)
        disease_req.raise_for_status()
        disease_data = disease_req.json()

        return {"species": species_data, "diseases": disease_data}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# ==========================================
# SIDEBAR & HISTORY
# ==========================================
with st.sidebar:
    st.header("Settings & History")
    show_raw = st.checkbox("Show Technical JSON", value=False)
    if 'history' not in st.session_state:
        st.session_state.history = []
    
    if st.session_state.history:
        st.write("Recent Scans:")
        for item in st.session_state.history[-5:]:
            st.text(f"• {item}")
    
    st.divider()
    st.info("Sorting Mode: Species Priority (Matches moved to top)")

# ==========================================
# MAIN UI LAYOUT
# ==========================================
st.title("🌿 Pro AI Plant Pathologist")
st.markdown("---")

uploaded_file = st.file_uploader("Upload leaf photo (JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    main_col, side_col = st.columns([2, 1])
    
    with side_col:
        image = Image.open(uploaded_file)
        st.image(image, caption="Current Specimen", use_container_width=True)
        st.divider()
        st.warning("AI can make mistakes. Always verify with a local expert.")

    with main_col:
        if st.button("🚀 Start Deep Analysis", type="primary", use_container_width=True):
            with st.spinner("Processing dual-stage identification..."):
                img_bytes = uploaded_file.getvalue()
                full_result = analyze_plant_health(img_bytes, uploaded_file.name)

                if "error" in full_result:
                    st.error(f"API Connection Failed: {full_result['error']}")
                else:
                    # IDENTIFY SPECIES
                    species_list = full_result['species'].get('results', [])
                    top_species = species_list[0].get('species', {}).get('commonNames', ['Unknown'])[0] if species_list else "Unknown Plant"
                    
                    st.success(f"Detected Plant: **{top_species.title()}**")
                    st.session_state.history.append(f"{top_species} Diagnosis")

                    # PROCESS DISEASES WITH CUSTOM SORTING LOGIC
                    disease_results = full_result['diseases'].get('results', [])
                    
                    if not disease_results:
                        st.balloons()
                        st.success("No specific diseases detected! The plant appears healthy.")
                    else:
                        # --- START OF PRIORITY SORTING ---
                        matched_list = []
                        other_list = []
                        
                        for res in disease_results:
                            desc = res.get('description', 'Unknown Pathology')
                            # Check if identified species name is in the disease description
                            if top_species.lower() in desc.lower():
                                matched_list.append(res)
                            else:
                                other_list.append(res)
                        
                        # Rebuild results: Matches first, then others
                        sorted_results = matched_list + other_list
                        # --- END OF PRIORITY SORTING ---

                        st.subheader("🔬 Diagnostic Results")
                        chart_data = []
                        
                        # Loop through sorted results (Matches are now at the top)
                        for i, res in enumerate(sorted_results[:6]): 
                            score = res.get('score', 0) * 100
                            desc = res.get('description', 'Unknown Issue')
                            
                            is_match = top_species.lower() in desc.lower()
                            match_tag = "🎯 SPECIES MATCH" if is_match else "ℹ️ POTENTIAL"
                            
                            chart_data.append({"Condition": desc, "Certainty": score})
                            
                            # Auto-expand the match, collapse others
                            with st.expander(f"{'⭐ ' if is_match else ''}{desc} ({score:.1f}%)", expanded=is_match):
                                col_a, col_b = st.columns([1, 2])
                                col_a.metric("Certainty Score", f"{score:.1f}%")
                                col_a.write(f"Status: **{match_tag}**")
                                
                                col_b.markdown("**Recommended Remedy:**")
                                col_b.info(get_remedy_for_disease(desc))
                                
                        # Visual Chart Distribution
                        st.divider()
                        st.write("### Certainty Distribution (All Possibilities)")
                        df = pd.DataFrame(chart_data)
                        st.bar_chart(df.set_index('Condition'))

                    if show_raw:
                        st.divider()
                        st.subheader("Developer Metadata")
                        st.json(full_result)

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.caption("Powered by Pl@ntNet API v2. Context-Aware Diagnostic System.")