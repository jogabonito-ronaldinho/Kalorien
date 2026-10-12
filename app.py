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
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Person": person,
                "Gericht": f"{gericht_name} ({portion})",
                "kcal": vals["kcal"],
                "protein": vals["protein"],
                "carbs": vals["carbs"],
                "fett": vals["fett"]
            }
            st.session_state.eintraege.append(neuer_eintrag)
            speichere_daten(st.session_state.eintraege)
            st.success(f"Eingetragen für {person}: {vals['kcal']} kcal | P: {vals['protein']}g | C: {vals['carbs']}g | F: {vals['fett']}g")
    else:
        st.warning("Bitte gib einen Namen oder eine Beschreibung ein.")

# --- HEUTIGER FORTSCHRITT ---
st.divider()
st.subheader("📊 Heutiger Fortschritt")

heute_str = str(date.today())
df_all = pd.DataFrame(st.session_state.eintraege) if st.session_state.eintraege else pd.DataFrame(columns=["Datum", "Timestamp", "Person", "Gericht", "kcal", "protein", "carbs", "fett"])

df_heute = df_all[df_all["Datum"] == heute_str] if not df_all.empty and "Datum" in df_all.columns else pd.DataFrame()

col_mabe, col_richi = st.columns(2)

for current_user in ["Mabe", "Richi"]:
    target_col = col_mabe if current_user == "Mabe" else col_richi
    goals = USER_GOALS[current_user]
    
    with target_col:
        st.markdown(f"### 👤 {current_user}")
        
        curr_kcal = int(df_heute[df_heute["Person"] == current_user]["kcal"].sum()) if not df_heute.empty and "Person" in df_heute.columns else 0
        curr_prot = int(df_heute[df_heute["Person"] == current_user]["protein"].sum()) if not df_heute.empty and "Person" in df_heute.columns else 0
        curr_carbs = int(df_heute[df_heute["Person"] == current_user]["carbs"].sum()) if not df_heute.empty and "Person" in df_heute.columns else 0
        curr_fett = int(df_heute[df_heute["Person"] == current_user]["fett"].sum()) if not df_heute.empty and "Person" in df_heute.columns else 0

        st.write(f"**Kalorien:** {curr_kcal} / {goals['ziel_kcal']} kcal")
        st.progress(min(curr_kcal / goals["ziel_kcal"], 1.0))
        
        st.write(f"**Eiweiß:** {curr_prot}g / {goals['protein']}g")
        st.progress(min(curr_prot / goals["protein"], 1.0))

        st.write(f"**Carbs:** {curr_carbs}g / {goals['carbs']}g")
        st.progress(min(curr_carbs / goals["carbs"], 1.0))

        st.write(f"**Fett:** {curr_fett}g / {goals['fett']}g")
        st.progress(min(curr_fett / goals["fett"], 1.0))

if not df_heute.empty:
    st.markdown("---")
    st.markdown("### 📋 Heutige Einträge")
    st.dataframe(df_heute[["Person", "Gericht", "kcal", "protein", "carbs", "fett"]], use_container_width=True)

# --- REPORT / HISTORIE (Tage, Wochen, Monate, Jahre) ---
st.divider()
st.subheader("📈 Historie & Berichte")

if not df_all.empty:
    report_typ = st.selectbox("Auswertung anzeigen für:", ["Tage (Einzeltage)", "Wochen", "Monate", "Jahre"])
    
    df_all["Datum_dt"] = pd.to_datetime(df_all["Datum"])
    
    if report_typ == "Tage (Einzeltage)":
        tages_agg = df_all.groupby(["Datum", "Person"])[["kcal", "protein", "carbs", "fett"]].sum().reset_index()
        tages_agg = tages_agg.sort_values(by="Datum", ascending=False)
        st.dataframe(tages_agg, use_container_width=True)
        
    elif report_typ == "Wochen":
        df_all["Woche"] = df_all["Datum_dt"].dt.strftime('%Y-W%V')
        wochen_agg = df_all.groupby(["Woche", "Person"])[["kcal", "protein", "carbs", "fett"]].mean().reset_index()
        wochen_agg[["kcal", "protein", "carbs", "fett"]] = wochen_agg[["kcal", "protein", "carbs", "fett"]].astype(int)
        st.caption("Durchschnittliche Tageswerte pro Kalenderwoche:")
        st.dataframe(wochen_agg, use_container_width=True)
        
    elif report_typ == "Monate":
        df_all["Monat"] = df_all["Datum_dt"].dt.strftime('%Y-%m')
        monat_agg = df_all.groupby(["Monat", "Person"])[["kcal", "protein", "carbs", "fett"]].mean().reset_index()
        monat_agg[["kcal", "protein", "carbs", "fett"]] = monat_agg[["kcal", "protein", "carbs", "fett"]].astype(int)
        st.caption("Durchschnittliche Tageswerte pro Monat:")
        st.dataframe(monat_agg, use_container_width=True)
        
    elif report_typ == "Jahre":
        df_all["Jahr"] = df_all["Datum_dt"].dt.strftime('%Y')
        jahr_agg = df_all.groupby(["Jahr", "Person"])[["kcal", "protein", "carbs", "fett"]].mean().reset_index()
        jahr_agg[["kcal", "protein", "carbs", "fett"]] = jahr_agg[["kcal", "protein", "carbs", "fett"]].astype(int)
        st.caption("Durchschnittliche Tageswerte pro Jahr:")
        st.dataframe(jahr_agg, use_container_width=True)
else:
    st.info("Bisher sind noch keine Historiedaten vorhanden.")
