import streamlit as st
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Optimizador de Línea")
st.title("🏭 Optimizador de Producción Inteligente")
st.markdown("El sistema analizará el flujo y te recomendará **qué ajustes hacer** para llegar a 600 bolsas/h.")

# --- 1. CONFIGURACIÓN INICIAL ---
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

# --- 2. MOTOR DE GEOMETRÍA ---
def calcular_layout_dinamico(configs):
    layout = {}
    l3 = configs["Cinta 3"]["largo"]
    l4 = configs["Cinta 4"]["largo"]
    altura_max_bajada = max(l3, l4)
    y_base = 1.5 
    y_superior = y_base + altura_max_bajada + 0.5 
    
    # Nivel Superior
    l1 = configs["Cinta 1"]["largo"]
    layout["Cinta 1"] = {"x": 0, "y": y_superior, "w": l1, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)}
    layout["Cinta 3"] = {"x": l1, "y": y_superior - l3, "w": 1, "h": l3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)}
    
    separacion_bajadas = 2.0 
    pos_x_c4 = l1 + 1 + separacion_bajadas
    layout["Cinta 4"] = {"x": pos_x_c4, "y": y_superior - l4, "w": 1, "h": l4, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)}
    
    l2 = configs["Cinta 2"]["largo"]
    layout["Cinta 2"] = {"x": pos_x_c4 + 1, "y": y_superior, "w": l2, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (-1,0)}
    
    # Nivel Inferior
    inicio_c7 = l1 - 1.5
    if inicio_c7 < 0: inicio_c7 = 0 
    
    l7 = configs["Cinta 7"]["largo"]
    layout["Cinta 7"] = {"x": inicio_c7, "y": y_base, "w": l7, "h": 1.5, "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)}
    
    cursor_x = inicio_c7 + l7 
    for nombre in ["Cinta 8", "Cinta 9", "Cinta 10"]:
        l = configs[nombre]["largo"]
        sig = "Cinta 9" if nombre == "Cinta 8" else "Cinta 10" if nombre == "Cinta 9" else "Cinta 11"
        layout[nombre] = {"x": cursor_x, "y": y_base, "w": l, "h": 1.5, "color": "#FFD700", "next": [sig], "dir": (1,0)}
        cursor_x += l
    
    l11 = configs["Cinta 11"]["largo"]
    layout["Cinta 11"] = {"x": cursor_x, "y": y_base, "w": 1.5, "h": l11, "color": "#FFD700", "next": [], "dir": (0,1)}
    
    return layout

# --- 3. PANEL DE CONTROL ---
st.sidebar.header("🎛️ Configuración")

# A) ESTRATEGIA
st.sidebar.subheader("1. Estrategia de Entrada")
modo_generacion = st.sidebar.radio("Patrón:", ["Constante", "Ráfaga (4 bolsas/10s)"])

input_teorico = 0
if modo_generacion == "Constante":
    segundos_input = st.sidebar.number_input("⏱️ Segundos entre bolsas:", 0.5, 20.0, 5.0, 0.5)
    input_teorico = 3600 / segundos_input
else:
    input_teorico = 1440 # 4 bolsas cada 10s = 0.4/s = 1440/h

st.sidebar.caption(f"Entrada Teórica: {input_teorico:.0f} b/h")

# B) CINTAS
st.sidebar.divider()
st.sidebar.subheader("2. Ajuste de Cintas")
cinta_sel = st.sidebar.selectbox("Cinta:", list(st.session_state.config_cintas.keys()))
conf = st.session_state.config_cintas[cinta_sel]
c1, c2 = st.sidebar.columns(2)
nv = c1.number_input(f"Vel (m/s)", value=float(conf['velocidad']), step=0.1)
nl = c2.number_input(f"Largo (m)", value=float(conf['largo']), step=0.5)
st.session_state.config_cintas[cinta_sel].update({"velocidad": nv, "largo": nl})

duracion_sim = st.sidebar.slider("Duración (seg)", 30, 300, 60)
layout_props = calcular_layout_dinamico(st.session_state.config_cintas)

# --- 4. MOTOR DE SIMULACIÓN ---
def simular(layout, configs, modo, param_entrada, duracion=60, paso=0.1):
    frames = []
    bolsas = []
    llegadas = []
    choques_report = [] # Guardar dónde ocurren los choques
    
    t_acum = 0
    t_ciclo = 0
    id_count = 0
    steps = int(duracion / paso)
    
    patron_rafaga = [(0.5, "Cinta 1"), (2.0, "Cinta 2"), (3.5, "Cinta 1"), (5.0, "Cinta 2")]
    ultimo_disparo_idx = -1 
    
    for step in range(steps):
        t_actual = step * paso
        
        # Generación
        if modo == "Constante":
            t_acum += paso
            if t_acum >= param_entrada:
                t_acum = 0
                origen = "Cinta 1" if (id_count % 2 == 0) else "Cinta 2"
                p = layout[origen]
                sx = p['x'] if p['dir'] == (1,0) else p['x'] + p['w']
                bolsas.append({'id': id_count, 'cinta': origen, 'dist': 0.0, 'x': sx, 'y': p['y'] + p['h']/2, 'estado': 'ok'})
                id_count += 1
        else: 
            t_ciclo = t_actual % 10.0
            if t_ciclo < paso: ultimo_disparo_idx = -1
            for i, (t_trigger, cinta_origen) in enumerate(patron_rafaga):
                if i > ultimo_disparo_idx and t_ciclo >= t_trigger:
                    p = layout[cinta_origen]
                    sx = p['x'] if p['dir'] == (1,0) else p['x'] + p['w']
                    bolsas.append({'id': id_count, 'cinta': cinta_origen, 'dist': 0.0, 'x': sx, 'y': p['y'] + p['h']/2, 'estado': 'ok'})
                    id_count += 1
                    ultimo_disparo_idx = i
        
        # Movimiento
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
                    # Registrar dónde chocaron (una sola vez por par)
                    choque_id = f"{b1['cinta']}"
                    if choque_id not in choques_report:
                        choques_report.append(choque_id)
        
        bolsas = activos
        colors = ['#FF0000' if b['estado'] == 'choque' else '#0000FF' for b in bolsas]
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colors})
        
    return frames, llegadas, choques_report

