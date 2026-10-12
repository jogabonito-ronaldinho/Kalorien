import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import os

st.set_page_config(page_title="Mabe & Richi Tracker", page_icon="🥗", layout="centered")

st.title("🥗 Mabe & Richi's Kalorien- & Makro-Tracker")

# --- DATEI-SPEICHERUNG (DAMIT NIX VERLOREN GEHT) ---
DATA_FILE = "kalorien_daten.csv"

def lade_daten():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            return df.to_dict(orient="records")
        except Exception:
            return []
    return []

def speichere_daten(eintraege_liste):
    df = pd.DataFrame(eintraege_liste)
    df.to_csv(DATA_FILE, index=False)

if "eintraege" not in st.session_state:
    st.session_state.eintraege = lade_daten()

# --- ZIELE ---
USER_GOALS = {
    "Mabe": {"ziel_kcal": 1900, "protein": 150, "fett": 55, "carbs": 200},
    "Richi": {"ziel_kcal": 2200, "protein": 150, "fett": 70, "carbs": 240}
}

PORTION_FACTORS = {"Klein": 0.7, "Mittel": 1.0, "Groß": 1.4}

def search_or_estimate_nutrition(query_text, portion_size):
    factor = PORTION_FACTORS.get(portion_size, 1.0)
    try:
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query_text}&search_simple=1&action=process&json=1"
        res = requests.get(url, timeout=3).json()
        if res.get("products") and len(res["products"]) > 0:
            p = res["products"][0]
            nutriments = p.get("nutriments", {})
            base_g = 3.5 * factor
            return {
                "kcal": int(nutriments.get("energy-kcal_100g", 150) * base_g),
                "protein": int(nutriments.get("proteins_100g", 12) * base_g),
                "carbs": int(nutriments.get("carbohydrates_100g", 18) * base_g),
                "fett": int(nutriments.get("fat_100g", 5) * base_g)
            }
    except Exception:
        pass
    
    base_kcal = 500 * factor
    return {
        "kcal": int(base_kcal),
        "protein": int(25 * factor),
        "carbs": int(50 * factor),
        "fett": int(18 * factor)
    }

# --- EINGABEBEREICH ---
st.subheader("📝 Mahlzeit erfassen")

person = st.radio("Wer isst?", ["Mabe", "Richi"], horizontal=True, key="person_wahl")
eingabe_art = st.radio("Erfassungsart", ["Suche / Name des Gerichts", "Foto hochladen / machen"], horizontal=True)

gericht_name = ""
portion = "Mittel"

if eingabe_art == "Suche / Name des Gerichts":
    col1, col2 = st.columns([2, 1])
    with col1:
        gericht_name = st.text_input("Name des Gerichts (z.B. Spaghetti, Steak mit Pommes)")
    with col2:
        portion = st.selectbox("Portionsgröße", ["Klein", "Mittel", "Groß"], index=1, key="p_suche")
else:
    uploaded_file = st.file_uploader("Foto des Gerichts aufnehmen oder hochladen", type=["jpg", "png", "jpeg"])
    col1, col2 = st.columns([2, 1])
    with col1:
        foto_text = st.text_input("Was ist auf dem Foto? (z.B. Caesar Salad)")
        gericht_name = foto_text if foto_text else "Gericht vom Foto"
    with col2:
        portion = st.selectbox("Portionsgröße", ["Klein", "Mittel", "Groß"], index=1, key="p_foto")

if st.button("🔍 Nährwerte ermitteln & Eintragen", use_container_width=True):
    if gericht_name:
        with st.spinner("Analysiere Nährwerte..."):
            vals = search_or_estimate_nutrition(gericht_name, portion)
            
            neuer_eintrag = {
                "Datum": str(date.today()),
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M
