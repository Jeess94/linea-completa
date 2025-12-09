import streamlit as st
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador de Flujo Corregido")
st.title("🏭 Simulador: Corrección de Flujo")
st.markdown("""
- **Cinta 1:** Izquierda $\\to$ Derecha.
- **Cinta 2:** Derecha $\\to$ Izquierda (Contraflujo).
- **Cintas 3 y 4:** Bajan a la línea principal.
- **Objetivo:** Que todo llegue a la Cinta 11.
""")

# --- 1. LAYOUT FÍSICO ---
# NOTA: Ajusté 'dir' de Cinta 2 a (-1, 0)
layout_props = {
    # Entradas
    "Cinta 1":  {"x": 0,    "y": 8, "w": 3, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},
    "Cinta 2":  {"x": 6,    "y": 8, "w": 3, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (-1,0)}, # <--- CAMBIO AQUÍ (Izquierda)
    
    # Transversales (Bajan)
    "Cinta 3":  {"x": 3.5,  "y": 4.5, "w": 1, "h": 3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 4":  {"x": 5.0,  "y": 4.5, "w": 1, "h": 3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    
    # Línea Principal
    "Cinta 7":  {"x": 2,    "y": 2, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)},
    "Cinta 8":  {"x": 10.5, "y": 2, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5, "y": 2, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5, "y": 2, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    "Cinta 11": {"x": 23,   "y": 2, "w": 1.5, "h": 3.5, "color": "#FFD700", "next": [], "dir": (0,1)},
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
            "velocidad": 1.0 # Velocidad base m/s
        }

# --- 3. PANEL DE CONTROL ---
st.sidebar.header("🎛️ Configuración")

# Control de Cadencia
st.sidebar.subheader("1. Entrada")
modo_input = st.sidebar.radio("Controlar por:", ["Tiempo (seg)", "Separación (m)"], horizontal=True)
vel_c1 = st.session_state.config_cintas["Cinta 1"]["velocidad"]

if modo_input == "Tiempo (seg)":
    val_tiempo = st.sidebar.number_input("⏱️ Bolsa cada (seg):", 3.0, step=0.5)
    intervalo_real = val_tiempo
else:
    val_dist = st.sidebar.number_input("📏 Separación (m):", 2.0, step=0.5)
    intervalo_real = (val_dist / vel_c1) / 2 if vel_c1 > 0 else 999

# Control de Velocidades
st.sidebar.divider()
st.sidebar.subheader("2. Velocidades Individuales")
cinta_sel = st.sidebar.selectbox("Editar Cinta:", list(layout_props.keys()))
conf = st.session_state.config_cintas[cinta_sel]

c1, c2 = st.sidebar.columns(2)
n_vel = c1.number_input(f"Vel. {cinta_sel} (m/s)", value=float(conf['velocidad']), step=0.1)
n_lar = c2.number_input(f"Largo {cinta_sel} (m)", value=float(conf['largo']), step=0.5)

st.session_state.config_cintas[cinta_sel].update({"velocidad": n_vel, "largo": n_lar})

# --- 4. SIMULACIÓN (LÓGICA CORREGIDA) ---
def simular(layout, configs, intervalo, duracion=40, paso=0.1):
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
            # Alternar orígenes
            origen = "Cinta 1" if (id_count % 2 == 0) else "Cinta 2"
            p = layout[origen]
            
            # POSICIÓN INICIAL SEGÚN DIRECCIÓN
            if p['dir'] == (-1, 0): 
                # Si va hacia la izquierda (Cinta 2), nace en el borde derecho
                start_x = p['x'] + p['w']
            else:
                # Si va hacia la derecha (Cinta 1), nace en el borde izquierdo
                start_x = p['x']
                
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
            
            # --- MOVIMIENTO FÍSICO ---
            avance = c_conf['velocidad'] * paso
            b['dist'] += avance
            
            # --- TRANSFERENCIA (CAMBIO DE CINTA) ---
            if b['dist'] >= c_conf['largo']:
                # Llegó al final de su cinta actual
                siguientes = c_props['next']
                
                if not siguientes:
                    # Final de línea (Cinta 11) -> Contabilizar salida
                    llegadas.append(1)
                else:
                    nueva_nom = siguientes[0]
                    nueva_props = layout[nueva_nom]
                    
                    # 1. ¿EN QUÉ COORDENADA X/Y TERMINÓ LA CINTA ANTERIOR?
                    if c_props['dir'] == (1, 0):      # Terminó yendo a derecha
                        fin_x = c_props['x'] + c_props['w']
                    elif c_props['dir'] == (-1, 0):   # Terminó yendo a izquierda (Cinta 2)
                        fin_x = c_props['x'] # El final es el inicio X (izquierda)
                    elif c_props['dir'] == (0, -1):   # Terminó bajando (C3, C4)
                        # Cae en el centro X de la cinta vertical
                        fin_x = c_props['x'] + (c_props['w']/2)
                    else: 
                        fin_x = c_props['x'] + c_props['w']

                    # 2. CALCULAR OFFSET (¿En qué metro de la nueva cinta cae?)
                    # Esto evita que vuelvan al inicio si caen a mitad de camino
                    if nueva_props['dir'] == (1, 0): # Entrando a una horizontal (ej: C7)
                        offset = max(0.0, fin_x - nueva_props['x'])
                    else:
                        offset = 0.0 # Entrando a una vertical, empieza arriba (0)
                    
                    # Actualizar datos de la bolsa
                    b['cinta'] = nueva_nom
                    b['dist'] = offset
                    
                    # 3. ACTUALIZAR VISUALIZACIÓN INSTANTÁNEA (TELETRANSPORTE VISUAL)
                    if nueva_props['dir'] == (1,0): # Horizontal
                        b['y'] = nueva_props['y'] + nueva_props['h']/2
                        b['x'] = nueva_props['x'] + offset
                    elif nueva_props['dir'] == (0,-1): # Vertical Bajada
                         b['x'] = nueva_props['x'] + nueva_props['w']/2
                         b['y'] = nueva_props['y'] + nueva_props['h'] 
                    elif nueva_props['dir'] == (0,1): # Vertical Subida
                         b['x'] = nueva_props['x'] + nueva_props['w']/2
                         b['y'] = nueva_props['y']
                    
                    activos.append(b)
            else:
                # --- MOVIMIENTO VISUAL CONTINUO ---
                dist = b['dist']
                
                if c_props['dir'] == (1, 0):   # Derecha
                    b['x'] = c_props['x'] + dist
                    b['y'] = c_props['y'] + c_props['h']/2
                    
                elif c_props['dir'] == (-1, 0): # Izquierda (Cinta 2)
                    # Nace a la derecha y se resta distancia
                    b['x'] = (c_props['x'] + c_props['w']) - dist
                    b['y'] = c_props['y'] + c_props['h']/2
                    
                elif c_props['dir'] == (0, -1): # Abajo
                    b['x'] = c_props['x'] + c_props['w']/2
                    b['y'] = (c_props['y'] + c_props['h']) - dist
                    
                elif c_props['dir'] == (0, 1):  # Arriba
                    b['x'] = c_props['x'] + c_props['w']/2
                    b['y'] = c_props['y'] + dist
                    
                activos.append(b)

        # Detección de colisiones visuales
        for i in range(len(activos)):
            b1 = activos[i]
            b1['estado'] = 'ok'
            for j in range(i + 1, len(activos)):
                b2 = activos[j]
                if b1['cinta'] == b2['cinta'] and abs(b1['dist'] - b2['dist']) < 0.8:
                    b1['estado'] = 'choque'
                    b2['estado'] = 'choque'

        bolsas = activos
        colores = ['red' if b['estado'] == 'choque' else 'blue' for b in bolsas]
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colores})
        
    return frames, llegadas, intervalo

