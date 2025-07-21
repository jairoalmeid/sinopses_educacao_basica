import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(
    page_title="Sinopse da Educação Básica",
    page_icon=None,
    layout="wide"
)

# --- Funções de Carregamento de Dados ---
@st.cache_data
def carregar_dados_educacionais(caminho_arquivo):
    """Carrega e trata os dados de matrículas."""
    try:
        df = pd.read_csv(caminho_arquivo, encoding='utf-8', sep=',')
        if df.shape[1] == 1: df = pd.read_csv(caminho_arquivo, encoding='utf-8', sep=';')
    except FileNotFoundError:
        st.error(f"Erro: Arquivo educacional não encontrado em '{caminho_arquivo}'.")
        return None
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = [str(col).strip() for col in df.columns]
    colunas_texto = ['Região', 'Porte', 'Desenvolvimento', 'Codigo', 'Município']
    colunas_numericas = [col for col in df.columns if col not in colunas_texto]
    for col in colunas_numericas:
        if df[col].dtype == 'object':
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce')
    df[colunas_numericas] = df[colunas_numericas].fillna(0)
    return df

@st.cache_data
def carregar_dados_raciais(caminho_arquivo):
    """Carrega os dados do censo racial."""
    try:
        df = pd.read_csv(caminho_arquivo, encoding='utf-8', sep=',')
    except FileNotFoundError:
        st.warning(f"Aviso: Arquivo de dados raciais não encontrado. O recorte racial não será exibido.")
        return None
    return df

# --- Funções de Plotagem de Gráficos ---

def _criar_figura_donut_racial(df_ano, ano):
    """Função auxiliar para criar uma figura de gráfico de rosca."""
    colors = px.colors.qualitative.Pastel
    fig = go.Figure(data=[go.Pie(
        labels=df_ano['cor'], values=df_ano['populacao'], hole=.4,
        marker=dict(colors=colors, line=dict(color='#FFFFFF', width=2)),
        hovertemplate="<b>%{label}</b><br>População: %{value:,.0f}<br>Percentual: %{percent:.2%}<extra></extra>"
    )])
    fig.update_layout(
        title_text=f"Ano de {ano}", title_x=0.5,
        showlegend=True, legend_title_text='Cor/Raça',
        font=dict(family="Arial, sans-serif", color="black"),
        annotations=[dict(text=str(ano), x=0.5, y=0.5, font_size=20, showarrow=False)]
    )
    return fig

def plotar_graficos_raciais_comparativo(df_racial, municipio):
    """Gera os gráficos de rosca de 2010 e 2022 lado a lado com uma pergunta como título."""
    st.markdown(f"#### Qual foi a evolução do perfil demográfico de {municipio} entre 2010 e 2022?")
    col1, col2 = st.columns(2)
    with col1:
        dados_2010 = df_racial[(df_racial['municipio'].str.lower() == municipio.lower()) & (df_racial['ano'] == 2010)]
        if dados_2010.empty: st.info(f"Não há dados de 2010."); return
        fig_2010 = _criar_figura_donut_racial(dados_2010[dados_2010['cor'] != 'Total'], 2010)
        st.plotly_chart(fig_2010, use_container_width=True)
    with col2:
        dados_2022 = df_racial[(df_racial['municipio'].str.lower() == municipio.lower()) & (df_racial['ano'] == 2022)]
        if dados_2022.empty: st.info(f"Não há dados de 2022."); return
        fig_2022 = _criar_figura_donut_racial(dados_2022[dados_2022['cor'] != 'Total'], 2022)
        st.plotly_chart(fig_2022, use_container_width=True)

