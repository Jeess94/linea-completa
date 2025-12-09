import streamlit as st
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador Industrial")
st.title("🏭 Simulador de Línea: Control de Cadencia")
st.markdown("Control manual del **intervalo de salida** de bolsas.")

# --- 1. LAYOUT FÍSICO (Geometría Conectada) ---
layout_props = {
    # Nivel Superior (Y=6)
    "Cinta 1":  {"x": 0,    "y": 6, "w": 3.5, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},   # Derecha
    "Cinta 2":  {"x": 6.5,  "y": 6, "w": 3.5, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (-1,0)},  # Izquierda
    
    # Transversales (Bajan de Y=6 a Y=3)
    "Cinta 3":  {"x": 3.5,  "y": 3, "w": 1, "h": 3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},  # Baja
    "Cinta 4":  {"x": 5.5,  "y": 3, "w": 1, "h": 3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},  # Baja
    
    # Nivel Inferior (Y=1.5)
    "Cinta 7":  {"x": 2,    "y": 1.5, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)},
    "Cinta 8":  {"x": 10.5, "y": 1.5, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5, "y": 1.5, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5, "y": 1.5, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    
    # Salida
    "Cinta 11": {"x": 23,   "y": 1.5, "w": 1.5, "h": 3.5, "color": "#FFD700", "next": [], "dir": (0,1)},
}

# --- 2. ESTADO INICIAL ---
if 'config_cintas' not in st.session_state:
    st.session_state.config_cintas = {}
    for nombre, props in layout_props.items():
        es_vertical = props['dir'] == (0, 1) or props['dir'] == (0, -1)
        largo_def = props['h'] if es_vertical else props['w']
        if nombre == "Cinta 7": largo_def = 8.0 
        
        st.session_state.config_cintas[nombre] = {
            "largo": largo_def,
            "velocidad": 1.5 
        }

# --- 3. PANEL DE CONTROL ---
st.sidebar.header("🎛️ Panel de Operación")

# --- A) CONTROL DE CADENCIA ---
st.sidebar.subheader("1. Cadencia de Producción")

# Input manual de Segundos
segundos_input = st.sidebar.number_input(
    "⏱️ Sale 1 bolsa cada (segundos):", 
    min_value=0.1, 
    max_value=60.0, 
    value=5.0,
    step=0.5
)

bolsas_por_hora = 3600 / segundos_input
st.sidebar.info(f"Esto equivale a: **{bolsas_por_hora:.0f} Bolsas/Hora**")

# --- B) VELOCIDADES MANUALES ---
st.sidebar.divider()
st.sidebar.subheader("2. Velocidades de Cintas")
cinta_sel = st.sidebar.selectbox("Seleccionar Cinta:", list(layout_props.keys()))
conf = st.session_state.config_cintas[cinta_sel]

c1, c2 = st.sidebar.columns(2)
nv = c1.number_input(f"Velocidad (m/s)", value=float(conf['velocidad']), step=0.1, min_value=0.1)
nl = c2.number_input(f"Largo (m)", value=float(conf['largo']), step=0.5, min_value=0.5)
st.session_state.config_cintas[cinta_sel].update({"velocidad": nv, "largo": nl})

duracion_sim = st.sidebar.slider("Duración de la prueba (seg)", 30, 200, 100)


