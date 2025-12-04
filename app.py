import streamlit as st
import plotly.graph_objects as go
import math

# Configuración de la página
st.set_page_config(layout="wide", page_title="Configurador de Layout Pro")

st.title("🏭 Configurador de Línea de Producción")

# --- 1. DEFINICIÓN DEL LAYOUT BASE ---
initial_layout = {
    # Sector Izquierda
    "Cinta 1":  {"x": 0,  "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "gold"},
    "Cinta 2":  {"x": 6,  "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "gold"},
    # Bajadas
    "Cinta 3":  {"x": 3.5, "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "gold"},
    "Cinta 4":  {"x": 5.0, "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "gold"},
    # Línea Principal
    "Cinta 7":  {"x": 2,  "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "gold"},
    "Cinta 8":  {"x": 10.5,"y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "gold"},
    "Cinta 9":  {"x": 12.5,"y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "gold"},
    "Cinta 10": {"x": 14.5,"y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "gold"},
    # Subida Derecha
    "Cinta 11": {"x": 23, "y": 2, "w": 1.5, "h": 3.5, "type": "cinta", "color": "gold"},
    # Final
    "Cinta 12": {"x": 23, "y": 6, "w": 2, "h": 2, "type": "cinta", "color": "gold"},
    "Tobogán":  {"x": 25.5,"y": 6.5,"w": 3, "h": 1, "type": "tobogan", "color": "silver"},
    "Cinta 13": {"x": 29, "y": 6.5,"w": 3, "h": 1, "type": "cinta", "color": "gold"},
}

# --- 2. GESTIÓN DEL ESTADO ---
if 'equipos' not in st.session_state:
    st.session_state.equipos = {}
    for nombre, props in initial_layout.items():
        st.session_state.equipos[nombre] = {
            "rodillo_mm": 100, # Diámetro default
            "rpm": 60,         # RPM default
            "velocidad_calc": 0.0,
            "angulo": 0 if props['type'] == 'cinta' else 45
        }

# --- 3. BARRA LATERAL (INPUTS) ---
st.sidebar.header("📊 Datos de Producción")

# Input de flujo de bolsas
bolsas_seg = st.sidebar.number_input("Bolsas por Segundo (Input)", value=3.0, step=0.1)

# Cálculos de proyección
bolsas_min = bolsas_seg * 60
bolsas_hora = bolsas_min * 60
bolsas_turno = bolsas_hora * 8

# Métricas visuales en la sidebar
st.sidebar.markdown("---")
st.sidebar.metric("Bolsas / Minuto", f"{bolsas_min:,.0f}")
st.sidebar.metric("Bolsas / Hora", f"{bolsas_hora:,.0f}")
st.sidebar.metric("Bolsas / Turno (8h)", f"{bolsas_turno:,.0f}")
st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ Configuración de Equipo")
equipo_seleccionado = st.sidebar.selectbox("Seleccionar Equipo:", list(initial_layout.keys()))

# Recuperar datos
datos = st.session_state.equipos[equipo_seleccionado]
tipo = initial_layout[equipo_seleccionado]['type']

if tipo == "cinta":
    st.sidebar.info(f"Editando: {equipo_seleccionado}")
    
    # Inputs para cálculo de velocidad
    col1, col2 = st.sidebar.columns(2)
    rodillo = col1.number_input("Ø Rodillo (mm)", value=datos["rodillo_mm"])
    rpm = col2.number_input("RPM Salida", value=datos["rpm"])
    
    # FÓRMULA: V = (Pi * Diámetro * RPM) / 1000
    velocidad = (math.pi * rodillo * rpm) / 1000
    
    st.sidebar.success(f"🚀 Velocidad: {velocidad:.2f} m/min")
    
    # Guardar
    st.session_state.equipos[equipo_seleccionado].update({
        "rodillo_mm": rodillo,
        "rpm": rpm,
        "velocidad_calc": velocidad
    })

else:
    # Tobogán
    st.sidebar.info(f"Editando: {equipo_seleccionado}")
    angulo = st.sidebar.slider("Ángulo de Inclinación", 0, 90, value=datos["angulo"])
    st.session_state.equipos[equipo_seleccionado]["angulo"] = angulo

# --- 4. VISUALIZACIÓN EN DASHBOARD SUPERIOR ---
# Mostramos KPIs grandes arriba del gráfico
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Throughput Actual", f"{bolsas_seg} bolsas/s", delta="Objetivo OK")
kpi2.metric("Capacidad Teórica", f"{bolsas_hora:,.0f} bolsas/h")
kpi3.metric("Tiempo de Ciclo", f"{1/bolsas_seg:.2f} seg/bolsa")

st.divider()

# --- 5. DIBUJAR EL LAYOUT ---
fig = go.Figure()

for nombre, layout in initial_layout.items():
    data = st.session_state.equipos[nombre]
    
    # Texto Hover dinámico
    if layout['type'] == 'cinta':
        hover_txt = (
            f"<b>{nombre}</b><br>"
            f"⚙️ Ø Rodillo: {data['rodillo_mm']} mm<br>"
            f"🔄 RPM: {data['rpm']}<br>"
            f"🚀 <b>Velocidad: {data['velocidad_calc']:.2f} m/min</b>"
        )
    else:
        hover_txt = (
            f"<b>{nombre}</b><br>"
            f"📐 Ángulo: {data['angulo']}°<br>"
            f"⬇️ Caída gravedad"
        )

    fig.add_shape(type="rect",
        x0=layout['x'], y0=layout['y'],
        x1=layout['x'] + layout['w'], y1=layout['y'] + layout['h'],
        line=dict(color="black", width=1),
        fillcolor=layout['color'],
    )
    
    # Zona de detección hover
    fig.add_trace(go.Scatter(
        x=[layout['x'] + layout['w']/2],
        y=[layout['y'] + layout['h']/2],
        text=[hover_txt],
        mode="text",
        hoverinfo="text",
        showlegend=False
    ))
    
    # Etiqueta visible
    fig.add_annotation(
        x=layout['x'] + layout['w']/2,
        y=layout['y'] + layout['h']/2,
        text=f"<b>{nombre}</b>",
        showarrow=False,
        font=dict(size=10, color="black")
    )

fig.update_layout(
    width=1000, height=600,
    xaxis=dict(visible=False, range=[-1, 35]),
    yaxis=dict(visible=False, scaleanchor="x", scaleratio=1, range=[0, 12]),
    plot_bgcolor="white",
    title="Planta - Vista Superior"
)

st.plotly_chart(fig, use_container_width=True)