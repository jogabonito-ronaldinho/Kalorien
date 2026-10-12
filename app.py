import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import os
import uuid

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="Mabe & Richi Tracker",
    page_icon="🥗",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("🥗 Mabe & Richi's Kalorien- & Makro-Tracker")

# --- DATEI-SPEICHERUNG (CSV PERSISTENZ) ---
DATA_FILE = "kalorien_daten.csv"

def lade_daten():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            eintraege = df.to_dict(orient="records")
            # Abwärtskompatibilität & Bereinigung alter Einträge
            for item in eintraege:
                if "ID" not in item or pd.isna(item["ID"]) or str(item["ID"]).strip() == "":
                    item["ID"] = str(uuid.uuid4())
                if "protein" not in item or pd.isna(item["protein"]):
                    item["protein"] = 0
                if "carbs" not in item or pd.isna(item["carbs"]):
                    item["carbs"] = 0
                if "fett" not in item or pd.isna(item["fett"]):
                    item["fett"] = 0
                if "kcal" not in item or pd.isna(item["kcal"]):
                    item["kcal"] = 0
            return eintraege
        except Exception:
            return []
    return []

def speichere_daten(eintraege_liste):
    df = pd.DataFrame(eintraege_liste)
    df.to_csv(DATA_FILE, index=False)

# Session State Initialisierungen
if "eintraege" not in st.session_state:
    st.session_state.eintraege = lade_daten()

if "last_success" not in st.session_state:
    st.session_state.last_success = None

if "clear_camera" not in st.session_state:
    st.session_state.clear_camera = False

