import streamlit as st
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Calculadora de Throughput")
st.title("🏭 Calculadora de Capacidad Real (Bolsas/Hora)")
st.markdown("Define la **separación** o el **tiempo** entre bolsas y verifica si logras el objetivo de **600 bolsas/hora** al final de la línea.")

# --- 1. LAYOUT FÍSICO ---
layout_props = {
    "Cinta 1":  {"x": 0,    "y": 8, "w": 3, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},
    "Cinta 2":  {"x": 6,    "y": 8, "w": 3, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (1,0)},
    "Cinta 3":  {"x": 3.5,  "y": 4.5, "w": 1, "h": 3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 4":  {"x": 5.0,  "y": 4.5, "w": 1, "h": 3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 7":  {"x": 2,    "y": 2, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)},
    "Cinta 8":  {"x": 10.5, "y": 2, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5, "y": 2, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5, "y": 2, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    "Cinta 11": {"x": 23,   "y": 2, "w": 1.5, "h": 3.5, "color": "#FFD700", "next": [], "dir": (0,1)}, # Salida
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
            "velocidad": 0.5 # Velocidad inicial tranquila
        }

# --- 3. PANEL DE CONTROL ---
st.sidebar.header("🎛️ Control de Entrada")

# --- A) CONTROL DE SEPARACIÓN / TIEMPO ---
st.sidebar.subheader("1. Definir Entrada")
modo_control = st.sidebar.radio("Controlar por:", ["Tiempo (segundos)", "Separación (metros)"], horizontal=True)

# Recuperamos velocidad de entrada (Cinta 1) para los cálculos
vel_entrada = st.session_state.config_cintas["Cinta 1"]["velocidad"]

if modo_control == "Tiempo (segundos)":
    input_seg = st.sidebar.number_input("⏱️ Una bolsa cada (seg):", value=5.0, step=0.5)
    # Cálculo derivado
    distancia_calc = input_seg * vel_entrada * 2 # x2 porque alternamos cintas
    input_distancia = distancia_calc # Solo referencial
    intervalo_real = input_seg
    st.sidebar.caption(f"Con vel. de {vel_entrada} m/s, esto genera una separación de **{distancia_calc:.2f} m** en cada cinta.")

else:
    input_distancia = st.sidebar.number_input("📏 Separación entre bolsas (m):", value=2.0, step=0.5)
    # Cálculo derivado: t = d / v
    if vel_entrada > 0:
        # La separación en UNA cinta es resultado de alternar. 
        # Si quiero X metros en Cinta 1, el sistema debe inyectar a un ritmo acorde.
        # Intervalo sistema = (Distancia / Vel) / 2 (porque son 2 cintas)
        tiempo_calc = (input_distancia / vel_entrada) / 2
    else:
        tiempo_calc = 9999
    intervalo_real = tiempo_calc
    st.sidebar.caption(f"Para lograr {input_distancia}m de hueco, entran bolsas al sistema cada **{tiempo_calc:.2f} seg**.")

# --- B) VELOCIDADES MANUALES ---
st.sidebar.divider()
st.sidebar.subheader("2. Velocidades Manuales")
cinta_sel = st.sidebar.selectbox("Configurar Cinta:", list(layout_props.keys()))
conf = st.session_state.config_cintas[cinta_sel]

col1, col2 = st.sidebar.columns(2)
n_vel = col1.number_input(f"Vel. {cinta_sel} (m/s)", value=float(conf['velocidad']), step=0.1)
n_largo = col2.number_input(f"Largo {cinta_sel} (m)", value=float(conf['largo']), step=0.5)

st.session_state.config_cintas[cinta_sel].update({"velocidad": n_vel, "largo": n_largo})


# --- 4. SIMULACIÓN ---
def simular(layout, configs, intervalo, duracion=60, paso=0.1):
    frames = []
    bolsas = []
    llegadas = [] 
    t_acum = 0
    id_count = 0
    steps = int(duracion / paso)
    
    for _ in range(steps):
        t_now = _ * paso
        t_acum += paso
        
        # Generar
        if t_acum >= intervalo:
            t_acum = 0
            origen = "Cinta 1" if (id_count % 2 == 0) else "Cinta 2"
            p = layout[origen]
            bolsas.append({
                'id': id_count, 'cinta': origen, 'dist': 0.0,
                'x': p['x'], 'y': p['y'] + p['h']/2, 'estado': 'ok'
            })
            id_count += 1
            
        activos = []
        for b in bolsas:
            c_nom = b['cinta']
            c_props = layout[c_nom]
            c_conf = configs[c_nom]
            
            # Mover
            avance = c_conf['velocidad'] * paso
            b['dist'] += avance
            
            # Fin de cinta
            if b['dist'] >= c_conf['largo']:
                nexts = c_props['next']
                if not nexts:
                    llegadas.append(t_now) # SALIDA EXITOSA
                else:
                    new_nom = nexts[0]
                    new_props = layout[new_nom]
                    
                    # Offset
                    if c_props['dir'] == (0, -1): fin_x = c_props['x'] + (c_props['w']/2)
                    else: fin_x = c_props['x'] + c_props['w']
                    
                    if new_props['dir'] == (1, 0): offset = max(0.0, fin_x - new_props['x'])
                    else: offset = 0.0
                    
                    b['cinta'] = new_nom
                    b['dist'] = offset
                    
                    # Pos visual
                    if new_props['dir'] == (1,0): 
                        b['y'] = new_props['y'] + new_props['h']/2
                        b['x'] = new_props['x'] + offset
                    elif new_props['dir'] == (0,-1): 
                         b['x'] = new_props['x'] + new_props['w']/2
                         b['y'] = new_props['y'] + new_props['h']
                    elif new_props['dir'] == (0,1): 
                         b['x'] = new_props['x'] + new_props['w']/2
                         b['y'] = new_props['y']
                    
                    activos.append(b)
            else:
                # Visual update
                if c_props['dir'] == (1, 0): 
                    b['x'] = c_props['x'] + b['dist']
                    b['y'] = c_props['y'] + c_props['h']/2
                elif c_props['dir'] == (0, -1): 
                    b['x'] = c_props['x'] + c_props['w']/2
                    b['y'] = (c_props['y'] + c_props['h']) - b['dist']
                elif c_props['dir'] == (0, 1): 
                    b['x'] = c_props['x'] + c_props['w']/2
                    b['y'] = c_props['y'] + b['dist']
                activos.append(b)
        
        # Colisiones
        for i in range(len(activos)):
            b1 = activos[i]
            b1['estado'] = 'ok'
            for j in range(i + 1, len(activos)):
                b2 = activos[j]
                if b1['cinta'] == b2['cinta'] and abs(b1['dist'] - b2['dist']) < 0.8: # 0.8m distancia min
                    b1['estado'] = 'choque'
                    b2['estado'] = 'choque'

        bolsas = activos
        colors = ['red' if b['estado'] == 'choque' else '#0033cc' for b in bolsas]
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colors})
        
    return frames, llegadas, intervalo_real

