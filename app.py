import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px # Importamos o Plotly Express para acessar paletas de cores

# --- Configuração da Página ---
st.set_page_config(
    page_title="Sinopse da Educação Básica",
    page_icon="📊",
    layout="wide"
)

# --- Carregamento e Tratamento dos Dados ---
@st.cache_data
def carregar_dados(caminho_arquivo):
    """
    Carrega e trata os dados do arquivo CSV simplificado.
    """
    try:
        df = pd.read_csv(caminho_arquivo, encoding='utf-8', sep=',')
        if df.shape[1] == 1:
            df = pd.read_csv(caminho_arquivo, encoding='utf-8', sep=';')
    except FileNotFoundError:
        st.error(f"Erro: Arquivo não encontrado em '{caminho_arquivo}'. Verifique a pasta 'dados'.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo CSV: {e}")
        return None

    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = [str(col).strip() for col in df.columns]

    colunas_texto = ['Região', 'Porte', 'Desenvolvimento', 'Codigo', 'Município']
    colunas_numericas = [col for col in df.columns if col not in colunas_texto]

    for col in colunas_numericas:
        if df[col].dtype == 'object':
            df[col] = (
                df[col].astype(str)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df[colunas_numericas] = df[colunas_numericas].fillna(0)
    return df

def plotar_treemap_geral(dados_municipio, modalidades):
    """
    FUNÇÃO ATUALIZADA: Gera um gráfico Treemap com visual inspirado no Flourish.
    """
    st.subheader("Visão Geral das Matrículas")
    
    labels = []
    values = []

    for titulo, base_name in modalidades.items():
        total = int(dados_municipio.get(f'{base_name}Total', 0))
        if total > 0:
            labels.append(titulo.replace(" - ", "<br>"))
            values.append(total)

    if not values:
        st.info("Não há dados de matrícula para gerar a visão geral.")
        return

    # Paleta de cores inspirada no Flourish
    colors = px.colors.qualitative.Pastel
    
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=["Matrículas no Município"] * len(labels),
        values=values,
        textinfo="label+value+percent root",
        textfont=dict(size=15, family="Arial, sans-serif"),
        hovertemplate='<b>%{label}</b><br>Matrículas: %{value:,.0f}<br>Percentual: %{percentRoot:.2%}<extra></extra>',
        marker=dict(
            colors=colors,
            # Adiciona borda branca entre os blocos para clareza
            line=dict(width=2, color='white') 
        ),
        pathbar=dict(visible=False),
        root_color="lightgrey" # Cor do nó pai, se visível
    ))

    fig.update_layout(
        title_text='Distribuição Geral de Matrículas por Modalidade',
        title_font_size=22,
        title_x=0.5,
        margin=dict(t=50, l=10, r=10, b=10),
        font=dict(family="Arial, sans-serif", color="black"),
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="Arial, sans-serif"
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plotar_grafico_dependencia(titulo, dados_municipio, base_name):
    """
    Gera o gráfico de barras com a biblioteca Plotly para incluir os marcadores numéricos.
    """
    st.subheader(titulo)

    colunas = {
        'Total': f'{base_name}Total', 'Federal': f'{base_name}Federal',
        'Estadual': f'{base_name}Estadual', 'Municipal': f'{base_name}Municipal',
        'Privada': f'{base_name}Privada'
    }

    total_matriculas = int(dados_municipio.get(colunas['Total'], 0))
    dados_grafico = {
        'Federal': int(dados_municipio.get(colunas['Federal'], 0)),
        'Estadual': int(dados_municipio.get(colunas['Estadual'], 0)),
        'Municipal': int(dados_municipio.get(colunas['Municipal'], 0)),
        'Privada': int(dados_municipio.get(colunas['Privada'], 0))
    }
    
    dados_grafico = {k: v for k, v in dados_grafico.items() if v > 0}

    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        st.metric(label="Total de Matrículas", value=f"{total_matriculas:,}".replace(",", "."))
    with col2:
        if not dados_grafico:
            st.info("Não há dados de matrícula para esta modalidade.")
        else:
            df_grafico = pd.DataFrame(list(dados_grafico.items()), columns=['Dependência', 'Matrículas'])
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_grafico['Dependência'], y=df_grafico['Matrículas'],
                text=df_grafico['Matrículas'], textposition='outside',
                texttemplate='%{text:,.0f}', marker_color='#0068C9'
            ))
            
            fig.update_layout(
                title_text=f'Distribuição por Dependência - {titulo}',
                title_x=0.5, yaxis_title="Nº de Matrículas",
                xaxis_title="Dependência Administrativa", showlegend=False,
                uniformtext_minsize=8, uniformtext_mode='hide',
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

# --- Interface Principal do Dashboard ---
st.title("Sinopse da Educação Básica")
st.markdown("A educação básica no Brasil compreende a educação infantil, o ensino fundamental e o ensino médio, sendo a base da formação educacional de crianças e jovens. É um período fundamental para o desenvolvimento integral do indivíduo, preparando-o para o exercício da cidadania e para o futuro acesso ao ensino superior ou ao mercado de trabalho.")

caminho_do_arquivo = os.path.join("dados", "dep_administrativa.csv")
df = carregar_dados(caminho_do_arquivo)

if df is not None:
    NOME_COLUNA_MUNICIPIO = 'Município'

    if NOME_COLUNA_MUNICIPIO not in df.columns:
        st.error(f"Erro Crítico: A coluna '{NOME_COLUNA_MUNICIPIO}' não foi encontrada.")
        st.info("**Colunas encontradas:**")
        st.json(df.columns.tolist())
    else:
        st.sidebar.header("🔍 Filtros")
        
        municipios = sorted(df[NOME_COLUNA_MUNICIPIO].dropna().astype(str).unique())
        municipio_selecionado = st.sidebar.selectbox("Selecione o Município", municipios)

        dados_filtrados = df[df[NOME_COLUNA_MUNICIPIO].astype(str) == municipio_selecionado]

        if not dados_filtrados.empty:
            dados_municipio = dados_filtrados.iloc[0]
            st.header(f"Município: {municipio_selecionado}")

            st.markdown(f"**População:** ")
            st.markdown(f"**PIB:** ")
            st.markdown(f"**Taxa de desemprego:** ")

            st.markdown("---")
            info1, info2, info3 = st.columns(3)
            with info1:
                st.markdown("##### 🗺️ Região Administrativa")
                st.markdown(f"**{dados_municipio.get('Região', 'N/A')}**")
            with info2:
                st.markdown("##### 🏙️ Porte do Município")
                st.markdown(f"**{dados_municipio.get('Porte', 'N/A')}**")
            with info3:
                st.markdown("##### 🌱 Desenvolvimento Social")
                st.markdown(f"**{dados_municipio.get('Desenvolvimento', 'N/A')}**")
            
            st.markdown("---")

            modalidades = {
                "Ensino Fundamental - Anos Finais": "EFAnosFinais",
                "Ensino Médio Regular": "EnsinoMédioRegular",
                "Educação Profissional - Integrado": "EProfisIntegrado",
                "Educação Profissional - Concomitante": "EProfisConcomitante",
                "Educação Profissional - Subsequente": "EProfisSubsequente",
                "EJA - Ensino Fundamental": "EJAEnsinoFundamental",
                "EJA - Ensino Médio": "EJAEnsinoMédio"
            }

            plotar_treemap_geral(dados_municipio, modalidades)

            st.markdown("---")
            st.header("Análise Detalhada por Modalidade")

            for titulo, base_name in modalidades.items():
                plotar_grafico_dependencia(titulo, dados_municipio, base_name)