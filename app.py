import streamlit as st
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador de Flujo Final")
st.title("🏭 Simulador de Línea: Flujo Corregido")
st.markdown("Visualización del recorrido completo: **C1/C2 $\\to$ Bajada $\\to$ Cinta 7 $\\to$ Final**.")

# --- 1. LAYOUT FÍSICO (Geometría Ajustada para Conexión Visual) ---
layout_props = {
    # NIVEL SUPERIOR (Y=6)
    # Cinta 1 va hacia la derecha ->
    "Cinta 1":  {"x": 0,    "y": 6, "w": 3.5, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},
    # Cinta 2 va hacia la izquierda <-
    "Cinta 2":  {"x": 6.5,  "y": 6, "w": 3.5, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (-1,0)},
    
    # TRANSVERSALES (BAJAN de Y=6 a Y=1.5)
    # Se superponen visualmente para dar efecto de caída sobre la C7
    "Cinta 3":  {"x": 3.5,  "y": 2.5, "w": 1, "h": 3.5, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 4":  {"x": 5.5,  "y": 2.5, "w": 1, "h": 3.5, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    
    # NIVEL INFERIOR (Y=1.5) - Recolectora
    "Cinta 7":  {"x": 2,    "y": 1.5, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)},
    "Cinta 8":  {"x": 10.5, "y": 1.5, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5, "y": 1.5, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5, "y": 1.5, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    
    # SALIDA
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
st.sidebar.header("🎛️ Operación")

# --- A) CADENCIA ---
st.sidebar.subheader("1. Producción")
segundos_input = st.sidebar.number_input(
    "⏱️ Intervalo entre bolsas (segundos):", 
    min_value=0.1, max_value=60.0, value=5.0, step=0.5
)
st.sidebar.caption(f"Salida teórica: {3600/segundos_input:.0f} bolsas/hora")

# --- B) VELOCIDADES ---
st.sidebar.divider()
st.sidebar.subheader("2. Velocidades")
cinta_sel = st.sidebar.selectbox("Seleccionar Cinta:", list(layout_props.keys()))
conf = st.session_state.config_cintas[cinta_sel]

c1, c2 = st.sidebar.columns(2)
nv = c1.number_input(f"Velocidad (m/s)", value=float(conf['velocidad']), step=0.1, min_value=0.1)
nl = c2.number_input(f"Largo (m)", value=float(conf['largo']), step=0.5, min_value=0.5)
st.session_state.config_cintas[cinta_sel].update({"velocidad": nv, "largo": nl})

duracion_sim = st.sidebar.slider("Duración Simulación (seg)", 30, 200, 90)

# --- 4. MOTOR DE SIMULACIÓN ---
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
            # Inicio visual: C1 izquierda, C2 derecha
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
            
            # --- MOVIMIENTO LÓGICO ---
            avance = c_conf['velocidad'] * paso
            b['dist'] += avance
            
            # --- CAMBIO DE CINTA ---
            if b['dist'] >= c_conf['largo']:
                siguientes = c_props['next']
                
                if not siguientes:
                    llegadas.append(1) # Llegó al final (C11)
                else:
                    nueva_nom = siguientes[0]
                    nueva_props = layout[nueva_nom]
                    
                    # 1. Calcular coordenada X absoluta donde termina la cinta actual
                    if c_props['dir'] == (1,0): fin_x = c_props['x'] + c_props['w']
                    elif c_props['dir'] == (-1,0): fin_x = c_props['x']
                    else: fin_x = c_props['x'] + c_props['w']/2 # Vertical cae en su centro X
                    
                    # 2. Calcular 'dist' inicial en la nueva cinta (Offset)
                    if nueva_props['dir'] == (1,0): 
                        # Si cae en C7, el offset es la distancia desde el inicio de C7 hasta el punto de caída
                        offset = max(0.0, fin_x - nueva_props['x'])
                    else: 
                        offset = 0.0
                    
                    b['cinta'] = nueva_nom
                    b['dist'] = offset
                    
                    # 3. Actualizar Coordenadas Visuales Inmediatas (Evitar saltos raros)
                    if nueva_props['dir'] == (1,0): # Cae a Horizontal
                        b['y'] = nueva_props['y'] + nueva_props['h']/2
                        b['x'] = nueva_props['x'] + offset
                    elif nueva_props['dir'] == (0,-1): # Entra a Bajada
                        b['x'] = nueva_props['x'] + nueva_props['w']/2
                        b['y'] = nueva_props['y'] + nueva_props['h']
                    elif nueva_props['dir'] == (0,1): # Entra a Subida
                        b['x'] = nueva_props['x'] + nueva_props['w']/2
                        b['y'] = nueva_props['y']
                        
                    activos.append(b)
            else:
                # --- MOVIMIENTO VISUAL ---
                d = b['dist']
                if c_props['dir'] == (1,0): # Derecha
                    b['x'] = c_props['x'] + d
                    b['y'] = c_props['y'] + c_props['h']/2
                elif c_props['dir'] == (-1,0): # Izquierda (C2)
                    b['x'] = (c_props['x'] + c_props['w']) - d
                    b['y'] = c_props['y'] + c_props['h']/2
                elif c_props['dir'] == (0,-1): # Bajando (C3, C4)
                    b['x'] = c_props['x'] + c_props['w']/2
                    b['y'] = (c_props['y'] + c_props['h']) - d
                elif c_props['dir'] == (0,1): # Subiendo (C11)
                    b['x'] = c_props['x'] + c_props['w']/2
                    b['y'] = c_props['y'] + d
                
                activos.append(b)

        # --- DETECCIÓN DE COLISIONES (CORREGIDA) ---
        num_activos = len(activos)
        for i in range(num_activos):
            b1 = activos[i]
            b1['estado'] = 'ok'
            for j in range(i + 1, num_activos):
                b2 = activos[j] # <--- VARIABLE b2 DEFINIDA CORRECTAMENTE
                
                # Solo chocan si están en la misma cinta
                if b1['cinta'] == b2['cinta']:
                    distancia = abs(b1['dist'] - b2['dist'])
                    if distancia < 0.8: # Umbral de choque (metros)
                        b1['estado'] = 'choque'
                        b2['estado'] = 'choque'
        
        bolsas = activos
        colors = ['#FF0000' if b['estado'] == 'choque' else '#0000FF' for b in bolsas]
        # Puntos un poco más grandes para ver mejor
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colors})
        
    return frames, llegadas

