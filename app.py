import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import math
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador de Balance de Línea")
st.title("⚖️ Calibrador de Velocidad de Línea")
st.markdown("Ajusta las velocidades para evitar que las bolsas se **choquen (velocidad baja)** o que el robot quede **desabastecido**.")

# --- 1. CONFIGURACIÓN DEL LAYOUT (Tu diseño) ---
layout_props = {
    "Cinta 1":  {"x": 0,  "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},
    "Cinta 2":  {"x": 6,  "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 4"], "dir": (1,0)},
    "Cinta 3":  {"x": 3.5, "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 4":  {"x": 5.0, "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 7":  {"x": 2,  "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)},
    "Cinta 8":  {"x": 10.5,"y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5,"y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5,"y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    "Cinta 11": {"x": 23, "y": 2, "w": 1.5, "h": 3.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 12"], "dir": (0,1)},
    "Cinta 12": {"x": 23, "y": 6, "w": 2, "h": 2, "type": "cinta", "color": "#FFD700", "next": ["Tobogán"], "dir": (1,0)},
    "Tobogán":  {"x": 25.5,"y": 6.5,"w": 3, "h": 1, "type": "tobogan", "color": "#C0C0C0", "next": ["Cinta 13"], "dir": (1,0)},
    "Cinta 13": {"x": 29, "y": 6.5,"w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["ROBOT"], "dir": (1,0)},
    "ROBOT":    {"x": 33, "y": 6.5,"w": 1, "h": 1, "type": "robot", "color": "#4CAF50", "next": [], "dir": (0,0)},
}

# --- 2. ESTADO Y CONFIGURACIÓN ---
if 'equipos_config' not in st.session_state:
    st.session_state.equipos_config = {}
    for nombre, props in layout_props.items():
        is_cinta = props['type'] == 'cinta'
        st.session_state.equipos_config[nombre] = {
            "largo_m": props['w'] * 0.5,
            "ancho_mm": 500,
            "rodillo_mm": 120 if is_cinta else 0,
            "rpm": 30 if is_cinta else 0,
            "velocidad_m_s": 0.18 # Valor inicial seguro
        }

# --- 3. PANEL DE CONTROL (IZQUIERDA) ---
st.sidebar.header("🎯 Objetivos de Producción")

# Input: Cadencia de Entrada Real
sec_entrada = st.sidebar.number_input("⏱️ Cada cuánto entra una bolsa (seg)", value=3.0, step=0.5, help="Tu dato real: 1 bolsa cada 3 seg")
tasa_entrada_hora = 3600 / sec_entrada
st.sidebar.caption(f"Esto equivale a una entrada de: **{tasa_entrada_hora:.0f} bolsas/hora**")

# Input: Objetivo del Robot
target_robot = st.sidebar.number_input("🤖 Objetivo del Robot (bolsas/hora)", value=600, step=50)

st.sidebar.divider()
st.sidebar.subheader("⚙️ Ajuste de Velocidades")

equipo_sel = st.sidebar.selectbox("Editar Equipo:", [k for k in layout_props.keys() if k != "ROBOT"])
conf = st.session_state.equipos_config[equipo_sel]

# Control simplificado de velocidad
if layout_props[equipo_sel]['type'] == 'cinta':
    col1, col2 = st.sidebar.columns(2)
    nuevo_rodillo = col1.number_input("Ø Rodillo (mm)", value=int(conf['rodillo_mm']), step=10)
    nueva_rpm = col2.number_input("RPM Motor", value=int(conf['rpm']), step=5)
    v_ms = (math.pi * nuevo_rodillo * nueva_rpm) / 60000
    st.sidebar.metric("Velocidad Cinta", f"{v_ms*60:.1f} m/min", delta_color="off")
else:
    # Tobogán
    v_ms = 1.0 # Fijo gravedad
    nuevo_rodillo, nueva_rpm = 0, 0
    st.sidebar.info("Tobogán: Velocidad por gravedad")

st.session_state.equipos_config[equipo_sel].update({
    "rodillo_mm": nuevo_rodillo, "rpm": nueva_rpm, "velocidad_m_s": v_ms
})


# --- 4. LÓGICA DE SIMULACIÓN ---
def simular(layout, configs, intervalo_entrada, duracion, paso_t=0.1):
    frames = []
    bolsas = []
    llegadas_robot = [] # Tiempos en los que llega una bolsa al final
    tiempo_acumulado = 0
    bolsa_id_counter = 0
    
    steps = int(duracion / paso_t)
    
    for step in range(steps):
        t_actual = step * paso_t
        
        # Generar bolsa
        tiempo_acumulado += paso_t
        if tiempo_acumulado >= intervalo_entrada:
            tiempo_acumulado = 0
            # Alternar entrada entre Cinta 1 y Cinta 2 para realismo
            entrada = "Cinta 1" if (bolsa_id_counter % 2 == 0) else "Cinta 2"
            props = layout[entrada]
            bolsas.append({
                'id': bolsa_id_counter,
                'x': props['x'], 'y': props['y'] + props['h']/2,
                'cinta': entrada, 'dist': 0.0, 'estado': 'ok'
            })
            bolsa_id_counter += 1
            
        bolsas_activas = []
        
        # Mover bolsas
        for b in bolsas:
            # Detectar choques simples (si dos bolsas están muy cerca en la misma cinta)
            # Simplificación: si la distancia entre esta bolsa y la anterior es < 0.5m
            b['estado'] = 'ok' # Reset
            
            curr_conf = configs.get(b['cinta'], {'velocidad_m_s': 0})
            desp = curr_conf['velocidad_m_s'] * paso_t
            
            # Factor visual
            props_vis = layout[b['cinta']]
            escala = props_vis['w'] / curr_conf['largo_m'] if curr_conf['largo_m'] > 0 else 1
            
            b['dist'] += desp
            
            # Lógica de cambio de cinta
            largo_real = curr_conf.get('largo_m', 5)
            if b['dist'] >= largo_real:
                siguientes = layout[b['cinta']]['next']
                if siguientes:
                    if siguientes[0] == "ROBOT":
                        llegadas_robot.append(t_actual)
                        # Bolsa sale del sistema
                    else:
                        # Pasa a siguiente
                        nueva = siguientes[0]
                        b['cinta'] = nueva
                        b['dist'] = 0.0
                        
                        # Ubicar visualmente
                        n_props = layout[nueva]
                        # Lógica simple de conexión visual
                        if layout[b['cinta']]['dir'] == (0,1): # Vertical hacia arriba
                             b['x'] = n_props['x'] + n_props['w']/2
                             b['y'] = n_props['y']
                        else:
                             b['x'] = n_props['x']
                             b['y'] = n_props['y'] + n_props['h']/2
                        bolsas_activas.append(b)
            else:
                # Movimiento visual
                dx, dy = layout[b['cinta']]['dir']
                b['x'] += dx * (desp * escala)
                b['y'] += dy * (desp * escala)
                bolsas_activas.append(b)

        # Chequeo de colisiones (Básico: distancia entre puntos)
        for i in range(len(bolsas_activas)):
            for j in range(i + 1, len(bolsas_activas)):
                b1 = bolsas_activas[i]
                b2 = bolsas_activas[j]
                dist_euclidea = math.sqrt((b1['x']-b2['x'])**2 + (b1['y']-b2['y'])**2)
                # Umbral de choque visual
                if dist_euclidea < 0.8: 
                    b1['estado'] = 'choque'
                    b2['estado'] = 'choque'

        bolsas = bolsas_activas
        
        # Guardar frame
        colores = ['red' if b['estado'] == 'choque' else 'blue' for b in bolsas]
        frames.append({
            'x': [b['x'] for b in bolsas],
            'y': [b['y'] for b in bolsas],
            'c': colores,
            'count': len(llegadas_robot)
        })

    return frames, llegadas_robot

# Ejecutar simulación
datos, llegadas = simular(layout_props, st.session_state.equipos_config, sec_entrada, duracion=40)

# --- 5. RESULTADOS VISUALES ---
col_res1, col_res2 = st.columns([3, 1])

with col_res1:
    fig = go.Figure()
    
    # Dibujar Layout
    for k, v in layout_props.items():
        color = v['color']
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=color, line=dict(color="black", width=1))
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=k, showarrow=False, font=dict(size=8))

    # Trace Bolsas
    fig.add_trace(go.Scatter(
        x=[], y=[], mode="markers", 
        marker=dict(size=10, color="blue"), name="Bolsas"
    ))

    # Animación
    frames_plotly = []
    for f in datos:
        frames_plotly.append(go.Frame(
            data=[go.Scatter(x=f['x'], y=f['y'], marker=dict(color=f['c']))]
        ))
    
    fig.frames = frames_plotly
    fig.update_layout(
        width=800, height=500, xaxis=dict(visible=False, range=[-1, 35]), yaxis=dict(visible=False, range=[0, 10], scaleanchor="x"),
        updatemenus=[dict(type="buttons", buttons=[dict(label="▶️ Play", method="animate", args=[None, dict(frame=dict(duration=100))])])]
    )
    st.plotly_chart(fig, use_container_width=True)

with col_res2:
    st.subheader("📊 Diagnóstico")
    
    # Cálculo de Ritmo Final
    if len(llegadas) > 1:
        tiempo_total_llegadas = llegadas[-1] - llegadas[0]
        if tiempo_total_llegadas > 0:
            ritmo_real_hora = (len(llegadas) / tiempo_total_llegadas) * 3600
        else:
            ritmo_real_hora = 0
    else:
        ritmo_real_hora = 0
        
    delta = ritmo_real_hora - target_robot
    
    st.metric("Ritmo de Llegada al Robot", f"{ritmo_real_hora:.0f} b/h", delta=f"{delta:.0f} vs Objetivo")
    
    if ritmo_real_hora < target_robot * 0.8:
        st.error("⚠️ **Hambriento**: Las bolsas llegan muy lento o la simulación es corta.")
    elif ritmo_real_hora > target_robot * 1.2:
        st.warning("⚠️ **Saturado**: Llegan más bolsas de las que el robot pide.")
    else:
        st.success("✅ **Óptimo**: El flujo coincide con la capacidad del robot.")

    # Alerta de Colisiones
    choques = any('red' in f['c'] for f in datos)
    if choques:
        st.error("🚨 **ALERTA DE CHOQUE**: Bolsas encimadas. Aumenta la velocidad de las cintas de entrada.")
    else:
        st.info("Espaciado correcto entre bolsas.")
