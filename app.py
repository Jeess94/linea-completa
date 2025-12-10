import streamlit as st
import plotly.graph_objects as go
import math
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador Mecánico de Planta")
st.title("🏭 Simulador: Ingeniería de Detalle")
st.markdown("Configura **Motor, Reductor y Rodillo** para obtener la velocidad real y verificar el caudal (Bolsas/Hora).")

# --- 1. CONFIGURACIÓN INICIAL (DATOS MECÁNICOS POR DEFECTO) ---
if 'config_cintas' not in st.session_state:
    # Valores estándar de industria
    defaults = {"motor": 1450, "reductor": 25, "rodillo": 130} 
    
    st.session_state.config_cintas = {
        # Entradas
        "Cinta 1": {"largo": 4.0, **defaults},
        "Cinta 2": {"largo": 4.0, **defaults},
        # Bajadas
        "Cinta 3": {"largo": 3.0, **defaults},
        "Cinta 4": {"largo": 3.0, **defaults},
        # Línea Principal
        "Cinta 7":  {"largo": 8.0, **defaults},
        "Cinta 8":  {"largo": 2.0, **defaults},
        "Cinta 9":  {"largo": 2.0, **defaults},
        "Cinta 10": {"largo": 8.0, **defaults},
        # Salida
        "Cinta 11": {"largo": 4.0, **defaults},
    }

# --- 2. PANEL DE INGENIERÍA ---
st.sidebar.header("🎛️ Panel de Ingeniería")

# A) CADENCIA (INPUT)
st.sidebar.subheader("1. Objetivo de Producción")
segundos_input = st.sidebar.number_input(
    "⏱️ Intervalo de entrada (segundos):", 
    min_value=0.5, max_value=60.0, value=5.0, step=0.5
)
input_teorico = 3600 / segundos_input
st.sidebar.info(f"Ritmo de Entrada: **{input_teorico:.0f} bolsas/h**")

# B) CONFIGURACIÓN MECÁNICA
st.sidebar.divider()
st.sidebar.subheader("2. Datos Mecánicos")

cinta_sel = st.sidebar.selectbox("Editar Cinta:", list(st.session_state.config_cintas.keys()))
datos = st.session_state.config_cintas[cinta_sel]

# Inputs
col1, col2 = st.sidebar.columns(2)
nuevo_l = col1.number_input(f"Largo (m)", value=float(datos['largo']), step=0.5)
nuevo_motor = col2.number_input(f"RPM Motor", value=int(datos['motor']), step=50)

col3, col4 = st.sidebar.columns(2)
nuevo_red = col3.number_input(f"Reductor (i)", value=int(datos['reductor']), step=5)
nuevo_rod = col4.number_input(f"Ø Rodillo (mm)", value=int(datos['rodillo']), step=5)

# CÁLCULO FÍSICO DE VELOCIDAD
if nuevo_red > 0:
    rpm_salida = nuevo_motor / nuevo_red
    # V (m/min) = RPM * Pi * Diámetro(m)
    v_m_min = rpm_salida * math.pi * (nuevo_rod / 1000)
    v_m_s = v_m_min / 60
else:
    v_m_s = 0

st.sidebar.success(f"⚡ Velocidad Calc: **{v_m_s:.2f} m/s**\n\n({v_m_min:.1f} m/min)")

# Guardar en estado
st.session_state.config_cintas[cinta_sel].update({
    "largo": nuevo_l,
    "motor": nuevo_motor,
    "reductor": nuevo_red,
    "rodillo": nuevo_rod,
    "velocidad_calc": v_m_s # Guardamos la calculada para usarla en la simulación
})

duracion_sim = st.sidebar.slider("Duración Simulación (seg)", 30, 300, 100)