# --- 4. SIMULACIÓN ---
def simular(layout, configs, intervalo, duracion=60, paso=0.1):
    frames = []
    bolsas = []
    llegadas = []
    t_acum = 0
    id_count = 0
    steps = int(duracion / paso)
    
    for _ in range(steps):
        t_acum += paso
        
        # --- GENERACIÓN ---
        if t_acum >= intervalo:
            t_acum = 0
            origen = "Cinta 1" if (id_count % 2 == 0) else "Cinta 2"
            p = layout[origen]
            
            start_x = p['x'] if p['dir'] == (1,0) else p['x'] + p['w']
            
            bolsas.append({
                'id': id_count, 'cinta': origen, 'dist': 0.0,
                'x': start_x, 'y': p['y'] + p['h']/2, 'estado': 'ok'
            })
            id_count += 1
            
        activos = []
        for b in bolsas:
            c_nom = b['cinta']
            c_props = layout[c_nom]
            c_conf = configs[c_nom]
            
            # Movimiento
            avance = c_conf['velocidad'] * paso
            b['dist'] += avance
            
            # Fin de cinta
            if b['dist'] >= c_conf['largo']:
                siguientes = c_props['next']
                if not siguientes:
                    llegadas.append(1)
                else:
                    nueva_nom = siguientes[0]
                    nueva_props = layout[nueva_nom]
                    
                    if c_props['dir'] == (1,0): fin_x = c_props['x'] + c_props['w']
                    elif c_props['dir'] == (-1,0): fin_x = c_props['x']
                    else: fin_x = c_props['x'] + c_props['w']/2 
                    
                    if nueva_props['dir'] == (1,0): offset = max(0.0, fin_x - nueva_props['x'])
                    else: offset = 0.0
                    
                    b['cinta'] = nueva_nom
                    b['dist'] = offset
                    
                    if nueva_props['dir'] == (1,0):
                        b['y'] = nueva_props['y'] + nueva_props['h']/2
                        b['x'] = nueva_props['x'] + offset
                    elif nueva_props['dir'] == (0,-1):
                        b['x'] = nueva_props['x'] + nueva_props['w']/2
                        b['y'] = nueva_props['y'] + nueva_props['h']
                    elif nueva_props['dir'] == (0,1):
                        b['x'] = nueva_props['x'] + nueva_props['w']/2
                        b['y'] = nueva_props['y']
                        
                    activos.append(b)
            else:
                d = b['dist']
                if c_props['dir'] == (1,0): b['x'] = c_props['x'] + d
                elif c_props['dir'] == (-1,0): b['x'] = (c_props['x'] + c_props['w']) - d
                elif c_props['dir'] == (0,-1): 
                    b['x'] = c_props['x'] + c_props['w']/2
                    b['y'] = (c_props['y'] + c_props['h']) - d
                elif c_props['dir'] == (0,1):
                    b['x'] = c_props['x'] + c_props['w']/2
                    b['y'] = c_props['y'] + d
                
                activos.append(b)

        # Colisiones - CORREGIDO AQUÍ
        for i in range(len(activos)):
            b1 = activos[i]
            b1['estado'] = 'ok'
            for j in range(i + 1, len(activos)):
                b2 = activos[j] # <--- ESTA LÍNEA FALTABA
                if b1['cinta'] == b2['cinta'] and abs(b1['dist'] - b2['dist']) < 0.8:
                    b1['estado'] = 'choque'
                    b2['estado'] = 'choque'
        
        bolsas = activos
        colors = ['red' if b['estado'] == 'choque' else 'blue' for b in bolsas]
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colors})
        
    return frames, llegadas

# Ejecutar
datos, salidas = simular(layout_props, st.session_state.config_cintas, segundos_input, duracion_sim)

# --- 5. VISUALIZACIÓN ---
col1, col2 = st.columns([3, 1])
with col1:
    fig = go.Figure()
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444"), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=k, showarrow=False, font=dict(size=10))
    
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers"))
    fig.frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=10))]) for f in datos]
    
    fig.update_layout(height=600, xaxis=dict(visible=False, range=[-1, 26]), yaxis=dict(visible=False, range=[0, 8], scaleanchor="x"),
                      updatemenus=[dict(type="buttons", buttons=[dict(label="▶️ PLAY", method="animate", args=[None, dict(frame=dict(duration=50, redraw=True))])])])
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Resultados")
    st.metric("Entrada Configurada", f"{segundos_input} seg/bolsa")
    st.metric("Proyección Horaria", f"{bolsas_por_hora:.0f} bolsas/h")
    
    if len(salidas) > 0:
        st.success(f"¡Salieron {len(salidas)} bolsas!")
    else:
        st.warning("Simulando...")
