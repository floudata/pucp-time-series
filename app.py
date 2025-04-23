import streamlit as st
import pandas as pd
import time 
import os
import wfdb
import numpy as np
import matplotlib.pyplot as plt
import neurokit2 as nk
from streamlit_extras.metric_cards import style_metric_cards
import re


@st.dialog("filtrar")
def filtro():
    st.session_state["selecionado"] = None
    st.write("This is a filter dialog")
    data = pd.read_csv("records.csv", index_col="NUMBERS", sep=";")
    data["SELECT"] = False

    with st.form("seleccionar_record"):
        st.write("Seleccionar Record")
        data_edit = st.data_editor(
            data,
            column_config={
                "SELECT": st.column_config.CheckboxColumn(
                    "Seleccionar", default=False, help="Seleccionar solo un record",
                )
            },
            disabled=["NUMBERS", "RECORDS"],
            height=250,
        )

        st.write("Seleccionar la derivación")

        leads = ('I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6')
        lead = st.selectbox(
            "¿Cuál es la derivación que quieres visualizar?",
            leads,
            index=1,
        )

        submitted = st.form_submit_button("Guardar Selección")

    if submitted:
        if data_edit["SELECT"].sum() > 1:
            idx = data_edit[data_edit["SELECT"]].index[-1]
            data_edit["SELECT"] = False
            data_edit.at[idx, "SELECT"] = True
        elif data_edit["SELECT"].sum() == 0:
            st.warning("Debes seleccionar un RECORD.")
        
        seleccionado = data_edit[data_edit["SELECT"]]

        if not seleccionado.empty:
            st.session_state["selecionado"] = seleccionado
            st.session_state["lead"] = leads.index(lead)
            st.session_state["lead_name"] = lead
            st.success("¡Selección guardada!")
            st.write("Seleccionaste:")
            st.write(seleccionado)
            

            with st.spinner("Descargando..."):
                seleccionado_name = seleccionado["RECORDS"].iloc[0]
                db_name = 'ecg-arrhythmia'
                download_dir = './ecg-arrhythmia-1.0.0'
                records = [seleccionado_name]
                record_path = os.path.join(download_dir, f"{seleccionado_name}.hea")
                if not os.path.exists(path=record_path):
                    st.info(f"Downloading the specific record from PhysioNet... **{seleccionado_name}**")
                    wfdb.dl_database(db_name, dl_dir=download_dir, records=records)
                    st.success("Download complete!")
                else:
                    st.info("Database already downloaded.")
                
                time.sleep(5)
                st.rerun()
            


def set_slider():
    with st.sidebar:
        if st.button("FILTRAR RECORD", type="secondary", icon=":material/tune:", use_container_width=True):
            filtro()


def plot_ecg_style(ecg, fs, duration=10, title="Visualización ECG estilo clínico"):
    N = int(fs * duration)
    t = np.arange(0, duration, 1/fs)

    fig, ax = plt.subplots(figsize=(20, 4))
    ax.plot(t[:N], ecg[:N], color='black', linewidth=1)

    # Cuadrícula roja
    ax.set_xticks(np.arange(0, duration, 0.04), minor=True)
    ax.set_xticks(np.arange(0, duration, 0.2))
    ax.set_yticks(np.arange(-2, 2, 0.1), minor=True)
    ax.set_yticks(np.arange(-2, 2, 0.5))

    ax.grid(which='minor', color='red', linestyle=':', linewidth=0.5)
    ax.grid(which='major', color='red', linestyle='-', linewidth=1)

    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("Voltaje (mV)")
    ax.set_title(title)

    return fig


def decode_dx_codes(codes_string, snomed_map):
    codes = [code.strip() for code in codes_string.split(",")]
    names = [snomed_map.get(code, f"Unknown({code})") for code in codes]
    return ", ".join(names)


