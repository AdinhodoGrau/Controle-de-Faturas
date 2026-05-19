import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="Controle de Faturas", layout="wide")

# ── Conexão ────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.Client(auth=creds)

@st.cache_data(ttl=60)
def load_faturas(sheet_url: str) -> pd.DataFrame:
    client = get_client()
    sheet = client.open_by_url(sheet_url)
    data = sheet.worksheet("faturas").get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame(
        columns=["ID", "Cliente", "UC", "Mês Referência", "Data de Emissão", "Status"]
    )

@st.cache_data(ttl=300)
def load_clientes(sheet_url: str) -> pd.DataFrame:
    client = get_client()
    sheet = client.open_by_url(sheet_url)
    data = sheet.worksheet("clientes").get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame(columns=["ID", "Cliente", "UC"])

def save_faturas(df: pd.DataFrame, sheet_url: str):
    client = get_client()
    sheet = client.open_by_url(sheet_url).worksheet("faturas")
    df_str = df.astype(str).replace("nan", "")
    sheet.clear()
    sheet.update([df_str.columns.tolist()] + df_str.values.tolist())

def gerar_faturas_mes(df_faturas: pd.DataFrame, df_clientes: pd.DataFrame, mes_ref: str, sheet_url: str):
    """Gera uma linha AGUARDANDO para cada cliente no mês de referência."""
    faturas_existentes = df_faturas[df_faturas["Mês Referência"] == mes_ref]
    ucs_existentes = set(faturas_existentes["UC"].astype(str).tolist())

    novas = []
    proximo_id = int(df_faturas["ID"].max()) + 1 if not df_faturas.empty and "ID" in df_faturas.columns else 1

    for _, cliente in df_clientes.iterrows():
        if str(cliente["UC"]) not in ucs_existentes:

            # ✅ Monta a data de emissão: dia fixo do cliente + mês de referência
            try:
                dia = int(cliente["Data de Emissão"])  # ex: 10
                ano, mes = mes_ref.split("-")           # ex: "2026", "05"
                data_emissao = f"{ano}-{mes}-{dia:02d}" # ex: "2026-05-10"
            except:
                data_emissao = ""  # Se der erro, deixa em branco

            novas.append({
                "ID": proximo_id,
                "Cliente": cliente["Cliente"],
                "UC": cliente["UC"],
                "Mês Referência": mes_ref,
                "Data de Emissão": data_emissao,
                "Status": "AGUARDANDO"
            })
            proximo_id += 1

    if novas:
        df_novas = pd.DataFrame(novas)
        df_atualizado = pd.concat([df_faturas, df_novas], ignore_index=True)
        save_faturas(df_atualizado, sheet_url)
        st.cache_data.clear()
        return df_atualizado, len(novas)

    return df_faturas, 0

# ── Config ─────────────────────────────────────────────────────────────────────
SHEET_URL = st.secrets["SHEET_URL"]
MES_ATUAL = datetime.now().strftime("%Y-%m")  # ex: "2026-05"
MES_FORMATADO = datetime.now().strftime("%B de %Y").capitalize()  # ex: "Maio de 2026"

# ── Interface ──────────────────────────────────────────────────────────────────
st.title("📊 Controle de Faturas")
st.markdown(f"### 📅 Mês de Referência: `{MES_FORMATADO}`")
st.divider()

# Carrega dados
df_faturas  = load_faturas(SHEET_URL)
df_clientes = load_clientes(SHEET_URL)

# ── Geração automática do mês ──────────────────────────────────────────────────
if not df_clientes.empty:
    faturas_mes_atual = df_faturas[df_faturas["Mês Referência"] == MES_ATUAL]
    if faturas_mes_atual.empty:
        with st.spinner(f"Gerando faturas para {MES_FORMATADO}..."):
            df_faturas, qtd = gerar_faturas_mes(df_faturas, df_clientes, MES_ATUAL, SHEET_URL)
        st.success(f"✅ {qtd} faturas geradas automaticamente para {MES_FORMATADO}!")
        st.rerun()

# ── Filtra apenas mês atual ────────────────────────────────────────────────────
df_mes = df_faturas[df_faturas["Mês Referência"] == MES_ATUAL].copy()

# ── KPIs ───────────────────────────────────────────────────────────────────────
status_opcoes = ["AGUARDANDO", "RECEBIDA", "VALIDADA", "ENVIADA"]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Aguardando", len(df_mes[df_mes["Status"] == "AGUARDANDO"]))
col2.metric("Recebidas",  len(df_mes[df_mes["Status"] == "RECEBIDA"]))
col3.metric("Validadas",  len(df_mes[df_mes["Status"] == "VALIDADA"]))
col4.metric("Enviadas",   len(df_mes[df_mes["Status"] == "ENVIADA"]))

st.divider()

# ── Filtro de status ───────────────────────────────────────────────────────────
status_filtro = st.selectbox("Filtrar por status", ["Todos"] + status_opcoes)
df_filtrado = df_mes[df_mes["Status"] == status_filtro].copy() if status_filtro != "Todos" else df_mes.copy()

# ── Tabela editável ────────────────────────────────────────────────────────────
col_table, col_btn = st.columns([5, 1])
with col_table:
    st.subheader("📋 Faturas")
with col_btn:
    if st.button("🔄 Recarregar"):
        st.cache_data.clear()
        st.rerun()

df_editado = st.data_editor(
    df_filtrado,
    column_config={
        "Status": st.column_config.SelectboxColumn("Status", options=status_opcoes),
        "Data de Emissão": st.column_config.DateColumn("Data de Emissão", format="DD/MM/YYYY"),
    },
    use_container_width=True,
    num_rows="fixed",  # Clientes vêm da base, não se adicionam manualmente
    disabled=["ID", "Cliente", "UC", "Mês Referência"],  # Só Status e Data são editáveis
)

st.divider()

# ── Salvar ─────────────────────────────────────────────────────────────────────
if st.button("💾 Salvar alterações"):
    with st.spinner("Salvando no Google Sheets..."):
        df_faturas.update(df_editado)
        # Linhas novas (se houver)
        novos_ids = df_editado.index.difference(df_faturas.index)
        if not novos_ids.empty:
            df_faturas = pd.concat([df_faturas, df_editado.loc[novos_ids]])
        save_faturas(df_faturas, SHEET_URL)
        st.cache_data.clear()
    st.success("✅ Alterações salvas!")
    st.rerun()
