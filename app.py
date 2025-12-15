import streamlit as st
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Sintonizador Pro")
st.title("🎛️ Sintonizador de Flujo con Geometría Dinámica")
st.markdown("Define **Cadencia** (Input) y ajusta **Velocidades/Largos** para ver si logras el objetivo sin choques.")

# --- 1. CONFIGURACIÓN INICIAL (Valores por defecto) ---
if 'config_cintas' not in st.session_state:
    st.session_state.config_cintas = {
        # Entradas
        "Cinta 1": {"largo": 3.5, "velocidad": 1.5},
        "Cinta 2": {"largo": 3.5, "velocidad": 1.5},
        # Bajadas
        "Cinta 3": {"largo": 3.5, "velocidad": 1.5},
        "Cinta 4": {"largo": 3.5, "velocidad": 1.5},
        # Línea Principal
        "Cinta 7":  {"largo": 8.0, "velocidad": 1.5},
        "Cinta 8":  {"largo": 1.5, "velocidad": 1.5},
        "Cinta 9":  {"largo": 1.5, "velocidad": 1.5},
        "Cinta 10": {"largo": 8.0, "velocidad": 1.5},
        # Salida
        "Cinta 11": {"largo": 3.5, "velocidad": 1.5},
    }

# --- 2. MOTOR DE GEOMETRÍA (Cálculo de Coordenadas en Vivo) ---
def calcular_layout_dinamico(configs):
    layout = {}
    
    # --- NIVEL SUPERIOR ---
    l3 = configs["Cinta 3"]["largo"]
    l4 = configs["Cinta 4"]["largo"]
    altura_max_bajada = max(l3, l4)
    y_base = 1.5 
    y_superior = y_base + altura_max_bajada + 0.5 
    
    # Cinta 1 (Izquierda)
    l1 = configs["Cinta 1"]["largo"]
    layout["Cinta 1"] = {"x": 0, "y": y_superior, "w": l1, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)}
    
    # Cinta 3 (Bajada 1)
    layout["Cinta 3"] = {"x": l1, "y": y_superior - l3, "w": 1, "h": l3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)}
    
    separacion_bajadas = 2.0 
    
    # Cinta 4 (Bajada 2)
    pos_x_c4 = l1 + 1 + separacion_bajadas
    layout["Cinta 4"] = {"x": pos_x_c4, "y": y_superior - l4, "w": 1, "h": l4, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)}
    
    # Cinta 2 (Derecha)
    l2 = configs["Cinta 2"]["largo"]
    layout["Cinta 2"] = {"x": pos_x_c4 + 1, "y": y_superior, "w": l2, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (-1,0)}
    
    # --- NIVEL INFERIOR ---
    inicio_c7 = l1 - 1.5
    if inicio_c7 < 0: inicio_c7 = 0 
    
    l7 = configs["Cinta 7"]["largo"]
    layout["Cinta 7"] = {"x": inicio_c7, "y": y_base, "w": l7, "h": 1.5, "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)}
    
    cursor_x = inicio_c7 + l7 
    
    # Cintas intermedias
    for nombre in ["Cinta 8", "Cinta 9", "Cinta 10"]:
        l = configs[nombre]["largo"]
        sig = "Cinta 9" if nombre == "Cinta 8" else "Cinta 10" if nombre == "Cinta 9" else "Cinta 11"
        layout[nombre] = {"x": cursor_x, "y": y_base, "w": l, "h": 1.5, "color": "#FFD700", "next": [sig], "dir": (1,0)}
        cursor_x += l
    
    # Cinta 11 (Salida)
    l11 = configs["Cinta 11"]["largo"]
    layout["Cinta 11"] = {"x": cursor_x, "y": y_base, "w": 1.5, "h": l11, "color": "#FFD700", "next": [], "dir": (0,1)}
    
    return layout

# --- 3. PANEL DE CONTROL ---
st.sidebar.header("🎛️ Panel de Control")

# A) RITMO
st.sidebar.subheader("1. Ritmo de Entrada")
segundos_input = st.sidebar.number_input(
    "⏱️ Segundos entre bolsas:", 
    min_value=0.5, max_value=20.0, value=5.0, step=0.5
)
bolsas_hora_teorico = 3600 / segundos_input
st.sidebar.info(f"Ritmo teórico: **{bolsas_hora_teorico:.0f} bolsas/hora**")

# B) CONFIGURACIÓN
st.sidebar.divider()
st.sidebar.subheader("2. Configuración de Cintas")

cinta_sel = st.sidebar.selectbox("Seleccionar Cinta:", list(st.session_state.config_cintas.keys()))
conf = st.session_state.config_cintas[cinta_sel]

c1, c2 = st.sidebar.columns(2)
nv = c1.number_input(f"Velocidad {cinta_sel} (m/s)", value=float(conf['velocidad']), step=0.1, min_value=0.1)
nl = c2.number_input(f"Largo {cinta_sel} (m)", value=float(conf['largo']), step=0.5, min_value=1.0)

st.session_state.config_cintas[cinta_sel].update({"velocidad": nv, "largo": nl})

duracion_sim = st.sidebar.slider("Duración Prueba (seg)", 30, 300, 100)

# CÁLCULO DINÁMICO DEL LAYOUT
layout_props = calcular_layout_dinamico(st.session_state.config_cintas)

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
        
        # Generación
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
            
            avance = c_conf['velocidad'] * paso
            b['dist'] += avance
            
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

        # Colisiones
        num_activos = len(activos)
        for i in range(num_activos):
            b1 = activos[i]
            b1['estado'] = 'ok'
            for j in range(i + 1, num_activos):
                b2 = activos[j]
                if b1['cinta'] == b2['cinta'] and abs(b1['dist'] - b2['dist']) < 0.8:
                    b1['estado'] = 'choque'
                    b2['estado'] = 'choque'
        
        bolsas = activos
        colors = ['#FF0000' if b['estado'] == 'choque' else '#0000FF' for b in bolsas]
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colors})
        
    return frames, llegadas