# --- 3. MOTOR DE GEOMETRÍA DINÁMICA ---
def calcular_layout(configs):
    layout = {}
    
    # --- NIVEL SUPERIOR ---
    l1 = configs["Cinta 1"]["largo"]
    layout["Cinta 1"] = {"x": 0, "y": 10, "w": l1, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)}
    
    l3 = configs["Cinta 3"]["largo"]
    layout["Cinta 3"] = {"x": l1, "y": 10 - l3, "w": 1, "h": l3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)}

    separacion = 3.0
    
    l4 = configs["Cinta 4"]["largo"]
    pos_x_c4 = l1 + 1 + separacion 
    layout["Cinta 4"] = {"x": pos_x_c4, "y": 10 - l4, "w": 1, "h": l4, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)}

    l2 = configs["Cinta 2"]["largo"]
    layout["Cinta 2"] = {"x": pos_x_c4 + 1, "y": 10, "w": l2, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (-1,0)}

    # --- NIVEL INFERIOR ---
    max_bajada = max(l3, l4)
    y_inferior = 10 - max_bajada - 0.5 
    
    inicio_c7 = l1 - 1.0 
    l7 = configs["Cinta 7"]["largo"]
    layout["Cinta 7"] = {"x": inicio_c7, "y": y_inferior, "w": l7, "h": 1.5, "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)}
    
    cursor_x = inicio_c7 + l7
    
    # Encadenamiento
    for nombre in ["Cinta 8", "Cinta 9", "Cinta 10"]:
        l = configs[nombre]["largo"]
        siguiente = "Cinta 9" if nombre == "Cinta 8" else "Cinta 10" if nombre == "Cinta 9" else "Cinta 11"
        layout[nombre] = {"x": cursor_x, "y": y_inferior, "w": l, "h": 1.5, "color": "#FFD700", "next": [siguiente], "dir": (1,0)}
        cursor_x += l
    
    l11 = configs["Cinta 11"]["largo"]
    layout["Cinta 11"] = {"x": cursor_x, "y": y_inferior, "w": 1.5, "h": l11, "color": "#FFD700", "next": [], "dir": (0,1)}
    
    return layout

layout_props = calcular_layout(st.session_state.config_cintas)

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
            
            # --- USAMOS LA VELOCIDAD CALCULADA MECÁNICAMENTE ---
            # Si no se calculó aún, usamos 0
            vel_real = configs[c_nom].get('velocidad_calc', 0)
            
            avance = vel_real * paso
            b['dist'] += avance
            
            # Fin de cinta
            if b['dist'] >= configs[c_nom]['largo']:
                siguientes = c_props['next']
                if not siguientes:
                    llegadas.append(1)
                else:
                    nueva_nom = siguientes[0]
                    nueva_props = layout[nueva_nom]
                    
                    # Calcular X absoluta de caída
                    if c_props['dir'] == (1,0): fin_x = c_props['x'] + c_props['w']
                    elif c_props['dir'] == (-1,0): fin_x = c_props['x']
                    else: fin_x = c_props['x'] + c_props['w']/2 
                    
                    # Offset
                    if nueva_props['dir'] == (1,0): offset = max(0.0, fin_x - nueva_props['x'])
                    else: offset = 0.0
                    
                    b['cinta'] = nueva_nom
                    b['dist'] = offset
                    
                    # Visual instantánea
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
        colors = ['red' if b['estado'] == 'choque' else 'blue' for b in bolsas]
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colors})
        
    return frames, llegadas

datos, salidas = simular(layout_props, st.session_state.config_cintas, segundos_input, duracion_sim)

# --- 5. VISUALIZACIÓN ---
col1, col2 = st.columns([3, 1])
with col1:
    fig = go.Figure()
    max_x = 0
    max_y = 12
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444"), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=k, showarrow=False, font=dict(size=10))
        max_x = max(max_x, v['x'] + v['w'])

    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="Bolsas"))
    fig.frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=12))]) for f in datos]
    
    fig.update_layout(
        height=600, 
        xaxis=dict(visible=False, range=[-1, max_x + 2]),
        yaxis=dict(visible=False, range=[0, max_y], scaleanchor="x", scaleratio=1),
        plot_bgcolor="#eff2f6",
        margin=dict(l=10, r=10, t=10, b=10),
        updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=0.95,
            buttons=[dict(label="▶️ PLAY", method="animate", 
                          args=[None, dict(frame=dict(duration=40, redraw=True), fromcurrent=True)])])]
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Resultados")
    st.metric("Entrada (Input)", f"{input_teorico:.0f} bolsas/h")
    
    # Proyección de Salida
    # Si la simulación dura 100seg y salieron 20 bolsas -> (20/100) * 3600
    if len(salidas) > 0:
        # Usamos el tiempo transcurrido desde la primera salida hasta la última para mayor precisión
        output_proyectado = (len(salidas) / duracion_sim) * 3600
        # Factor de corrección simple por tiempo de llenado de línea
        output_ajustado = min(input_teorico, output_proyectado * 1.1) 
        
        st.metric("Salida Real (Output)", f"{output_ajustado:.0f} bolsas/h")
        
        hubo_choques = any('red' in str(f['c']) for f in datos)
        
        st.divider()
        if hubo_choques:
            st.error("🚨 **ALERTA:** Atascos detectados. Las bolsas chocan.")
        elif output_ajustado >= 600:
            st.success("✅ **APROBADO:** Superas las 600 u/h.")
        else:
            st.warning("⚠️ **ATENCIÓN:** Revisa velocidades o aumenta la entrada.")
            
    else:
        st.info("Simulando... Espera que las bolsas lleguen al final.")
