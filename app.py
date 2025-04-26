import streamlit as st
import pandas as pd
import time 
import os
import wfdb
import numpy as np
import matplotlib.pyplot as plt
import neurokit2 as nk
import re
from PIL import Image


# Files
file_record = "records.csv"
file_snomed_ct = "SNOMED-CT.csv"
path_arrhythmia = "./ecg-arrhythmia-1.0.0"

@st.dialog("filtrar")
def filtro():
    st.session_state["selecionado"] = None
    st.write("Filtro de dialogo")
    data = pd.read_csv(file_record, index_col="NUMBERS", sep=";")
    data["SELECT"] = False

    with st.form("seleccionar_record"):
        st.write("Seleccionar registro(s) ")
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

        # Derivaciones
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
            st.warning("Debes seleccionar un registro.")
        
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
                records = [seleccionado_name]
                record_path = os.path.join(path_arrhythmia, f"{seleccionado_name}.hea")

                if not os.path.exists(path=record_path):
                    st.info(f"Descargando un registro especifico PhysioNet... **{seleccionado_name}**")
                    wfdb.dl_database(db_name, dl_dir=path_arrhythmia, records=records)
                    st.success("Descarga completa !")
                else:
                    st.info("La base de datos ha sido descargada.")
                
                time.sleep(5)
                st.rerun()


def set_slider():
    with st.sidebar:
        if st.button("Filtrar record", type="secondary", icon=":material/tune:", use_container_width=True):
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

    # Obtiene una derivacion especifica de sesion
    signal = signal_array[:, st.session_state["lead"]]
    # Frecuencia del muestreo
    fs = record.fs
    df_snomed = pd.read_csv(file_snomed_ct)
    
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
            search_dx = re.compile(r"Dx: (?P<dx>[\d,]+)") # diagnosticos

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

    # Limpieza de la señal ECG
    ecg_cleaned = nk.ecg_clean(signal, sampling_rate=fs)
    st.pyplot(plot_ecg_style(ecg_cleaned, fs=fs, title="Visualización ECG Limpio"))

    # Identificar tipo R
    _, rpeaks = nk.ecg_peaks(ecg_cleaned, sampling_rate=fs)
    # Calcula intervalos RR
    rr_intervals = np.diff(rpeaks['ECG_R_Peaks']) / fs
    # Identifica frecuencia cardica
    heart_rate = 60/rr_intervals
    # Promedio frecuencia cardiaca
    hr_calculado = np.mean(heart_rate)

    signal_process, info_process = nk.ecg_process(signal, sampling_rate=fs) # procesacimiento ECG
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
    msg = st.toast('Calculando Frecuencia Cardiaca...', icon=":material/pending:")
    time.sleep(2)
    msg.toast("Frecuencia Cardiaca Calculada", icon=":material/favorite:")
    if np.mean(heart_rate) < 60 or np.mean(heart_rate) > 100:
        st.warning(f"⚠️ Frecuencia cardíaca fuera de rango: {hr_calculado:.1f} bpm")
        msg.toast(f'Frecuencia cardíaca fuera de rango: {hr_calculado:.1f} bpm', icon='⚠️')
    else:
        st.success(f"✅ Frecuencia cardíaca dentro del rango: {hr_calculado:.1f} bpm")
        msg.toast(f'Frecuencia cardíaca dentro del rango: {hr_calculado:.1f} bpm', icon='✅')

    st.markdown(f"📊 **HR calculado (manual):** `{hr_calculado:.2f} bpm`")
    st.markdown(f"🖼️ **HR figura (neurokit2):** `{hr_visible:.2f} bpm`")


def set_main(): 
    seleccionado = st.session_state["selecionado"]["RECORDS"].iloc[0]
    st.title("Análisis del registro {seleccionado} - Derivación {lead}".format(seleccionado=seleccionado, lead=st.session_state["lead_name"]))
    view_graphics(path_arrhythmia, seleccionado)


def set_resumen():
    img = Image.open("imagen.jpg")
    st.markdown("# 🩺 Bienvenido a la Plataforma de Análisis de Señales ECG")
    st.image(img, caption="Proceso de adquisición de un ECG estándar de 12 derivaciones, mostrando la colocación torácica de los electrodos y la impresión del trazado.", use_container_width=True)
    st.markdown(
        """
            ## 📚 Sobre el Dataset

            Esta plataforma utiliza el conjunto de datos **“A Large-Scale 12-lead Electrocardiogram Database for Arrhythmia Study”**, publicado en *Scientific Data (Nature)* y disponible públicamente a través de PhysioNet.  
            Este dataset contiene más de **10,000 registros de pacientes** con señales de ECG de 12 derivaciones, muestreadas a 500 Hz, cada una con una duración de 10 segundos. Incluye diagnósticos detallados de más de 70 tipos de condiciones cardíacas, anotadas por expertos médicos.

            ---

            ## 🌟 ¿Qué encontrarás en esta plataforma?

            ### 1. Visualización de registros ECG

            - **Señal original con ruido**:  
            La señal cruda tal como fue capturada, incluyendo artefactos reales de adquisición.

            - **Señal limpia**:  
            La misma señal, pero preprocesada utilizando filtros digitales para mejorar su legibilidad clínica.

            ---

            ### 2. Análisis automático de la señal

            Con ayuda de la librería **[NeuroKit2](https://github.com/neuropsychology/NeuroKit)**, se realiza un análisis automático de la señal:

            - Limpieza digital con `nk.ecg_clean`
            - Detección de picos R con `nk.ecg_peaks`
            - Cálculo de intervalos RR
            - Estimación de la frecuencia cardíaca (bpm)
            - Identificación de latidos anómalos

            ---

            ## 🔬 Flujo de trabajo

            1. **Selecciona un registro** desde el dataset.
            2. **Visualiza** la señal cruda y la limpia.
            3. **Analiza automáticamente** el ritmo cardíaco con NeuroKit2.
            4. **Observa los resultados** directamente desde el dashboard.

            ---

            ## 🧠 Propósito de la Plataforma

            Brindar una herramienta educativa e interactiva que permita visualizar, explorar y analizar señales ECG reales, fomentando el aprendizaje y la investigación en el área de electrofisiología y ciencia de datos biomédicos.

            ---

            ## 📚 Referencias

            - 📄 *Zheng, J. et al. (2020)*. A 12-lead electrocardiogram database for arrhythmia research covering more than 10,000 patients. Scientific Data, 7, 48. [DOI:10.1038/s41597-020-0386-x](https://www.nature.com/articles/s41597-020-0386-x)

            - 🔗 Dataset: [https://physionet.org/content/ecg-arrhythmia/1.0.0/WFDBRecords/](https://physionet.org/content/ecg-arrhythmia/1.0.0/WFDBRecords/)

            - 🧪 NeuroKit2: [https://github.com/neuropsychology/NeuroKit](https://github.com/neuropsychology/NeuroKit)

            ---

            _Disfruta explorando las señales del corazón ❤️_

        """
    )

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