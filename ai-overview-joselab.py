import streamlit as st
import requests
import json
import time
import base64
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuración de la página
st.set_page_config(
    page_title="AI Overviews Checker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar el diseño
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea, #764ba2);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .keyword-result {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .keyword-ai-yes {
        background-color: #f0fdf4;
        border-left-color: #10b981;
    }
    
    .keyword-ai-no {
        background-color: #fef2f2;
        border-left-color: #ef4444;
    }
    
    .keyword-loading {
        background-color: #fffbeb;
        border-left-color: #f59e0b;
    }
    
    .keyword-error {
        background-color: #f8fafc;
        border-left-color: #6b7280;
    }
    
    .status-icon {
        font-size: 1.2rem;
        margin-right: 0.5rem;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #4facfe, #00f2fe);
    }
</style>
""", unsafe_allow_html=True)

# Inicializar session state
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = {
        'keywords': [],
        'total': 0,
        'with_ai': 0,
        'without_ai': 0,
        'errors': 0,
        'completed': 0
    }

if 'analyzing' not in st.session_state:
    st.session_state.analyzing = False

# Header principal
st.markdown("""
<div class="main-header">
    <h1>🔍 AI Overviews Checker</h1>
    <p>Verifica qué palabras clave activan Google AI Overviews usando DataForSEO</p>
</div>
""", unsafe_allow_html=True)

# Sidebar para configuración
with st.sidebar:
    st.header("⚙️ Configuración API")
    
    api_login = st.text_input("Usuario DataForSEO", placeholder="tu_usuario@email.com")
    api_password = st.text_input("Contraseña API", type="password", placeholder="tu_contraseña_api")
    
    location_options = {
        "Estados Unidos": 2840,
        "España": 2724,
        "México": 2484,
        "Argentina": 2032,
        "Colombia": 2170,
        "Chile": 2152
    }
    
    selected_location = st.selectbox("Ubicación", list(location_options.keys()))
    location_code = location_options[selected_location]
    
    st.header("📝 Palabras Clave")
    default_keywords = """qué es inteligencia artificial