# Ejecutar
datos, salidas, intervalo_simulado = simular(layout_props, st.session_state.config_cintas, intervalo_real)

# --- 5. RESULTADOS ---
col_graph, col_kpi = st.columns([3, 1])

with col_graph:
    fig = go.Figure()
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#333"), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=k, showarrow=False)

    fig.add_trace(go.Scatter(x=[], y=[], mode="markers"))
    
    ply_frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=10))]) for f in datos]
    fig.frames = ply_frames
    
    fig.update_layout(height=550, xaxis=dict(visible=False, range=[-1, 26]), yaxis=dict(visible=False, range=[0, 10], scaleanchor="x"),
                      updatemenus=[dict(type="buttons", buttons=[dict(label="▶️ PLAY", method="animate", args=[None, dict(frame=dict(duration=50, redraw=True))])])])
    st.plotly_chart(fig, use_container_width=True)

with col_kpi:
    st.subheader("📊 Resultados Finales")
    
    # 1. Cálculo de Entrada Teórica
    if intervalo_simulado > 0:
        teorico_hora = 3600 / intervalo_simulado
    else:
        teorico_hora = 0
    
    st.markdown("### Entrada")
    st.metric("Bolsas lanzadas (Teórico)", f"{teorico_hora:.0f} / h", delta="Input")

    # 2. Cálculo de Salida Real
    if len(salidas) > 1:
        # Tiempo entre la primera que salió y la última que salió
        tiempo_flujo = salidas[-1] - salidas[0]
        if tiempo_flujo > 0:
            rate_real = (len(salidas) / tiempo_flujo) * 3600
        else:
            rate_real = 0
    else:
        rate_real = 0
        
    st.markdown("### Salida Real")
    # Colorear según el objetivo de 600
    color_delta = "normal"
    if rate_real < 580: color_delta = "off" # Rojo/Gris
    elif rate_real > 620: color_delta = "inverse" # Alto
    
    st.metric("Llegan al final (Real)", f"{rate_real:.0f} / h", delta=f"{rate_real - 600:.0f} vs Target 600")
    
    st.divider()
    if rate_real < teorico_hora * 0.9:
        st.error(f"⚠️ **Pérdida de Eficiencia**: Estás metiendo {teorico_hora:.0f} pero solo salen {rate_real:.0f}. \n\n¡Hay bolsas chocando o acumulándose! Revisa si las cintas están muy lentas.")
    elif rate_real >= 600:
        st.success("✅ **Objetivo Cumplido**: La línea soporta el caudal de 600 bolsas/hora.")
    else:
        st.warning("⚠️ **No llegas**: Aumenta la cadencia de entrada.")
