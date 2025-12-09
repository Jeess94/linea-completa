import streamlit as st
import plotly.graph_objects as go
import math
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador Individual de Cintas")
st.title("🏭 Configuración Detallada por Cinta")
st.markdown("Selecciona cada cinta individualmente para cargar sus datos de placa (Motor, Reductor, Largo) y obtener la velocidad teórica.")

# --- 1. LAYOUT FÍSICO (HORIZONTAL) ---
layout_props = {
    "Cinta 1":  {"x": 0,    "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},
    "Cinta 2":  {"x": 6,    "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 4"], "dir": (1,0)},
    "Cinta 3":  {"x": 3.5,  "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 4":  {"x": 5.0,  "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 7":  {"x": 2,    "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)},
    "Cinta 8":  {"x": 10.5, "y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5, "y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5, "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    "Cinta 11": {"x": 23,   "y": 2, "w": 1.5, "h": 3.5, "type": "cinta", "color": "#FFD700", "next": [], "dir": (0,1)},
}

# --- 2. ESTADO INICIAL ---
if 'equipos_config' not in st.session_state:
    st.session_state.equipos_config = {}
    for nombre, props in layout_props.items():
        # Lógica para detectar largo visual por defecto
        es_transversal = props['dir'] == (0, 1) or props['dir'] == (0, -1)
        largo_visual = props['h'] if es_transversal else props['w']
        if nombre == "Cinta 7": largo_visual = 8.0 
        
        st.session_state.equipos_config[nombre] = {
            "largo_m": largo_visual,
            "motor_rpm": 1450,    # Valor estándar
            "reductor_i": 20,     # Reductor estándar
            "rodillo_mm": 120,    # Rodillo necesario para el cálculo
            "velocidad_m_s": 0.0
        }

# --- 3. BARRA LATERAL (CONFIGURACIÓN INDIVIDUAL) ---
st.sidebar.header("🎛️ Panel de Ingeniería")

st.sidebar.subheader("🎯 Parámetros Globales")
sec_entrada = st.sidebar.number_input("Entrada (seg/bolsa)", value=3.0, step=0.5)
target_output = st.sidebar.number_input("Target Salida (b/h)", value=600, step=50)

st.sidebar.divider()
st.sidebar.subheader("🔧 Datos de Cinta (Individual)")

# 1. SELECCIÓN INDIVIDUAL
lista_cintas = list(layout_props.keys())
cinta_sel = st.sidebar.selectbox("Seleccionar Cinta:", lista_cintas)

# Recuperar datos guardados
conf = st.session_state.equipos_config[cinta_sel]

# 2. INPUTS DE DATOS
st.sidebar.markdown(f"**Editando: {cinta_sel}**")

# Largo
nuevo_largo = st.sidebar.number_input("📏 Largo de Cinta (m)", value=float(conf['largo_m']), step=0.5, format="%.2f")

# Motor y Reductor
c1, c2 = st.sidebar.columns(2)
nuevo_motor_rpm = c1.number_input("RPM Motor", value=int(conf['motor_rpm']), step=50, help="Velocidad nominal del motor")
nuevo_reductor = c2.number_input("Reductor (i)", value=int(conf['reductor_i']), step=5, help="Relación de reducción (ej. 20, 30)")

# Rodillo (Necesario para fórmula física)
nuevo_rodillo = st.sidebar.number_input("Ø Rodillo Motriz (mm)", value=int(conf['rodillo_mm']), step=10)

# 3. CÁLCULO DE VELOCIDAD TEÓRICA
# Fórmula: RPM Salida = RPM Motor / Reductor
# Velocidad = RPM Salida * Pi * Diámetro
if nuevo_reductor > 0 and nuevo_rodillo > 0:
    rpm_salida = nuevo_motor_rpm / nuevo_reductor
    velocidad_teorica_m_min = (rpm_salida * math.pi * nuevo_rodillo) / 1000
    velocidad_teorica_m_s = velocidad_teorica_m_min / 60
else:
    velocidad_teorica_m_min = 0
    velocidad_teorica_m_s = 0

# Mostrar Resultado Calculado
st.sidebar.info(f"⚡ **Velocidad Teórica:**\n\n# **{velocidad_teorica_m_min:.2f} m/min**")
st.sidebar.caption(f"(Equivale a {velocidad_teorica_m_s:.2f} m/s)")

# 4. GUARDAR CAMBIOS (Solo para la cinta seleccionada)
st.session_state.equipos_config[cinta_sel].update({
    "largo_m": nuevo_largo,
    "motor_rpm": nuevo_motor_rpm,
    "reductor_i": nuevo_reductor,
    "rodillo_mm": nuevo_rodillo,
    "velocidad_m_s": velocidad_teorica_m_s
})


# --- 4. SIMULACIÓN ---
def simular_flujo(layout, configs, intervalo, duracion=40, paso=0.1):
    frames = []
    bolsas = []
    llegadas_final = [] 
    t_acum = 0
    id_counter = 0
    steps = int(duracion / paso)
    
    for step in range(steps):
        t_actual = step * paso
        t_acum += paso
        
        # Generación
        if t_acum >= intervalo:
            t_acum = 0
            origen = "Cinta 1" if (id_counter % 2 == 0) else "Cinta 2"
            props = layout[origen]
            bolsas.append({
                'id': id_counter, 'cinta': origen, 'dist': 0.0,
                'x': props['x'], 'y': props['y'] + props['h']/2, 'estado': 'ok'
            })
            id_counter += 1
            
        bolsas_activas = []
        for b in bolsas:
            cinta_nom = b['cinta']
            cinta_props = layout[cinta_nom]
            cinta_conf = configs.get(cinta_nom, {'velocidad_m_s': 0, 'largo_m': 1})
            
            # Movimiento Físico
            avance = cinta_conf['velocidad_m_s'] * paso
            b['dist'] += avance
            
            # Transferencia
            if b['dist'] >= cinta_conf['largo_m']:
                next_list = cinta_props['next']
                if not next_list:
                    llegadas_final.append(t_actual) # Sale del sistema
                else:
                    nueva_cinta = next_list[0]
                    nueva_props = layout[nueva_cinta]
                    
                    # Cálculo Offset de Transferencia
                    if cinta_props['dir'] == (0, -1): # Transversal Bajando
                        fin_x = cinta_props['x'] + (cinta_props['w'] / 2)
                    else: # Horizontal
                        fin_x = cinta_props['x'] + cinta_props['w']
                        
                    if nueva_props['dir'] == (1, 0): # Entrando a Horizontal
                        offset = max(0.0, fin_x - nueva_props['x'])
                    else:
                        offset = 0.0
                    
                    b['cinta'] = nueva_cinta
                    b['dist'] = offset
                    
                    # Actualizar pos visual
                    if nueva_props['dir'] == (1,0): 
                        b['y'] = nueva_props['y'] + nueva_props['h']/2
                        b['x'] = nueva_props['x'] + offset
                    elif nueva_props['dir'] == (0,-1): 
                         b['x'] = nueva_props['x'] + nueva_props['w']/2
                         b['y'] = nueva_props['y'] + nueva_props['h'] 
                    elif nueva_props['dir'] == (0,1):
                         b['x'] = nueva_props['x'] + nueva_props['w']/2
                         b['y'] = nueva_props['y'] 

                    bolsas_activas.append(b)
            else:
                # Actualizar Visuales
                if cinta_props['dir'] == (1, 0): 
                    b['x'] = cinta_props['x'] + b['dist']
                    b['y'] = cinta_props['y'] + cinta_props['h']/2
                elif cinta_props['dir'] == (0, -1): 
                    b['x'] = cinta_props['x'] + cinta_props['w']/2
                    b['y'] = (cinta_props['y'] + cinta_props['h']) - b['dist'] 
                elif cinta_props['dir'] == (0, 1):
                    b['x'] = cinta_props['x'] + cinta_props['w']/2
                    b['y'] = cinta_props['y'] + b['dist']
                
                bolsas_activas.append(b)
                
        # Colisiones
        for i in range(len(bolsas_activas)):
            b1 = bolsas_activas[i]
            b1['estado'] = 'ok'
            for j in range(i + 1, len(bolsas_activas)):
                b2 = bolsas_activas[j]
                if b1['cinta'] == b2['cinta'] and abs(b1['dist'] - b2['dist']) < 0.6:
                    b1['estado'] = 'choque'
                    b2['estado'] = 'choque'
        
        bolsas = bolsas_activas
        colores = ['#D32F2F' if b['estado'] == 'choque' else '#0D47A1' for b in bolsas]
        tamano = [12 if b['estado'] == 'choque' else 10 for b in bolsas]
        
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colores, 's': tamano})
        
    return frames, llegadas_final

# Ejecutar Simulación
datos_anim, llegadas = simular_flujo(layout_props, st.session_state.equipos_config, sec_entrada)

# --- 5. VISUALIZACIÓN ---
col_main, col_stats = st.columns([3, 1])

with col_main:
    fig = go.Figure()
    # Cintas (Fondo)
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444", width=1), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=f"<b>{k}</b>", showarrow=False, font=dict(size=10))

    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="Bolsas"))

    plotly_frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=f['s'], line=dict(width=1, color="white")))]) for f in datos_anim]
    fig.frames = plotly_frames

    fig.update_layout(
        height=600, 
        xaxis=dict(visible=False, range=[-1, 26], fixedrange=True), 
        yaxis=dict(visible=False, range=[0, 10], scaleanchor="x", scaleratio=1, fixedrange=True),
        plot_bgcolor="#eff2f6",
        margin=dict(l=10, r=10, t=10, b=10),
        updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=0.95, buttons=[dict(label="▶️ PLAY", method="animate", args=[None, dict(frame=dict(duration=50, redraw=True), fromcurrent=True)])])]
    )
    st.plotly_chart(fig, use_container_width=True)

with col_stats:
    st.subheader("📊 Resultados")
    
    if len(llegadas) > 2:
        tiempo = llegadas[-1] - llegadas[0]
        ritmo = (len(llegadas) / tiempo) * 3600 if tiempo > 0 else 0
    else:
        ritmo = 0

    delta = ritmo - target_output
    st.metric("Salida C11 (b/h)", f"{ritmo:.0f}", delta=f"{delta:.0f}")
    
    st.markdown("---")
    st.markdown("**Resumen de Velocidades (m/min):**")
    
    # Crear un pequeño dataframe o tabla para ver todas a la vez
    resumen = {}
    for k, v in st.session_state.equipos_config.items():
        vel_min = v['velocidad_m_s'] * 60
        resumen[k] = f"{vel_min:.1f}"
    
    st.json(resumen)
