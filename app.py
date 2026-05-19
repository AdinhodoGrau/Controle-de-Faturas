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
status_filtro = st.selectbox("Filtrar por status", ["Todos"] + list(df["Status"].unique()))

if status_filtro != "Todos":
    df_filtrado = df[df["Status"] == status_filtro]
else:
    df_filtrado = df.copy()

# Opções de status
status_opcoes = ["AGUARDANDO", "RECEBIDA", "VALIDADA", "ENVIADA"]

st.subheader("📋 Tabela de Faturas")

# Tabela editável
df_editado = st.data_editor(
    df_filtrado,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            options=status_opcoes
        )
    },
    use_container_width=True,
    num_rows="dynamic"
)

st.divider()

# Botão de salvar (simulação por enquanto)
if st.button("💾 Salvar alterações"):
    st.success("Alterações salvas! (em breve conectado ao Google Sheets)")
