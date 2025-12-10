import streamlit as st
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Sintonizador de Línea")
st.title("🎛️ Sintonizador de Flujo y Producción")
st.markdown("Ajusta velocidades y tiempos para lograr **10 bolsas/minuto** (600/hora) sin que se choquen.")

# --- 1. LAYOUT FÍSICO (CONEXIONES CORRECTAS) ---
layout_props = {
    # Nivel Superior
    "Cinta 1":  {"x": 0,    "y": 6, "w": 3.5, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},
    "Cinta 2":  {"x": 6.5,  "y": 6, "w": 3.5, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (-1,0)},
    
    # Bajadas (Se superponen visualmente para conectar)
    "Cinta 3":  {"x": 3.5,  "y": 2.5, "w": 1, "h": 3.5, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 4":  {"x": 5.5,  "y": 2.5, "w": 1, "h": 3.5, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    
    # Línea Principal
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
st.sidebar.header("🎛️ Panel de Control")

# --- A) RITMO DE ENTRADA ---
st.sidebar.subheader("1. Ritmo de Entrada")
st.sidebar.markdown("¿Cada cuánto tirás una bolsa?")
segundos_input = st.sidebar.number_input(
    "⏱️ Segundos entre bolsas:", 
    min_value=0.5, max_value=20.0, value=6.0, step=0.5
)

# Cálculo inmediato para el usuario
bolsas_minuto_teorico = 60 / segundos_input
bolsas_hora_teorico = 3600 / segundos_input

st.sidebar.info(f"""
Esto equivale a meter:
* **{bolsas_minuto_teorico:.1f} bolsas/minuto**
* **{bolsas_hora_teorico:.0f} bolsas/hora**
""")

if bolsas_hora_teorico < 600:
    st.sidebar.warning("⚠️ **AVISO:** Con este ritmo de entrada, es matemáticamente imposible llegar a 600/h. ¡Tirá bolsas más rápido!")

# --- B) VELOCIDADES DE CINTA ---
st.sidebar.divider()
st.sidebar.subheader("2. Velocidades de Cintas")
st.sidebar.markdown("Ajustá para evitar que se amontonen.")

cinta_sel = st.sidebar.selectbox("Seleccionar Cinta:", list(layout_props.keys()))
conf = st.session_state.config_cintas[cinta_sel]

c1, c2 = st.sidebar.columns(2)
nv = c1.number_input(f"Velocidad (m/s)", value=float(conf['velocidad']), step=0.1, min_value=0.1)
nl = c2.number_input(f"Largo (m)", value=float(conf['largo']), step=0.5, min_value=0.5)
st.session_state.config_cintas[cinta_sel].update({"velocidad": nv, "largo": nl})

duracion_sim = st.sidebar.slider("Duración Prueba (seg)", 30, 300, 100)

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
            # Alternar C1 y C2
            origen = "Cinta 1" if (id_count % 2 == 0) else "Cinta 2"
            p = layout[origen]
            # Inicio: C1 (Izquierda), C2 (Derecha)
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
            
            # Fin de cinta y Transferencia
            if b['dist'] >= c_conf['largo']:
                siguientes = c_props['next']
                
                if not siguientes:
                    llegadas.append(1) # Salida Exitosa
                else:
                    nueva_nom = siguientes[0]
                    nueva_props = layout[nueva_nom]
                    
                    # Calcular coordenada X de caída
                    if c_props['dir'] == (1,0): fin_x = c_props['x'] + c_props['w']
                    elif c_props['dir'] == (-1,0): fin_x = c_props['x']
                    else: fin_x = c_props['x'] + c_props['w']/2 
                    
                    # Calcular Offset en nueva cinta
                    if nueva_props['dir'] == (1,0): offset = max(0.0, fin_x - nueva_props['x'])
                    else: offset = 0.0
                    
                    b['cinta'] = nueva_nom
                    b['dist'] = offset
                    
                    # Actualizar visual inmediata
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
                # Movimiento Visual
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

# Ejecutar
datos, salidas = simular(layout_props, st.session_state.config_cintas, segundos_input, duracion_sim)

# --- 5. VISUALIZACIÓN Y RESULTADOS ---
col1, col2 = st.columns([3, 1])

with col1:
    fig = go.Figure()
    # Dibujar Cintas
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444"), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=k, showarrow=False, font=dict(size=10))
    
    # Capa de Bolsas
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="Bolsas"))
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
    st.subheader("📊 Resultados de Salida")
    
    if len(salidas) > 0:
        # Calcular tasa REAL de salida
        # Usamos la duración completa para promediar
        # O si el flujo es constante, usamos la tasa de entrada si no hubo choques
        
        hubo_choques = any('red' in str(f['c']) for f in datos)
        
        # Proyección Realista
        salida_real_hora = (len(salidas) / duracion_sim) * 3600
        # Ajuste: No puede ser mayor que la entrada (física simple)
        salida_real_hora = min(salida_real_hora, bolsas_hora_teorico * 1.05)
        
        salida_real_minuto = salida_real_hora / 60
        
        # --- METRICAS GRANDES ---
        st.metric("Bolsas / Minuto (Real)", f"{salida_real_minuto:.1f} b/min")
        st.metric("Bolsas / Hora (Real)", f"{salida_real_hora:.0f} b/h", delta=f"{salida_real_hora - 600:.0f} vs Objetivo")
        
        st.divider()
        
        if hubo_choques:
            st.error("🚨 **COLISIÓN DETECTADA**\n\nLas cintas van muy lento. Aumenta velocidad o separa la entrada.")
        elif salida_real_hora >= 590: # Margen de error pequeño
            st.success("✅ **OBJETIVO CUMPLIDO**\n\nEl robot recibe suficiente material.")
        else:
            st.warning("⚠️ **NO LLEGAS**\n\nFalta velocidad o entrada.")
            
    else:
        st.info("⏳ Simulando... Dale al Play.")
        st.write(f"Con tu entrada de 1 cada {segundos_input}s, la tasa teórica es {bolsas_hora_teorico:.0f}/h.")
