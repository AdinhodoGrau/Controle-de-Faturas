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
    return pd.DataFrame(data) if data else pd.DataFrame(columns=["ID", "Cliente", "UC", "Data de Emissão"])

def save_faturas(df: pd.DataFrame, sheet_url: str):
    if df.empty:
        st.error("⚠️ Operação cancelada: tentativa de salvar tabela vazia.")
        return
    client = get_client()
    sheet = client.open_by_url(sheet_url).worksheet("faturas")
    df_str = df.astype(str).replace("nan", "")
    sheet.clear()
    sheet.update([df_str.columns.tolist()] + df_str.values.tolist())

def gerar_faturas_mes(df_faturas: pd.DataFrame, df_clientes: pd.DataFrame, mes_ref: str, sheet_url: str):
    faturas_existentes = df_faturas[df_faturas["Mês Referência"] == mes_ref]
    ucs_existentes = set(faturas_existentes["UC"].astype(str).tolist())

    novas = []
    proximo_id = int(df_faturas["ID"].max()) + 1 if not df_faturas.empty and "ID" in df_faturas.columns else 1

    for _, cliente in df_clientes.iterrows():
        if str(cliente["UC"]) not in ucs_existentes:
            try:
                dia = int(cliente["Data de Emissão"])
                ano, mes = mes_ref.split("-")
                data_emissao = f"{ano}-{mes}-{dia:02d}"
            except:
                data_emissao = ""

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

def formatar_mes(mes_str: str) -> str:
    try:
        return datetime.strptime(mes_str, "%Y-%m").strftime("%B de %Y").capitalize()
    except:
        return mes_str

# ── Config ─────────────────────────────────────────────────────────────────────
SHEET_URL = st.secrets["SHEET_URL"]
MES_ATUAL = datetime.now().strftime("%Y-%m")
status_opcoes = ["AGUARDANDO", "RECEBIDA", "VALIDADA", "ENVIADA"]  # ✅ definido aqui, antes de tudo

# ── Interface ──────────────────────────────────────────────────────────────────
st.title("📊 Controle de Faturas")
st.divider()

# Carrega dados
df_faturas  = load_faturas(SHEET_URL)
df_clientes = load_clientes(SHEET_URL)

# ── Geração automática do mês atual ───────────────────────────────────────────
if not df_clientes.empty:
    if df_faturas[df_faturas["Mês Referência"] == MES_ATUAL].empty:
        with st.spinner(f"Gerando faturas para {formatar_mes(MES_ATUAL)}..."):
            df_faturas, qtd = gerar_faturas_mes(df_faturas, df_clientes, MES_ATUAL, SHEET_URL)
        st.success(f"✅ {qtd} faturas geradas para {formatar_mes(MES_ATUAL)}!")
        st.rerun()

# ── Seletor de mês ─────────────────────────────────────────────────────────────
meses_disponiveis = sorted(df_faturas["Mês Referência"].unique().tolist(), reverse=True)

mes_selecionado = st.selectbox(
    "📅 Mês de Referência",
    options=meses_disponiveis,
    format_func=formatar_mes,
    index=0
)

st.markdown(f"## 📅 {formatar_mes(mes_selecionado)}")

# ── KPIs ───────────────────────────────────────────────────────────────────────
df_mes = df_faturas[df_faturas["Mês Referência"] == mes_selecionado].copy()

st.markdown("""
<style>
.kpi-card {
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    backdrop-filter: blur(8px);
}
.kpi-label {
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 42px;
    font-weight: 800;
    line-height: 1;
}
.kpi-aguardando { background: rgba(220, 38, 38, 0.15); border: 1.5px solid rgba(220, 38, 38, 0.4); color: #FFFFFF; }
.kpi-recebida   { background: rgba(234, 88, 12, 0.15); border: 1.5px solid rgba(234, 88, 12, 0.4); color: #FFFFFF; }
.kpi-validada   { background: rgba(22, 163, 74, 0.15); border: 1.5px solid rgba(22, 163, 74, 0.4); color: #FFFFFF; }
.kpi-enviada    { background: rgba(37, 99, 235, 0.15); border: 1.5px solid rgba(37, 99, 235, 0.4); color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)

n_aguardando = len(df_mes[df_mes["Status"] == "AGUARDANDO"])
n_recebida   = len(df_mes[df_mes["Status"] == "RECEBIDA"])
n_validada   = len(df_mes[df_mes["Status"] == "VALIDADA"])
n_enviada    = len(df_mes[df_mes["Status"] == "ENVIADA"])

col1, col2, col3, col4 = st.columns(4)
col1.markdown(f'<div class="kpi-card kpi-aguardando"><div class="kpi-label">Aguardando</div><div class="kpi-value">{n_aguardando}</div></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="kpi-card kpi-recebida"><div class="kpi-label">Recebidas</div><div class="kpi-value">{n_recebida}</div></div>', unsafe_allow_html=True)
col3.markdown(f'<div class="kpi-card kpi-validada"><div class="kpi-label">Validadas</div><div class="kpi-value">{n_validada}</div></div>', unsafe_allow_html=True)
col4.markdown(f'<div class="kpi-card kpi-enviada"><div class="kpi-label">Enviadas</div><div class="kpi-value">{n_enviada}</div></div>', unsafe_allow_html=True)

st.divider()

# ── Filtro de status ───────────────────────────────────────────────────────────
status_filtro = st.selectbox("Filtrar por status", ["Todos"] + status_opcoes)
df_filtrado = df_mes[df_mes["Status"] == status_filtro].copy() if status_filtro != "Todos" else df_mes.copy()

# ── Prepara df para exibição ───────────────────────────────────────────────────
df_display = df_filtrado.copy()
df_display["Data de Emissão"] = pd.to_datetime(
    df_display["Data de Emissão"], errors="coerce"
).dt.date

# ── Tabela editável ────────────────────────────────────────────────────────────
col_table, col_btn = st.columns([6, 1])
with col_table:
    st.subheader("📋 Faturas")
with col_btn:
    if st.button("🔄 Recarregar"):
        st.cache_data.clear()
        st.rerun()

df_editado = st.data_editor(
    df_display,
    column_config={
        "Status": st.column_config.SelectboxColumn("Status", options=status_opcoes),
        "Data de Emissão": st.column_config.DateColumn("Data de Emissão", format="DD/MM/YYYY"),
    },
    use_container_width=True,
    num_rows="fixed",
    disabled=["ID", "Cliente", "UC", "Mês Referência"],
)

st.divider()

# ── Salvar ─────────────────────────────────────────────────────────────────────
if st.button("💾 Salvar alterações"):
    with st.spinner("Salvando no Google Sheets..."):
        df_para_salvar = df_editado.copy()
        df_para_salvar["Data de Emissão"] = df_para_salvar["Data de Emissão"].astype(str).replace("None", "")

        df_faturas.update(df_para_salvar)
        novos_ids = df_para_salvar.index.difference(df_faturas.index)
        if not novos_ids.empty:
            df_faturas = pd.concat([df_faturas, df_para_salvar.loc[novos_ids]])

        save_faturas(df_faturas, SHEET_URL)
        st.cache_data.clear()
    st.success("✅ Alterações salvas!")
    st.rerun()