# Ejecutar
datos, salidas = simular(layout_props, st.session_state.config_cintas, segundos_input, duracion_sim)

# --- 5. VISUALIZACIÓN ---
col1, col2 = st.columns([3, 1])
with col1:
    fig = go.Figure()
    # Dibujar Cintas (Fondo)
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444"), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=k, showarrow=False, font=dict(size=10))
    
    # Capa de Bolsas
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="Bolsas"))
    
    # Animación
    fig.frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=12))]) for f in datos]
    
    fig.update_layout(
        height=600, 
        xaxis=dict(visible=False, range=[-1, 26], fixedrange=True), 
        yaxis=dict(visible=False, range=[0, 8], scaleanchor="x", scaleratio=1, fixedrange=True),
        plot_bgcolor="#eff2f6",
        margin=dict(l=10, r=10, t=10, b=10),
        updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=0.95,
            buttons=[dict(label="▶️ PLAY", method="animate", 
                          args=[None, dict(frame=dict(duration=40, redraw=True), fromcurrent=True)])])]
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Resultados")
    rate_h = 3600 / segundos_input
    st.metric("Entrada Configurada", f"{rate_h:.0f} bolsas/h")
    
    st.divider()
    if len(salidas) > 0:
        st.success(f"✅ **Salida Exitosa:**\n\n{len(salidas)} bolsas completaron el recorrido.")
    else:
        st.info("⏳ Simulando recorrido...")
        st.caption("Si tardan mucho en llegar, aumenta la 'Duración Simulación'.")