parametro = segundos_input if modo_generacion == "Constante" else None
datos, salidas, reportes_choque = simular(layout_props, st.session_state.config_cintas, modo_generacion, parametro, duracion_sim)

# --- 5. VISUALIZACIÓN ---
col1, col2 = st.columns([3, 1])

with col1:
    fig = go.Figure()
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
    st.header("📋 Diagnóstico")
    
    # 1. ANÁLISIS DE ENTRADA
    if input_teorico < 600:
        st.error(f"❌ **PROBLEMA DE ENTRADA**")
        st.write(f"Estás ingresando solo **{input_teorico:.0f} bolsas/h**.")
        st.info("💡 **Solución:** Baja los 'Segundos entre bolsas' a **6.0 o menos**.")
    else:
        st.success(f"✅ Entrada Correcta: {input_teorico:.0f} b/h")

    # 2. ANÁLISIS DE SALIDA Y CHOQUES
    if len(salidas) > 0:
        salida_real = min((len(salidas)/duracion_sim)*3600, input_teorico * 1.05)
        st.metric("Salida Real", f"{salida_real:.0f} b/h", delta=f"{salida_real-600:.0f}")
        
        st.divider()
        st.subheader("🛠️ Acciones Requeridas")
        
        if len(reportes_choque) > 0:
            st.error("🚨 **SE DETECTARON CHOQUES**")
            st.write("Las bolsas se están amontonando en:")
            for c in reportes_choque:
                st.write(f"- 🔴 **{c}**")
            
            st.warning(f"👉 **Solución:** Aumenta la velocidad de {reportes_choque[0]} (y las siguientes).")
        
        elif salida_real >= 600:
            st.success("🎉 **LÍNEA OPTIMIZADA**")
            st.write("Configuración válida para el robot.")
        else:
            st.warning("⚠️ **Producción Baja**")
            st.write("No hay choques, pero no llegas a 600. Revisa si la simulación duró suficiente.")

    else:
        st.info("Esperando resultados...")
