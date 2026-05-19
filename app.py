import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Controle de Faturas", layout="wide")

# ── Conexão com Google Sheets ──────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=60)  # Atualiza os dados a cada 60 segundos
def load_data(sheet_url: str) -> pd.DataFrame:
    client = get_client()
    sheet = client.open_by_url(sheet_url).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_data(df: pd.DataFrame, sheet_url: str):
    client = get_client()
    sheet = client.open_by_url(sheet_url).sheet1
    sheet.clear()
    sheet.update([df.columns.tolist()] + df.values.tolist())

# ── Configuração ───────────────────────────────────────────────────────────────
SHEET_URL = st.secrets["SHEET_URL"]

# ── Interface ──────────────────────────────────────────────────────────────────
st.title("📊 Controle de Faturas")

df = load_data(SHEET_URL)

# KPIs
status_opcoes = ["AGUARDANDO", "RECEBIDA", "VALIDADA", "ENVIADA"]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Aguardando", len(df[df["Status"] == "AGUARDANDO"]))
col2.metric("Recebidas",  len(df[df["Status"] == "RECEBIDA"]))
col3.metric("Validadas",  len(df[df["Status"] == "VALIDADA"]))
col4.metric("Enviadas",   len(df[df["Status"] == "ENVIADA"]))

st.divider()

# Filtro
status_filtro = st.selectbox("Filtrar por status", ["Todos"] + status_opcoes)
df_filtrado = df[df["Status"] == status_filtro] if status_filtro != "Todos" else df.copy()

# Tabela editável
st.subheader("📋 Faturas")
df_editado = st.data_editor(
    df_filtrado,
    column_config={
        "Status": st.column_config.SelectboxColumn("Status", options=status_opcoes)
    },
    use_container_width=True,
    num_rows="dynamic",
)

st.divider()

# Salvar
if st.button("💾 Salvar alterações"):
    with st.spinner("Salvando no Google Sheets..."):
        # Atualiza apenas as linhas editadas no df original
        df.update(df_editado)
        save_data(df, SHEET_URL)
        st.cache_data.clear()  # Força recarregar na próxima vez
    st.success("✅ Alterações salvas no Google Sheets!")