# Ejecutar
datos, salidas, interv = simular(layout_props, st.session_state.config_cintas, intervalo_real)

# --- 5. VISUALIZACIÓN ---
c_graf, c_dato = st.columns([3, 1])

with c_graf:
    fig = go.Figure()
    # Dibujar Layout
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444"), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=k, showarrow=False, font=dict(size=10))

    fig.add_trace(go.Scatter(x=[], y=[], mode="markers"))
    
    ply_frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=10))]) for f in datos]
    fig.frames = ply_frames
    
    fig.update_layout(height=550, xaxis=dict(visible=False, range=[-1, 26]), yaxis=dict(visible=False, range=[0, 10], scaleanchor="x"),
                      updatemenus=[dict(type="buttons", buttons=[dict(label="▶️ PLAY", method="animate", args=[None, dict(frame=dict(duration=50, redraw=True))])])])
    st.plotly_chart(fig, use_container_width=True)

with c_dato:
    st.subheader("Resultados")
    # Cálculo proyecciones
    teorico = 3600 / interv if interv > 0 else 0
    
    # Salida Real (aproximate based on simulation length)
    # Simple projection: (bolsas salidas / tiempo total simulado) * 3600
    # Nota: esto es aproximado porque la simulación dura poco
    rate_real = teorico # Asumimos flujo ideal para mostrar dato rápido, ajustar si hay choques
    
    st.metric("Entrada (b/h)", f"{teorico:.0f}")
    
    if len(salidas) == 0:
        st.warning("Aún no salen bolsas (Dale Play o espera)")
    else:
        st.success("¡Flujo llegando al final!")
    
    st.markdown("---")
    st.caption("Verifica visualmente si los puntos rojos aparecen (choques).")
