import streamlit as st
import pandas as pd
from datetime import date

# Titel der App
st.set_page_config(page_title="Unser Kalorien-Tracker", page_icon="🍽️", layout="centered")

st.title("🍽️ Gemeinsamer Kalorien-Tracker")
st.markdown("Ziel: **1.900 kcal** | Fokus: Proteinreich & fit bleiben 🍏")

# Einfache Session-State-Speicherung (für den Prototypen / die Session)
if "eintraege" not in st.session_state:
    st.session_state.eintraege = []

# --- EINGABE-BEREICH ---
with st.form("kalorien_form", clear_on_submit=True):
    st.subheader("Neues Gericht / Mahlzeit eintragen")
    
    col1, col2 = st.columns(2)
    with col1:
        person = st.selectbox("Wer isst?", ["Du", "Deine Frau"])
    with col2:
        mahlzeit_typ = st.selectbox("Mahlzeit", ["Frühstück", "Mittagessen", "Abendessen", "Snack"])
        
    gericht_name = st.text_input("Name des Gerichts (z.B. Hähnchen mit Reis)")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        kalorien_gesamt = st.number_input("Gesamt-Kalorien (kcal)", min_value=0, value=600, step=10)
    with c2:
        gramm_gesamt = st.number_input("Gesamtgewicht gekocht (g)", min_value=1, value=500, step=10)
    with c3:
        gramm_portion = st.number_input("Deine gegessene Menge (g)", min_value=1, value=300, step=10)

    submitted = st.form_submit_button("Portion berechnen & eintragen")
    
    if submitted and gericht_name:
        # Berechnung der individuellen Portions-Kalorien
        portion_kcal = (kalorien_gesamt / gramm_gesamt) * gramm_portion
        
        neuer_eintrag = {
            "Datum": str(date.today()),
            "Person": person,
            "Mahlzeit": mahlzeit_typ,
            "Gericht": gericht_name,
            "Gegessen (g)": gramm_portion,
            "Kalorien (kcal)": int(portion_kcal)
        }
        st.session_state.eintraege.append(neuer_eintrag)
        st.success(f"Eintrag für {person} gespeichert: **{int(portion_kcal)} kcal**!")

# --- TÄGLICHE ÜBERSICHT ---
st.divider()
st.subheader("📊 Heutige Übersicht")

if st.session_state.eintraege:
    df = pd.DataFrame(st.session_state.eintraege)
    
    # Filter für das heutige Datum
    heute_str = str(date.today())
    df_heute = df[df["Datum"] == heute_str]
    
    if not df_heute.empty:
        # Summen pro Person berechnen
        zusammenfassung = df_heute.groupby("Person")["Kalorien (kcal)"].sum().reset_index()
        
        col_du, col_frau = st.columns(2)
        
        # Du
        kalorien_du = zusammenfassung.loc[zusammenfassung["Person"] == "Du", "Kalorien (kcal)"]
        sum_du = int(kalorien_du.values[0]) if not kalorien_du.empty else 0
        rest_du = 1900 - sum_du
        
        with col_du:
            st.metric(label="Dein Stand (Du)", value=f"{sum_du} kcal", delta=f"Noch {rest_du} kcal bis 1.900")
            st.progress(min(sum_du / 1900, 1.0))
            
        # Deine Frau (Beispielhaftes Ziel 1.700 oder anpassbar)
        kalorien_frau = zusammenfassung.loc[zusammenfassung["Person"] == "Deine Frau", "Kalorien (kcal)"]
        sum_frau = int(kalorien_frau.values[0]) if not kalorien_frau.empty else 0
        
        with col_frau:
            st.metric(label="Stand (Deine Frau)", value=f"{sum_frau} kcal")
            st.progress(min(sum_frau / 1800, 1.0))

        st.markdown("### Alle heutigen Einträge:")
        st.dataframe(df_heute[["Person", "Mahlzeit", "Gericht", "Gegessen (g)", "Kalorien (kcal)"]], use_container_width=True)
        
        if st.button("Heutigen Verlauf zurücksetzen"):
            st.session_state.eintraege = [e for e in st.session_state.eintraege if e["Datum"] != heute_str]
            st.rerun()
    else:
        st.info("Heute wurden noch keine Kalorien eingetragen.")
else:
    st.info("Bisher noch keine Einträge vorhanden. Trag oben deine erste Mahlzeit ein!")