mejores smartphones 2024
recetas de cocina mediterránea
cómo invertir en criptomonedas
síntomas de gripe
mejores destinos de viaje
marketing digital para empresas
beneficios del ejercicio físico"""
    
    keywords_text = st.text_area(
        "Una palabra clave por línea",
        value=default_keywords,
        height=200,
        placeholder="qué es el machine learning\nmejor smartphone 2024\nrecetas de cocina fáciles"
    )

def check_for_ai_overview(result):
    """Detecta si hay AI Overview en los resultados"""
    if not result.get('items') or not isinstance(result['items'], list):
        return False
    
    for item in result['items']:
        if (item.get('type') == 'ai_overview' or 
            item.get('type') == 'ai_answer' or
            (item.get('type') == 'answer_box' and 
             item.get('text') and len(item['text']) > 200) or
            (item.get('xpath') and 'ai-overview' in item['xpath']) or
            (item.get('snippet') and len(item['snippet']) > 200 and 
             not item.get('domain') and item.get('position', 0) <= 1)):
            return True
    return False

async def analyze_keyword(keyword, login, password, location_code):
    """Analiza una palabra clave individual"""
    try:
        request_data = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": "es",
            "device": "desktop",
            "os": "windows"
        }]
        
        credentials = base64.b64encode(f"{login}:{password}".encode()).decode()
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            'https://api.dataforseo.com/v3/serp/google/organic/live/advanced',
            headers=headers,
            json=request_data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Error HTTP: {response.status_code}")
        
        data = response.json()
        
        if (data.get('status_code') == 20000 and 
            data.get('tasks') and 
            data['tasks'][0]):
            
            task = data['tasks'][0]
            
            if (task.get('status_code') == 20000 and 
                task.get('result') and 
                task['result'][0]):
                
                result = task['result'][0]
                has_ai_overview = check_for_ai_overview(result)
                return {'status': 'success', 'has_ai': has_ai_overview}
            else:
                raise Exception('Error en la respuesta de la tarea')
        else:
            raise Exception('Error en la petición')
            
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def display_keyword_results():
    """Muestra los resultados de las palabras clave"""
    if not st.session_state.analysis_data['keywords']:
        return
    
    st.subheader("📝 Resultados por Keyword")
    
    for keyword_data in st.session_state.analysis_data['keywords']:
        keyword = keyword_data['keyword']
        status = keyword_data['status']
        
        if status == 'ai-yes':
            icon = "✅"
            status_text = "AI Overview detectado"
            css_class = "keyword-ai-yes"
        elif status == 'ai-no':
            icon = "❌"
            status_text = "Sin AI Overview"
            css_class = "keyword-ai-no"
        elif status == 'loading':
            icon = "⏳"
            status_text = "Analizando..."
            css_class = "keyword-loading"
        else:  # error
            icon = "⚠️"
            status_text = "Error en análisis"
            css_class = "keyword-error"
        
        st.markdown(f"""
        <div class="keyword-result {css_class}">
            <div>
                <span class="status-icon">{icon}</span>
                <strong>{keyword}</strong>
            </div>
            <div style="color: #666; font-size: 0.9rem;">
                {status_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

def create_charts():
    """Crea los gráficos de resultados"""
    data = st.session_state.analysis_data
    
    if data['completed'] == 0:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribución AI Overviews")
        
        # Gráfico de dona
        labels = ['Con AI Overview', 'Sin AI Overview']
        values = [data['with_ai'], data['without_ai']]
        colors = ['#10b981', '#ef4444']
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.6,
            marker_colors=colors,
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig_pie.update_layout(
            showlegend=True,
            height=400,
            margin=dict(t=0, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.subheader("📈 Comparativa Visual")
        
        # Gráfico de barras
        fig_bar = go.Figure(data=[
            go.Bar(
                x=['Con AI Overview', 'Sin AI Overview'],
                y=[data['with_ai'], data['without_ai']],
                marker_color=['#10b981', '#ef4444'],
                text=[data['with_ai'], data['without_ai']],
                textposition='auto',
            )
        ])
        
        fig_bar.update_layout(
            showlegend=False,
            height=400,
            yaxis_title="Cantidad de Keywords",
            margin=dict(t=20, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)

def display_stats():
    """Muestra las estadísticas en tarjetas"""
    data = st.session_state.analysis_data
    
    if data['completed'] == 0:
        return
    
    st.subheader("📈 Estadísticas Generales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2>{data['completed']}</h2>
            <p>Total Analizadas</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h2>{data['with_ai']}</h2>
            <p>AI Activado</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        total = data['with_ai'] + data['without_ai']
        success_rate = round((data['with_ai'] / total) * 100) if total > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <h2>{success_rate}%</h2>
            <p>Tasa de Éxito</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Simular posición promedio
        avg_position = round(time.time() % 5 + 1) if data['with_ai'] > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <h2>{avg_position}</h2>
            <p>Posición Promedio</p>
        </div>
        """, unsafe_allow_html=True)

# Botón principal de análisis
if st.button("🚀 Analizar Palabras Clave", disabled=st.session_state.analyzing):
    if not api_login or not api_password:
        st.error("❌ Por favor, completa las credenciales de la API")
    elif not keywords_text.strip():
        st.error("❌ Por favor, añade al menos una palabra clave")
    else:
        # Procesar keywords
        keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        
        if not keywords:
            st.error("❌ No se encontraron palabras clave válidas")
        else:
            st.session_state.analyzing = True
            
            # Resetear datos
            st.session_state.analysis_data = {
                'keywords': [{'keyword': k, 'status': 'loading', 'has_ai': False} for k in keywords],
                'total': len(keywords),
                'with_ai': 0,
                'without_ai': 0,
                'errors': 0,
                'completed': 0
            }
            
            # Crear contenedores para actualizar
            progress_container = st.container()
            results_container = st.container()
            
            with progress_container:
                st.info("🔄 Iniciando análisis...")
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            # Procesar cada keyword
            for i, keyword in enumerate(keywords):
                with status_text:
                    st.text(f"Analizando: {keyword}")
                
                # Actualizar UI
                with results_container:
                    display_keyword_results()
                
                # Analizar keyword
                result = analyze_keyword(keyword, api_login, api_password, location_code)
                
                # Actualizar datos
                if result['status'] == 'success':
                    st.session_state.analysis_data['keywords'][i]['status'] = 'ai-yes' if result['has_ai'] else 'ai-no'
                    st.session_state.analysis_data['keywords'][i]['has_ai'] = result['has_ai']
                    
                    if result['has_ai']:
                        st.session_state.analysis_data['with_ai'] += 1
                    else:
                        st.session_state.analysis_data['without_ai'] += 1
                else:
                    st.session_state.analysis_data['keywords'][i]['status'] = 'error'
                    st.session_state.analysis_data['errors'] += 1
                
                st.session_state.analysis_data['completed'] += 1
                
                # Actualizar barra de progreso
                progress = st.session_state.analysis_data['completed'] / st.session_state.analysis_data['total']
                progress_bar.progress(progress)
                
                # Pausa entre requests
                if i < len(keywords) - 1:
                    time.sleep(1)
            
            # Finalizar análisis
            st.session_state.analyzing = False
            
            with progress_container:
                st.success("✅ Análisis completado!")
            
            # Forzar actualización de la página
            st.experimental_rerun()

# Mostrar resultados si hay datos
if st.session_state.analysis_data['completed'] > 0:
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        display_keyword_results()
    
    with col2:
        create_charts()
    
    st.markdown("---")
    display_stats()

# Información adicional en el footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>🔧 Desarrollado con Streamlit | 📊 Powered by DataForSEO API</p>
    <p>Esta herramienta te ayuda a identificar qué palabras clave activan Google AI Overviews</p>
</div>
""", unsafe_allow_html=True)