def plotar_treemap_geral(dados_municipio, modalidades, municipio):
    """Gera um gráfico Treemap com uma pergunta como título."""
    st.markdown(f"#### Como as matrículas de {municipio} se distribuem entre as modalidades do Ensino Básico?")
    labels, values = [], []
    for titulo, base_name in modalidades.items():
        total = int(dados_municipio.get(f'{base_name}Total', 0))
        if total > 0: labels.append(titulo.replace(" - ", "<br>")); values.append(total)

    if not values: st.info("Não há dados de matrícula para gerar a visão geral."); return
    fig = go.Figure(go.Treemap(
        labels=labels, parents=["Matrículas Totais"] * len(labels), values=values, textinfo="label+value+percent root",
        hovertemplate='<b>%{label}</b><br>Matrículas: %{value}<br>Percentual: %{percentRoot:.2%}<extra></extra>',
        marker=dict(colors=px.colors.qualitative.Pastel, line=dict(width=2, color='white')),
        pathbar=dict(visible=False), root_color="lightgrey"
    ))
    fig.update_layout(margin=dict(t=5, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

def plotar_grafico_dependencia(titulo, dados_municipio, base_name, municipio):
    """Gera o gráfico de barras com uma pergunta como título."""
    st.markdown(f"#### Em *{titulo}*, como as matrículas de {municipio} se dividem por dependência administrativa?")
    colunas = {'Total': f'{base_name}Total', 'Federal': f'{base_name}Federal', 'Estadual': f'{base_name}Estadual', 'Municipal': f'{base_name}Municipal', 'Privada': f'{base_name}Privada'}
    total_matriculas = int(dados_municipio.get(colunas['Total'], 0))
    dados_grafico = {k: int(dados_municipio.get(v, 0)) for k, v in colunas.items() if k != 'Total'}
    dados_grafico = {k: v for k, v in dados_grafico.items() if v > 0}

    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        st.metric(label="Total de Matrículas", value=f"{total_matriculas:,}".replace(",", "."))
    with col2:
        if not dados_grafico: st.info("Não há dados de matrícula para esta modalidade."); return
        df_grafico = pd.DataFrame(list(dados_grafico.items()), columns=['Dependência', 'Matrículas'])
        fig = go.Figure(data=[go.Bar(x=df_grafico['Dependência'], y=df_grafico['Matrículas'], text=df_grafico['Matrículas'], textposition='outside', texttemplate='%{text:,.0f}', marker_color='#0068C9')])
        fig.update_layout(yaxis_title="Nº de Matrículas", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# --- Interface Principal do Dashboard ---
st.title("Sinopse da Educação Básica")
st.markdown("A educação básica no Brasil compreende a educação infantil, o ensino fundamental e o ensino médio. Esta plataforma visualiza dados educacionais e demográficos para apoiar a análise e o planejamento.")

caminho_educacional = os.path.join("dados", "dep_administrativa.csv")
caminho_racial = os.path.join("dados", "cor_censo.csv")
df_educacional = carregar_dados_educacionais(caminho_educacional)
df_racial = carregar_dados_raciais(caminho_racial)

if df_educacional is not None:
    NOME_COLUNA_MUNICIPIO = 'Município'
    if NOME_COLUNA_MUNICIPIO not in df_educacional.columns:
        st.error(f"Erro Crítico: A coluna '{NOME_COLUNA_MUNICIPIO}' não foi encontrada.")
    else:
        st.sidebar.header("Filtros")
        municipios = sorted(df_educacional[NOME_COLUNA_MUNICIPIO].dropna().astype(str).unique())
        municipio_selecionado = st.sidebar.selectbox("Selecione o Município", municipios)
        dados_filtrados_educacional = df_educacional[df_educacional[NOME_COLUNA_MUNICIPIO].astype(str) == municipio_selecionado]

        if not dados_filtrados_educacional.empty:
            dados_municipio_educacional = dados_filtrados_educacional.iloc[0]
            st.header(f"Município: {municipio_selecionado}")

            info1, info2, info3 = st.columns(3)
            info1.markdown("##### Região Administrativa"); info1.markdown(f"**{dados_municipio_educacional.get('Região', 'N/A')}**")
            info2.markdown("##### Porte do Município"); info2.markdown(f"**{dados_municipio_educacional.get('Porte', 'N/A')}**")
            info3.markdown("##### Desenvolvimento Social"); info3.markdown(f"**{dados_municipio_educacional.get('Desenvolvimento', 'N/A')}**")
            
            st.markdown("---")
            modalidades = {"Ensino Fundamental - Anos Finais": "EFAnosFinais", "Ensino Médio Regular": "EnsinoMédioRegular", "Educação Profissional - Integrado": "EProfisIntegrado", "Educação Profissional - Concomitante": "EProfisConcomitante", "Educação Profissional - Subsequente": "EProfisSubsequente", "EJA - Ensino Fundamental": "EJAEnsinoFundamental", "EJA - Ensino Médio": "EJAEnsinoMédio"}
            plotar_treemap_geral(dados_municipio_educacional, modalidades, municipio_selecionado)
            
            st.markdown("---")
            if df_racial is not None:
                plotar_graficos_raciais_comparativo(df_racial, municipio_selecionado)

            st.markdown("---")
            st.header("Análise Detalhada por Modalidade de Ensino")
            for titulo, base_name in modalidades.items():
                plotar_grafico_dependencia(titulo, dados_municipio_educacional, base_name, municipio_selecionado)

# --- Rodapé ---
st.divider()
footer_cols = st.columns([1, 4])
with footer_cols[0]:
    st.image(os.path.join("Imagens", "logo.png"), width=720)
with footer_cols[1]:
    st.markdown("<p style='text-align: right; color: grey; font-size: 14px;'>Desenvolvido por:<br><b>NIS - Núcleo de Inteligência e Sustentabilidade | IFSP</b></p>", unsafe_allow_html=True)