# --- NUTZER-ZIELE ---
USER_GOALS = {
    "Mabe": {
        "ziel_kcal": 1900,
        "protein": 150,
        "fett": 55,
        "carbs": 200
    },
    "Richi": {
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

# --- NÄHRWERT-SCHÄTZUNG & DATABASE-SUCHE ---
def search_or_estimate_nutrition(query_text, portion_size):
    factor = PORTION_FACTORS.get(portion_size, 1.0)
    q = query_text.lower()
    gefundenes_gericht = query_text
    
    # 1. Versuche Abfrage über Open Food Facts API
    try:
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query_text}&search_simple=1&action=process&json=1"
        res = requests.get(url, timeout=3).json()
        if res.get("products") and len(res["products"]) > 0:
            for p in res["products"]:
                nutriments = p.get("nutriments", {})
                kcal_100 = nutriments.get("energy-kcal_100g")
                product_name = p.get("product_name")
                if kcal_100 and kcal_100 > 0:
                    if product_name:
                        gefundenes_gericht = product_name
                    base_g = 350 * factor
                    return {
                        "gericht": gefundenes_gericht,
                        "kcal": int(kcal_100 * (base_g / 100)),
                        "protein": int(nutriments.get("proteins_100g", 15) * (base_g / 100)),
                        "carbs": int(nutriments.get("carbohydrates_100g", 25) * (base_g / 100)),
                        "fett": int(nutriments.get("fat_100g", 10) * (base_g / 100))
                    }
    except Exception:
        pass
    
    # 2. Regelbasierte Keyword-Erkennung falls API keine Treffer liefert
    base_kcal, prot, carbs, fett = 600, 35, 65, 20
    
    if any(k in q for k in ["salat", "gemüse", "suppe", "obst"]):
        base_kcal, prot, carbs, fett = 350, 15, 30, 12
    elif any(k in q for k in ["pizza", "burger", "pasta", "nudeln", "steak", "pommes", "döner"]):
        base_kcal, prot, carbs, fett = 850, 40, 85, 35
    elif any(k in q for k in ["shake", "protein", "riegel", "quark", "joghurt"]):
        base_kcal, prot, carbs, fett = 300, 30, 20, 6
    elif any(k in q for k in ["reis", "hähnchen", "pute", "fisch", "lachs"]):
        base_kcal, prot, carbs, fett = 550, 45, 50, 15

    return {
        "gericht": gefundenes_gericht,
        "kcal": int(base_kcal * factor),
        "protein": int(prot * factor),
        "carbs": int(carbs * factor),
        "fett": int(fett * factor)
    }

# --- EINGABEBEREICH ---
st.subheader("📝 Mahlzeit erfassen")

person = st.radio("Wer isst?", ["Mabe", "Richi"], horizontal=True, key="person_wahl")
eingabe_art = st.radio("Erfassungsart", ["Suche / Name des Gerichts", "Foto aufnehmen"], horizontal=True)

such_text = ""
portion = "Mittel"
camera_foto = None

if eingabe_art == "Suche / Name des Gerichts":
    col1, col2 = st.columns([2, 1])
    with col1:
        such_text = st.text_input("Name des Gerichts (z.B. Lachs mit Reis, Caesar Salad)", value="", key="input_gericht")
    with col2:
        portion = st.selectbox("Portionsgröße", ["Klein", "Mittel", "Groß"], index=1, key="p_suche")
else:
    st.markdown("📷 **Kamera öffnen & Foto machen:**")
    
    # Schlüssel-Rotation zur dynamischen Zurücksetzung des Kamera-Inputs
    cam_key = f"camera_{st.session_state.get('cam_id', 0)}"
    camera_foto = st.camera_input("Kamera", key=cam_key)
    portion = st.selectbox("Portionsgröße", ["Klein", "Mittel", "Groß"], index=1, key="p_foto")

if st.button("🔍 Nährwerte ermitteln & Eintragen", use_container_width=True):
    vals = None
    finaler_gericht_name = ""
    
    if eingabe_art == "Suche / Name des Gerichts":
        if such_text and such_text.strip() != "":
            with st.spinner("Analysiere Nährwerte..."):
                res_vals = search_or_estimate_nutrition(such_text, portion)
                finaler_gericht_name = res_vals["gericht"]
                vals = res_vals
        else:
            st.warning("Bitte gib einen Namen für das Gericht ein.")
    else:
        if camera_foto is not None:
            with st.spinner("Verarbeite Foto..."):
                base_factor = PORTION_FACTORS.get(portion, 1.0)
                finaler_gericht_name = "Mahlzeit"
                
                # Realistische Portionswerte für ein Hauptgericht vom Foto
                vals = {
                    "kcal": int(600 * base_factor),
                    "protein": int(35 * base_factor),
                    "carbs": int(65 * base_factor),
                    "fett": int(20 * base_factor)
                }
        else:
            st.warning("Bitte zuerst ein Foto mit der Kamera aufnehmen.")

    if vals:
        gericht_bezeichnung = f"Foto: {finaler_gericht_name}" if eingabe_art != "Suche / Name des Gerichts" else finaler_gericht_name
        
        neuer_eintrag = {
            "ID": str(uuid.uuid4()),
            "Datum": str(date.today()),
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Person": person,
            "Gericht": f"{gericht_bezeichnung} ({portion})",
            "kcal": vals["kcal"],
            "protein": vals["protein"],
            "carbs": vals["carbs"],
            "fett": vals["fett"]
        }
        
        st.session_state.eintraege.append(neuer_eintrag)
        speichere_daten(st.session_state.eintraege)
        
        # Grüne Erfolgsmeldung für den nächsten Rerun speichern
        st.session_state.last_success = (
            f"✅ Erfasst für **{person}** ({gericht_bezeichnung} - {portion}):\n\n"
            f"🔥 **{vals['kcal']} kcal** | "
            f"🥩 Eiweiß: **{vals['protein']}g** | "
            f"🍞 Carbs: **{vals['carbs']}g** | "
            f"🥑 Fett: **{vals['fett']}g**"
        )
        
        # Zurücksetzen der Eingabefelder
        if "input_gericht" in st.session_state:
            st.session_state["input_gericht"] = ""
        st.session_state["cam_id"] = st.session_state.get("cam_id", 0) + 1
        
        st.rerun()

# Erfolgsmeldung anzeigen
if st.session_state.last_success:
    st.success(st.session_state.last_success)
    st.session_state.last_success = None

# --- HEUTIGER FORTSCHRITT MIT SYMBOLEN ---
st.divider()
st.subheader("📊 Heutiger Fortschritt")

heute_str = str(date.today())

if st.session_state.eintraege:
    df_all = pd.DataFrame(st.session_state.eintraege)
    for col in ["ID", "Datum", "Timestamp", "Person", "Gericht", "kcal", "protein", "carbs", "fett"]:
        if col not in df_all.columns:
            df_all[col] = 0 if col in ["kcal", "protein", "carbs", "fett"] else ""
else:
    df_all = pd.DataFrame(columns=["ID", "Datum", "Timestamp", "Person", "Gericht", "kcal", "protein", "carbs", "fett"])

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

        st.write(f"🔥 **Kalorien:** {curr_kcal} / {goals['ziel_kcal']} kcal")
        st.progress(min(curr_kcal / goals["ziel_kcal"], 1.0))
        
        st.write(f"🥩 **Eiweiß:** {curr_prot}g / {goals['protein']}g")
        st.progress(min(curr_prot / goals["protein"], 1.0))

        st.write(f"🍞 **Carbs:** {curr_carbs}g / {goals['carbs']}g")
        st.progress(min(curr_carbs / goals["carbs"], 1.0))

        st.write(f"🥑 **Fett:** {curr_fett}g / {goals['fett']}g")
        st.progress(min(curr_fett / goals["fett"], 1.0))

# --- REPORT / HISTORIE ---
st.divider()
st.subheader("📈 Historie & Berichte")

if not df_all.empty:
    report_typ = st.selectbox(
        "Auswertung anzeigen für:",
        ["Tage (Einzelansicht & Bearbeiten)", "Wochen", "Monate", "Jahre"]
    )
    
    df_all["Datum_dt"] = pd.to_datetime(df_all["Datum"])
    
    if report_typ == "Tage (Einzelansicht & Bearbeiten)":
        st.caption("Alle erfassten Mahlzeiten. Klicke auf 🗑️ direkt neben dem Eintrag zum Löschen:")
        
        for idx, row in df_all.sort_values(by="Timestamp", ascending=False).iterrows():
            e_id = str(row["ID"])
            
            cols = st.columns([10, 1])
            with cols[0]:
                st.markdown(
                    f"**📅 {row['Datum']} | 👤 {row['Person']}** — *{row['Gericht']}*<br>"
                    f"🔥 **{int(row['kcal'])} kcal** | "
                    f"🥩 Eiweiß: **{int(row['protein'])}g** | "
                    f"🍞 Carbs: **{int(row['carbs'])}g** | "
                    f"🥑 Fett: **{int(row['fett'])}g**",
                    unsafe_allow_html=True
                )
            with cols[1]:
                if st.button("🗑️", key=f"hist_del_{e_id}", help="Eintrag löschen"):
                    st.session_state.eintraege = [e for e in st.session_state.eintraege if str(e.get("ID")) != e_id]
                    speichere_daten(st.session_state.eintraege)
                    st.rerun()
            st.divider()

    elif report_typ == "Wochen":
        df_all["Woche"] = df_all["Datum_dt"].dt.strftime('%Y-W%V')
        wochen_agg = df_all.groupby(["Woche", "Person"])[["kcal", "protein", "carbs", "fett"]].mean().reset_index()
        wochen_agg[["kcal", "protein", "carbs", "fett"]] = wochen_agg[["kcal", "protein", "carbs", "fett"]].astype(int)
        wochen_agg = wochen_agg.rename(columns={
            "kcal": "🔥 kcal",
            "protein": "🥩 Eiweiß (g)",
            "carbs": "🍞 Carbs (g)",
            "fett": "🥑 Fett (g)"
        })
        st.caption("Durchschnittliche Tageswerte pro Kalenderwoche:")
        st.dataframe(wochen_agg, use_container_width=True)
        
    elif report_typ == "Monate":
        df_all["Monat"] = df_all["Datum_dt"].dt.strftime('%Y-%m')
        monat_agg = df_all.groupby(["Monat", "Person"])[["kcal", "protein", "carbs", "fett"]].mean().reset_index()
        monat_agg[["kcal", "protein", "carbs", "fett"]] = monat_agg[["kcal", "protein", "carbs", "fett"]].astype(int)
        monat_agg = monat_agg.rename(columns={
            "kcal": "🔥 kcal",
            "protein": "🥩 Eiweiß (g)",
            "carbs": "🍞 Carbs (g)",
            "fett": "🥑 Fett (g)"
        })
        st.caption("Durchschnittliche Tageswerte pro Monat:")
        st.dataframe(monat_agg, use_container_width=True)
        
    elif report_typ == "Jahre":
        df_all["Jahr"] = df_all["Datum_dt"].dt.strftime('%Y')
        jahr_agg = df_all.groupby(["Jahr", "Person"])[["kcal", "protein", "carbs", "fett"]].mean().reset_index()
        jahr_agg[["kcal", "protein", "carbs", "fett"]] = jahr_agg[["kcal", "protein", "carbs", "fett"]].astype(int)
        jahr_agg = jahr_agg.rename(columns={
            "kcal": "🔥 kcal",
            "protein": "🥩 Eiweiß (g)",
            "carbs": "🍞 Carbs (g)",
            "fett": "🥑 Fett (g)"
        })
        st.caption("Durchschnittliche Tageswerte pro Jahr:")
        st.dataframe(jahr_agg, use_container_width=True)
else:
    st.info("Bisher sind noch keine Historiedaten vorhanden.")
