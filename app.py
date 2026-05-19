import streamlit as st
import pandas as pd

st.set_page_config(page_title="Controle de Faturas", layout="wide")

# Simulação (depois vamos conectar ao Sheets)
df = pd.DataFrame({
    "ID": [1,2,3],
    "Cliente": ["Cliente A", "Cliente B", "Cliente C"],
    "UC": ["123", "456", "789"],
    "Mês Referência": ["2026-05","2026-05","2026-05"],
    "Data de Emissão": ["2026-05-01","2026-05-02","2026-05-03"],
    "Status": ["AGUARDANDO","RECEBIDA","VALIDADA"]
})

st.title("📊 Controle de Faturas")

# KPIs
col1, col2, col3, col4 = st.columns(4)

col1.metric("Aguardando", len(df[df["Status"] == "AGUARDANDO"]))
col2.metric("Recebidas", len(df[df["Status"] == "RECEBIDA"]))
col3.metric("Validadas", len(df[df["Status"] == "VALIDADA"]))
col4.metric("Enviadas", len(df[df["Status"] == "ENVIADA"]))

st.divider()

# Filtro
status = st.selectbox("Filtrar por status", ["Todos"] + list(df["Status"].unique()))

if status != "Todos":
    df = df[df["Status"] == status]

st.dataframe(df)

st.divider()

# Atualização de status
st.subheader("Atualizar Status")

id_fatura = st.text_input("ID da fatura")
novo_status = st.selectbox("Novo Status", ["AGUARDANDO","RECEBIDA","VALIDADA","ENVIADA"])

if st.button("Atualizar"):
    st.success(f"Fatura {id_fatura} atualizada para {novo_status}")
