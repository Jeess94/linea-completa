import streamlit as st
import plotly.graph_objects as go
import math
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador de Balance de Línea")
st.title("🏭 Simulador de Precisión: Puntos de Caída")
st.markdown("Ahora las bolsas (puntos) caen en la **posición exacta** dentro de la Cinta 7, respetando el layout.")

# --- 1. DEFINICIÓN DEL LAYOUT ---
# Nota: Ajusté levemente las coordenadas para que las caídas coincidan visualmente perfecto
layout_props = {
    # Sector Izquierda (Entradas)
    "Cinta 1":  {"x": 0,    "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},
    "Cinta 2":  {"x": 6,    "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 4"], "dir": (1,0)},
    
    # Bajadas Verticales
    "Cinta 3":  {"x": 3.5,  "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 4":  {"x": 5.0,  "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    
    # Línea Principal (Recolectora)
    # Cinta 7 empieza en X=2. Por tanto, Cinta 3 cae en el metro 1.5 (3.5 - 2) y Cinta 4 en el metro 3.0 (5 - 2)
    "Cinta 7":  {"x": 2,    "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)},
    "Cinta 8":  {"x": 10.5, "y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5, "y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5, "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    
    # Salida y Subida
    "Cinta 11": {"x": 23,   "y": 2, "w": 1.5, "h": 3.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 12"], "dir": (0,1)},
    "Cinta 12": {"x": 23,   "y": 6, "w": 2, "h": 2, "type": "cinta", "color": "#FFD700", "next": ["Tobogán"], "dir": (1,0)},
    "Tobogán":  {"x": 25.5, "y": 6.5,"w": 3, "h": 1, "type": "tobogan", "color": "#C0C0C0", "next": ["Cinta 13"], "dir": (1,0)},
    "Cinta 13": {"x": 29,   "y": 6.5,"w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["ROBOT"], "dir": (1,0)},
    "ROBOT":    {"x": 33,   "y": 6.5,"w": 1, "h": 1, "type": "robot", "color": "#4CAF50", "next": [], "dir": (0,0)},
}

# --- 2. CONFIGURACIÓN INICIAL ---
if 'equipos_config' not in st.session_state:
    st.session_state.equipos_config = {}
    for nombre, props in layout_props.items():
        is_cinta = props['type'] == 'cinta'
        st.session_state.equipos_config[nombre] = {
            "largo_m": props['w'] if props['dir'] != (0,1) and props['dir'] != (0,-1) else props['h'], # Estimación automática
            "ancho_mm": 500,
            "rodillo_mm": 120 if is_cinta else 0,
            "rpm": 30 if is_cinta else 0,
            "velocidad_m_s": 0.3 # Un poco más rápido por defecto
        }
    # Ajuste manual de largo para Cinta 7 para que coincida con el dibujo
    st.session_state.equipos_config["Cinta 7"]["largo_m"] = 8.0 

# --- 3. BARRA LATERAL ---
st.sidebar.header("🎛️ Panel de Control")
sec_entrada = st.sidebar.number_input("Entrada: 1 bolsa cada (seg)", value=2.0, step=0.5)
target_robot = st.sidebar.number_input("Objetivo Robot (bolsas/h)", value=600)

st.sidebar.divider()
st.sidebar.subheader("🔧 Velocidades")
equipo_sel = st.sidebar.selectbox("Configurar Equipo:", [k for k in layout_props.keys() if k != "ROBOT"])
conf = st.session_state.equipos_config[equipo_sel]

if layout_props[equipo_sel]['type'] == 'cinta':
    col1, col2 = st.sidebar.columns(2)
    nuevo_rodillo = col1.number_input("Ø Rodillo (mm)", value=int(conf['rodillo_mm']), step=10)
    nueva_rpm = col2.number_input("RPM", value=int(conf['rpm']), step=5)
    v_ms = (math.pi * nuevo_rodillo * nueva_rpm) / 60000
    st.sidebar.metric("Velocidad", f"{v_ms*60:.1f} m/min")
else:
    v_ms = 1.5
    nuevo_rodillo, nueva_rpm = 0, 0
    st.sidebar.info("Gravedad (Estándar)")

st.session_state.equipos_config[equipo_sel].update({
    "rodillo_mm": nuevo_rodillo, "rpm": nueva_rpm, "velocidad_m_s": v_ms
})

# --- 4. MOTOR DE SIMULACIÓN CON OFFSET ---
def simular_offset(layout, configs, intervalo, duracion=40, paso=0.1):
    frames = []
    bolsas = []
    t_acum = 0
    id_counter = 0
    
    steps = int(duracion / paso)
    
    for step in range(steps):
        t_acum += paso
        
        # Generación de bolsas
        if t_acum >= intervalo:
            t_acum = 0
            origen = "Cinta 1" if (id_counter % 2 == 0) else "Cinta 2"
            props = layout[origen]
            bolsas.append({
                'id': id_counter,
                'cinta': origen,
                'dist': 0.0,      # Metros recorridos en la cinta actual
                'x': props['x'],  # Coordenada visual X inicial
                'y': props['y'] + props['h']/2, # Coordenada visual Y inicial
                'estado': 'ok'
            })
            id_counter += 1
            
        bolsas_activas = []
        for b in bolsas:
            cinta_nom = b['cinta']
            cinta_props = layout[cinta_nom]
            cinta_conf = configs.get(cinta_nom, {'velocidad_m_s': 0, 'largo_m': 1})
            
            # Avanzar distancia física
            avance = cinta_conf['velocidad_m_s'] * paso
            b['dist'] += avance
            
            # Chequear si llegó al final de la cinta actual
            if b['dist'] >= cinta_conf['largo_m']:
                next_list = cinta_props['next']
                if not next_list or next_list[0] == "ROBOT":
                    pass # Sale de la simulación o llega al robot
                else:
                    nueva_cinta = next_list[0]
                    nueva_props = layout[nueva_cinta]
                    
                    # --- AQUÍ ESTÁ LA MAGIA DEL OFFSET ---
                    # Calculamos dónde cae la bolsa físicamente
                    
                    # 1. Posición visual de donde viene (Fin de cinta anterior)
                    # Si es bajada vertical (C3, C4), tomamos su X central
                    if cinta_props['dir'] == (0, -1): 
                        drop_x = cinta_props['x'] + (cinta_props['w'] / 2)
                    else:
                        drop_x = cinta_props['x'] + cinta_props['w']
                        
                    # 2. Calculamos el offset en la nueva cinta
                    # Si la nueva cinta es horizontal (como Cinta 7)
                    if nueva_props['dir'] == (1, 0):
                        # Offset = Coordenada X de caída - Coordenada X inicio nueva cinta
                        offset_entrada = drop_x - nueva_props['x']
                        # Seguridad: el offset no puede ser negativo
                        offset_entrada = max(0.0, offset_entrada)
                    else:
                        offset_entrada = 0.0 # Si no es horizontal compleja, empieza en 0
                        
                    # Aplicamos el cambio
                    b['cinta'] = nueva_cinta
                    b['dist'] = offset_entrada # <--- ESTO COLOCA LA BOLSA EN EL LUGAR CORRECTO
                    
                    # Actualizamos coords visuales para que no haya "teletransportación" visual rara
                    if nueva_props['dir'] == (1,0):
                        b['y'] = nueva_props['y'] + nueva_props['h']/2
                        b['x'] = nueva_props['x'] + offset_entrada # Visualmente empieza adelantada
                    
                    bolsas_activas.append(b)
            else:
                # Movimiento Visual Normal dentro de la cinta
                # Calculamos X e Y basado en la 'dist' actual y la dirección de la cinta
                if cinta_props['dir'] == (1, 0): # Horizontal Derecha
                    b['x'] = cinta_props['x'] + b['dist']
                    b['y'] = cinta_props['y'] + cinta_props['h']/2
                elif cinta_props['dir'] == (0, -1): # Vertical Abajo
                    b['x'] = cinta_props['x'] + cinta_props['w']/2
                    b['y'] = (cinta_props['y'] + cinta_props['h']) - b['dist'] # Ojo: coordenada Y crece hacia arriba en Plotly
                elif cinta_props['dir'] == (0, 1): # Vertical Arriba
                    b['x'] = cinta_props['x'] + cinta_props['w']/2
                    b['y'] = cinta_props['y'] + b['dist']
                
                bolsas_activas.append(b)
                
        # Detección visual simple de choques
        for i in range(len(bolsas_activas)):
            b1 = bolsas_activas[i]
            b1['estado'] = 'ok' # Reset
            for j in range(i + 1, len(bolsas_activas)):
                b2 = bolsas_activas[j]
                # Si están en la misma cinta y muy cerca
                if b1['cinta'] == b2['cinta'] and abs(b1['dist'] - b2['dist']) < 0.6:
                    b1['estado'] = 'choque'
                    b2['estado'] = 'choque'
                    
        bolsas = bolsas_activas
        
        # Guardar Frame
        colores = ['#FF0000' if b['estado'] == 'choque' else '#0000FF' for b in bolsas]
        tamano = [12 if b['estado'] == 'choque' else 9 for b in bolsas]
        
        frames.append({
            'x': [b['x'] for b in bolsas],
            'y': [b['y'] for b in bolsas],
            'c': colores,
            's': tamano
        })
        
    return frames

# Ejecutar lógica
datos_anim = simular_offset(layout_props, st.session_state.equipos_config, sec_entrada)

# --- 5. VISUALIZACIÓN ---
fig = go.Figure()

# Dibujar Fondo (Cintas)
for k, v in layout_props.items():
    fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                  fillcolor=v['color'], line=dict(color="#333", width=1))
    # Etiquetas
    fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=f"<b>{k}</b>", 
                       showarrow=False, font=dict(size=9, color="#444"))

# Trace Inicial
fig.add_trace(go.Scatter(x=[], y=[], mode="markers", marker=dict(color="blue", size=10)))

# Construir Frames
plotly_frames = []
for f in datos_anim:
    plotly_frames.append(go.Frame(data=[
        go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=f['s']))
    ]))

fig.frames = plotly_frames

fig.update_layout(
    width=1000, height=600,
    xaxis=dict(visible=False, range=[-1, 35], fixedrange=True),
    yaxis=dict(visible=False, range=[0, 10], scaleanchor="x", scaleratio=1, fixedrange=True),
    plot_bgcolor="#e6e9ef",
    title="Visualización de Flujo en Planta",
    updatemenus=[dict(type="buttons", showactive=False,
        buttons=[dict(label="▶️ Play Simulación", method="animate", 
                      args=[None, dict(frame=dict(duration=50, redraw=True), fromcurrent=True)])])]
)

st.plotly_chart(fig, use_container_width=True)
st.caption("🔵 Puntos Azules: Flujo Normal | 🔴 Puntos Rojos: Posible Colisión/Atasco")
