import streamlit as st
import agente

# ── Configuração da página ───────────────────────────
st.set_page_config(
    page_title="Agente de Roteiros de Viagem",
    page_icon="🌍",
    layout="centered"
)

st.title("🌍 Agente de Roteiros de Viagem")
st.caption("Preencha os dados abaixo e receba um roteiro completo com estimativas de custo.")

# ── Formulário de inputs ─────────────────────────────
with st.form("form_viagem"):
    st.subheader("📍 Origem e Destinos")
    origem = st.text_input("Cidade de origem", placeholder="ex: São Paulo, Brasil")
    destinos_raw = st.text_input(
        "Destinos focais (separe por vírgula)",
        placeholder="ex: Lisboa, Porto, Sevilha"
    )

    st.subheader("👥 Viajantes")
    col1, col2 = st.columns(2)
    with col1:
        qtd = st.number_input("Número de viajantes", min_value=1, max_value=20, value=2)
    with col2:
        duracao = st.number_input("Duração (dias)", min_value=3, max_value=90, value=10)

    perfil = st.text_area(
        "Perfil dos viajantes",
        placeholder="ex: casal de 35 e 38 anos, gostam de história, gastronomia e arquitetura",
        height=80
    )

    st.subheader("🗓️ Período e Orçamento")
    col3, col4 = st.columns(2)
    with col3:
        mes = st.text_input("Mês e ano da viagem", placeholder="ex: outubro de 2025")
    with col4:
        orcamento = st.number_input(
            "Orçamento total (R$)", min_value=1000, max_value=500000,
            value=18000, step=1000
        )

    gerar = st.form_submit_button("✈️ Gerar Roteiro Completo", use_container_width=True)

# ── Processar e exibir ───────────────────────────────
if gerar:
    # Validações
    if not origem or not destinos_raw or not perfil or not mes:
        st.error("Por favor, preencha todos os campos antes de gerar o roteiro.")
        st.stop()

    destinos = [d.strip() for d in destinos_raw.split(",") if d.strip()]

    # Gerar roteiro com spinner
    with st.spinner("🔄 Gerando seu roteiro personalizado... (pode levar ~40s)"):
        try:
            roteiro, custos, transportes, cambio = agente.gerar_roteiro(
                origem=origem,
                destinos=destinos,
                qtd_viajantes=int(qtd),
                perfil=perfil,
                duracao=int(duracao),
                mes=mes,
                orcamento=float(orcamento)
            )
        except Exception as e:
            st.error(f"Erro ao gerar roteiro: {e}")
            st.stop()

    st.success("✅ Roteiro gerado com sucesso!")

    # Métricas rápidas
    tr = transportes
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Destinos", len(destinos))
    col_b.metric("Total transportes", f"R$ {tr.get('total_geral_brl',0):,.0f}")
    col_c.metric(
        "Orçamento em EUR",
        f"€{agente.converter_brl(orcamento):,.0f}"
    )

    # Exibir conteúdo em abas
    aba1, aba2, aba3 = st.tabs(["📅 Roteiro Completo", "💰 Custos", "✈️ Transportes"])

    with aba1:
        st.markdown(roteiro)

    with aba2:
        st.markdown(custos)

    with aba3:
        ida   = tr.get("voo_ida", {})
        volta = tr.get("voo_volta", {})
        st.markdown(f"**✈️ Voo de ida:** {ida.get('trecho')} | {ida.get('duracao')} | R$ {ida.get('preco_total_brl',0):,.0f}")
        st.caption(f"💡 {ida.get('dica','')}")
        st.markdown(f"**✈️ Voo de volta:** {volta.get('trecho')} | {volta.get('duracao')} | R$ {volta.get('preco_total_brl',0):,.0f}")
        st.markdown("**🚆 Transportes internos:**")
        for t in tr.get("transportes_internos", []):
            st.markdown(f"- **{t.get('trecho')}**: {t.get('meio')} | {t.get('duracao')} | R$ {t.get('preco_total_brl',0):,.0f}")
            st.caption(f"💡 {t.get('dica','')}")

    # Botão de download
    conteudo = f"ROTEIRO COMPLETO\n{'='*50}\n{roteiro}\n\nCUSTOS\n{'='*50}\n{custos}"
    st.download_button(
        label="⬇️ Baixar roteiro em .txt",
        data=conteudo.encode("utf-8"),
        file_name=f"roteiro_{destinos[0].lower().replace(' ','_')}.txt",
        mime="text/plain",
        use_container_width=True
    )
