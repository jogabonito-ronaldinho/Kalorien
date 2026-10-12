import streamlit as st
import pandas as pd
import requests
from datetime import date

st.set_page_config(page_title="Mabe & Richi Tracker", page_icon="🥗", layout="centered")

st.title("🥗 Mabe & Richi's Kalorien- & Makro-Tracker")

# --- BENUTZER-ZIELE DEFINIEREN ---
USER_GOALS = {
    "Mabe": {
        "bedarf_kcal": 2400,
        "ziel_kcal": 1900,
        "protein": 150,
        "fett": 55,
        "carbs": 200
    },
    "Richi": {
        "bedarf_kcal": 2200,
        "ziel_kcal": 2200,
        "protein": 150,
        "fett": 70,
        "carbs": 240
    }
}

PORTION_FACTORS = {
    "Klein": 0.7,
    "Mittel": 1.0,
    "Groß": 1.4
}

# --- DATENSPEICHER ---
if "eintraege" not in st.session_state:
    st.session_state.eintraege = []

# --- SCHÄTZ- / SUCH-FUNKTION (OPEN FOOD FACTS & FALLBACK) ---
def search_or_estimate_nutrition(query_text, portion_size):
    factor = PORTION_FACTORS.get(portion_size, 1.0)
    
    # 1. Versuch: Open Food Facts API Abfrage
    try:
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query_text}&search_simple=1&action=process&json=1"
        res = requests.get(url, timeout=3).json()
        if res.get("products") and len(res["products"]) > 0:
            p = res["products"][0]
            nutriments = p.get("nutriments", {})
            
            # Basiswerte pro 100g/Portion hochrechnen (ca. 350g Standard-Mahlzeit)
            base_g = 3.5 * factor
            kcal = nutriments.get("energy-kcal_100g", 150) * base_g
            protein = nutriments.get("proteins_100g", 12) * base_g
            carbs = nutriments.get("carbohydrates_100g", 18) * base_g
            fett = nutriments.get("fat_100g", 5) * base_g
            
            return {
                "kcal": int(kcal),
                "protein": int(protein),
                "carbs": int(carbs),
                "fett": int(fett)
            }
    except Exception:
        pass

    # 2. Fallback: Plausible Standard-Schätzung für Mahlzeiten
    base_kcal = 500 * factor
    return {
        "kcal": int(base_kcal),
        "protein": int(25 * factor),
        "carbs": int(50 * factor),
        "fett": int(18 * factor)
    }

# --- EINGABEBEREICH ---
st.subheader("📝 Mahlzeit eintragen")

person = st.radio("Wer isst?", ["Mabe", "Richi"], horizontal=True)
eingabe_art = st.radio("Wie möchtest du eintragen?", ["Suche / Name des Gerichts", "Foto vom Gericht machen"], horizontal=True)

gericht_name = ""
portion = "Mittel"
estimated_values = None

if eingabe_art == "Suche / Name des Gerichts":
    col1, col2 = st.columns([2, 1])
    with col1:
        gericht_name = st.text_input("Name des Gerichts (z.B. Spaghetti Bolognese, Lachs mit Reis)")
    with col2:
        portion = st.selectbox("Portion", ["Klein", "Mittel", "Groß"], index=1)

else:
    uploaded_file = st.camera_input("Foto von der Mahlzeit aufnehmen")
    if uploaded_file is None:
        uploaded_file = st.file_uploader("Oder Foto aus Mediathek hochladen", type=["jpg", "png", "jpeg"])
        
    col1, col2 = st.columns([2, 1])
    with col1:
        gericht_name_input = st.text_input("Optionales Stichwort zum Foto (z.B. Salat mit Pute)")
        gericht_name = gericht_name_input if gericht_name_input else "Fotografierte Mahlzeit"
    with col2:
        portion = st.selectbox("Portionsgröße", ["Klein", "Mittel", "Groß"], index=1)

if st.button("🔍 Nährwerte ermitteln & Eintragen", use_container_width=True):
    if gericht_name:
        with st.spinner("Nährwerte werden recherchiert..."):
            vals = search_or_estimate_nutrition(gericht_name, portion)
            
            eintrag = {
                "Datum": str(date.today()),
                "Person": person,
                "Gericht": f"{gericht_name} ({portion})",
                "kcal": vals["kcal"],
                "protein": vals["protein"],
                "carbs": vals["carbs"],
                "fett": vals["fett"]
            }
            st.session_state.eintraege.append(eintrag)
            st.success(f"Erfolgreich für {person} eingetragen: {vals['kcal']} kcal | {vals['protein']}g Eiweiß | {vals['carbs']}g Carbs | {vals['fett']}g Fett")
    else:
        st.warning("Bitte gib einen Namen oder ein Stichwort für das Gericht ein.")

# --- TÄGLICHE ÜBERSICHT & DASHBOARD ---
st.divider()
st.subheader("📊 Heutiger Fortschritt")

heute = str(date.today())
if st.session_state.eintraege:
    df = pd.DataFrame(st.session_state.eintraege)
    df_heute = df[df["Datum"] == heute]
else:
    df_heute = pd.DataFrame()

# Anzeige für Mabe und Richi nebeneinander
col_mabe, col_richi = st.columns(2)

for idx, current_user in enumerate(["Mabe", "Richi"]):
    target_col = col_mabe if current_user == "Mabe" else col_richi
    goals = USER_GOALS[current_user]
    
    with target_col:
        st.markdown(f"### 👤 {current_user}")
        if current_user == "Mabe":
            st.caption("Ziel: Abnehmen (1.900 kcal)")
        else:
            st.caption("Ziel: Gewicht halten (2.200 kcal)")

        if not df_heute.empty and current_user in df_heute["Person"].values:
            u_df = df_heute[df_heute["Person"] == current_user]
            curr_kcal = int(u_df["kcal"].sum())
            curr_prot = int(u_df["protein"].sum())
            curr_carbs = int(u_df["carbs"].sum())
            curr_fett = int(u_df["fett"].sum())
        else:
            curr_kcal = curr_prot = curr_carbs = curr_fett = 0

        # Kalorien
        st.write(f"**Kalorien:** {curr_kcal} / {goals['ziel_kcal']} kcal")
        st.progress(min(curr_kcal / goals["ziel_kcal"], 1.0))
        
        # Eiweiß
        st.write(f"**Eiweiß:** {curr_prot}g / {goals['protein']}g")
        st.progress(min(curr_prot / goals["protein"], 1.0))

        # Kohlenhydrate
        st.write(f"**Carbs:** {curr_carbs}g / {goals['carbs']}g")
        st.progress(min(curr_carbs / goals["carbs"], 1.0))

        # Fett
        st.write(f"**Fett:** {curr_fett}g / {goals['fett']}g")
        st.progress(min(curr_fett / goals["fett"], 1.0))

if not df_heute.empty:
    st.markdown("---")
    st.markdown("### 📋 Heutige Mahlzeiten")
    st.dataframe(df_heute[["Person", "Gericht", "kcal", "protein", "carbs", "fett"]], use_container_width=True)
    if st.button("Tag zurücksetzen"):
        st.session_state.eintraege = [e for e in st.session_state.eintraege if e["Datum"] != heute]
        st.rerun()