def view_graphics(download_dir, record_name):
    record_path = os.path.join(download_dir, record_name)
    record = wfdb.rdrecord(record_path)
    signal_array = np.array(record.p_signal)
    signal = signal_array[:, st.session_state["lead"]]
    fs = record.fs

    df_snomed = pd.read_csv("SNOMED-CT.csv")
    
    st.markdown(f"## :small_blue_diamond: Detalles del Registro")
    with st.expander("Visualizar las carácteristicas del registro"):
        col1, col2, col3 = st.columns(3)
        col1.metric(label="Nombre del Registro", value=record.record_name, border=True)
        col2.metric(label="Duración (s)", value=f"{record.sig_len / record.fs:.2f}", border=True)
        col3.metric(label="Frecuencia de Muestreo (Hz)", value=record.fs, border=True)
        
        col1.metric(label="Número de Derivaciones", value=record.n_sig, border=True)
        col2.metric(label="Muestras por Derivación", value=record.sig_len, border=True)
        col3.metric(label="Unidades", value=record.units[0], border=True)

        age = ""
        sex = "" 
        dx = ""
        for i in record.comments:
            search_age = re.compile(r"Age: (?P<age>\d+)")
            search_sex = re.compile(r"Sex: (?P<sex>\w+)")
            search_dx = re.compile(r"Dx: (?P<dx>[\d,]+)")

            if search_age.search(i):
                age = search_age.search(i).group("age")
            if search_sex.search(i):
                sex = search_sex.search(i).group("sex")
            if search_dx.search(i):
                dx = search_dx.search(i).group("dx")
                dx = dx.split(",")

        col1.metric(label="Edad", value=age, border=True)
        col2.metric(label="Sex", value=sex, border=True)
        
        #style_metric_cards()

        st.write("Lista de Diagnósticos")
        dx_dataframe = df_snomed[df_snomed["Snomed_CT"].astype(str).isin(dx)]
        st.dataframe(dx_dataframe,
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Snomed_CT": st.column_config.TextColumn("Código SNOMED CT", width="medium"),
                        "Full_Name": st.column_config.TextColumn("Nombre", width="large"),
                        "Acronym_Name": st.column_config.TextColumn("Acrónimo", width="small"),
                    },
                    column_order=["Snomed_CT", "Full_Name", "Acronym_Name"],
                    )

    st.divider()
    st.markdown(f"## :small_blue_diamond: Gráfica del ECG")
    st.pyplot(plot_ecg_style(signal, fs=fs, title="Visualización ECG original"))

    ecg_cleaned = nk.ecg_clean(signal, sampling_rate=fs)

    st.pyplot(plot_ecg_style(ecg_cleaned, fs=fs, title="Visualización ECG Limpio"))

    _, rpeaks = nk.ecg_peaks(ecg_cleaned, sampling_rate=fs)
    rr_intervals = np.diff(rpeaks['ECG_R_Peaks']) / fs
    heart_rate = 60 / rr_intervals

    hr_calculado = np.mean(heart_rate)

    signal_process, info_process = nk.ecg_process(signal, sampling_rate=fs)
    hr_visible = signal_process["ECG_Rate"].mean()
    
    st.divider()
    st.markdown(f"## :small_blue_diamond: Gráfica del ECG Procesado")
    fig = plt.figure(figsize=(15, 10))
    nk.ecg_plot(signal_process, info_process)
    fig = plt.gcf()
    fig.tight_layout()
    st.pyplot(fig)

    st.divider()
    st.markdown(f"## :small_blue_diamond: Frecuencia Cardíaca")
    if np.mean(heart_rate) < 60 or np.mean(heart_rate) > 100:
        st.warning(f"⚠️ Frecuencia cardíaca fuera de rango: {hr_calculado:.1f} bpm")
    else:
        st.success(f"✅ Frecuencia cardíaca dentro del rango: {hr_calculado:.1f} bpm")
    
    st.markdown(f"📊 **HR calculado (manual):** `{hr_calculado:.2f} bpm`")
    st.markdown(f"🖼️ **HR figura (neurokit2):** `{hr_visible:.2f} bpm`")




def set_main():
    download_dir = './ecg-arrhythmia-1.0.0'
    seleccionado = st.session_state["selecionado"]["RECORDS"].iloc[0]
    st.title("Análisis del registro {seleccionado} - Derivación {lead}".format(seleccionado=seleccionado, lead=st.session_state["lead_name"]))
    view_graphics(download_dir, seleccionado)


def set_resumen():
    st.title("Resumen del Modelo")

def main():
    if "selecionado" not in st.session_state:
        st.session_state["selecionado"] = None
    if "lead" not in st.session_state:
        st.session_state["lead"] = None
    if "lead_name" not in st.session_state:
        st.session_state["lead_name"] = None

    set_slider()

    if st.session_state["selecionado"] is not None:
        set_main()
    else:
        set_resumen()

if __name__ == "__main__":
    main()