datos, salidas = simular(layout_props, st.session_state.config_cintas, segundos_input, duracion_sim)

# --- 5. VISUALIZACIÓN ---
col1, col2 = st.columns([3, 1])

with col1:
    fig = go.Figure()
    
    # Límites dinámicos
    max_x = 0
    max_y = 0
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444"), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=k, showarrow=False, font=dict(size=10))
        max_x = max(max_x, v['x'] + v['w'])
        max_y = max(max_y, v['y'] + v['h'])

    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="Bolsas"))
    fig.frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=12))]) for f in datos]
    
    fig.update_layout(
        height=600, 
        xaxis=dict(visible=False, range=[-1, max_x + 2], fixedrange=False), 
        yaxis=dict(visible=False, range=[0, max_y + 2], scaleanchor="x", scaleratio=1),
        plot_bgcolor="#eff2f6",
        margin=dict(l=10, r=10, t=10, b=10),
        updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=0.95,
            buttons=[dict(label="▶️ PLAY", method="animate", 
                          args=[None, dict(frame=dict(duration=40, redraw=True), fromcurrent=True)])])]
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 Resultados de Salida")
    
    if len(salidas) > 0:
        salida_real_hora = (len(salidas) / duracion_sim) * 3600
        # Tope físico: No puede salir más de lo que entra
        salida_real_hora = min(salida_real_hora, bolsas_hora_teorico * 1.05)
        
        st.metric("Bolsas / Hora (Real)", f"{salida_real_hora:.0f} b/h", delta=f"{salida_real_hora - 600:.0f} vs Objetivo 600")
        
        hubo_choques = any('red' in str(f['c']) for f in datos)
        
        st.divider()
        if hubo_choques:
            st.error("🚨 **COLISIÓN DETECTADA**\n\nAumenta la velocidad de las cintas.")
        elif salida_real_hora >= 590:
            st.success("✅ **OBJETIVO CUMPLIDO**")
        else:
            st.warning("⚠️ **BAJA PRODUCCIÓN**\n\nAumenta la entrada (baja los segundos).")
    else:
        st.info("Dale Play para simular.")
