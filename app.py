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
    return gspread.Client(auth=creds)  # ✅ forma atual, authorize() está deprecado

@st.cache_data(ttl=60)
def load_data(sheet_url: str) -> pd.DataFrame:
    client = get_client()
    sheet = client.open_by_url(sheet_url).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_data(df: pd.DataFrame, sheet_url: str):
    client = get_client()
    sheet = client.open_by_url(sheet_url).sheet1
    # Converte tudo para string para evitar erros de tipo no Sheets
    df_str = df.astype(str).replace("nan", "")
    sheet.clear()
    sheet.update([df_str.columns.tolist()] + df_str.values.tolist())

# ── Configuração ───────────────────────────────────────────────────────────────
SHEET_URL = st.secrets["SHEET_URL"]
status_opcoes = ["AGUARDANDO", "RECEBIDA", "VALIDADA", "ENVIADA"]

# ── Interface ──────────────────────────────────────────────────────────────────
st.title("📊 Controle de Faturas")

# Botão de recarregar
col_title, col_reload = st.columns([6, 1])
with col_reload:
    if st.button("🔄 Recarregar"):
        st.cache_data.clear()
        st.rerun()

# Carrega dados
df = load_data(SHEET_URL)

# ── KPIs ───────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Aguardando", len(df[df["Status"] == "AGUARDANDO"]))
col2.metric("Recebidas",  len(df[df["Status"] == "RECEBIDA"]))
col3.metric("Validadas",  len(df[df["Status"] == "VALIDADA"]))
col4.metric("Enviadas",   len(df[df["Status"] == "ENVIADA"]))

st.divider()

# ── Filtro ─────────────────────────────────────────────────────────────────────
status_filtro = st.selectbox("Filtrar por status", ["Todos"] + status_opcoes)
df_filtrado = df[df["Status"] == status_filtro].copy() if status_filtro != "Todos" else df.copy()

# ── Tabela editável ────────────────────────────────────────────────────────────
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

# ── Salvar ─────────────────────────────────────────────────────────────────────
if st.button("💾 Salvar alterações"):
    if df_editado.empty:
        st.warning("⚠️ Nenhum dado para salvar.")
    else:
        with st.spinner("Salvando no Google Sheets..."):
            # ✅ Mescla correto: atualiza o df completo com as edições do filtrado
            df_final = df.copy()
            df_final.update(df_editado)

            # Linhas novas adicionadas na tabela filtrada (não existiam no df original)
            novos_ids = df_editado.index.difference(df_final.index)
            if not novos_ids.empty:
                df_final = pd.concat([df_final, df_editado.loc[novos_ids]])

            save_data(df_final, SHEET_URL)
            st.cache_data.clear()

        st.success(f"✅ {len(df_editado)} linha(s) salvas no Google Sheets!")
        st.rerun()  # Recarrega a tabela com os dados atualizados
