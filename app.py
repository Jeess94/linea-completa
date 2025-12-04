import streamlit as st
import plotly.graph_objects as go
import math
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador Pro: Flujo y Motores")
st.title("🏭 Simulador de Línea: Motores y Flujo")
st.markdown("Validación completa: Configuración mecánica de motores + Análisis de caudal de bolsas (Target 600 b/h).")

# --- 1. LAYOUT FÍSICO ---
layout_props = {
    "Cinta 1":  {"x": 0,    "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},
    "Cinta 2":  {"x": 6,    "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 4"], "dir": (1,0)},
    "Cinta 3":  {"x": 3.5,  "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 4":  {"x": 5.0,  "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 7":  {"x": 2,    "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)},
    "Cinta 8":  {"x": 10.5, "y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5, "y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5, "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    "Cinta 11": {"x": 23,   "y": 2, "w": 1.5, "h": 3.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 12"], "dir": (0,1)},
    "Cinta 12": {"x": 23,   "y": 6, "w": 2, "h": 2, "type": "cinta", "color": "#FFD700", "next": ["Tobogán"], "dir": (1,0)},
    "Tobogán":  {"x": 25.5, "y": 6.5,"w": 3, "h": 1, "type": "tobogan", "color": "#C0C0C0", "next": ["Cinta 13"], "dir": (1,0)},
    "Cinta 13": {"x": 29,   "y": 6.5,"w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["ROBOT"], "dir": (1,0)},
    "ROBOT":    {"x": 33,   "y": 6.5,"w": 1, "h": 1, "type": "robot", "color": "#4CAF50", "next": [], "dir": (0,0)},
}

# --- 2. GRUPOS DE CONTROL ---
grupos_control = {
    "Entrada (Cintas 1 y 2)": ["Cinta 1", "Cinta 2"],
    "Bajada (Cintas 3 y 4)": ["Cinta 3", "Cinta 4"],
    "Principal (Cinta 7)": ["Cinta 7"],
    "Transferencia (Cinta 8)": ["Cinta 8"],
    "Transferencia (Cinta 9)": ["Cinta 9"],
    "Principal 2 (Cinta 10)": ["Cinta 10"],
    "Elevador (Cinta 11)": ["Cinta 11"],
    "Superior (Cinta 12)": ["Cinta 12"],
    "Tobogán (Gravedad)": ["Tobogán"],
    "Salida Final (Cinta 13)": ["Cinta 13"]
}

# --- 3. ESTADO INICIAL ---
if 'equipos_config' not in st.session_state:
    st.session_state.equipos_config = {}
    for nombre, props in layout_props.items():
        is_cinta = props['type'] == 'cinta'
        largo_def = props['w'] if props['dir'] in [(1,0), (-1,0)] else props['h']
        if nombre == "Cinta 7": largo_def = 8.0 
        
        st.session_state.equipos_config[nombre] = {
            "largo_m": largo_def,
            "motor_rpm": 1450 if is_cinta else 0,
            "reductor_i": 30 if is_cinta else 0,
            "rodillo_mm": 120 if is_cinta else 0,
            "velocidad_m_s": 0.0
        }

# --- 4. BARRA LATERAL ---
st.sidebar.header("🎛️ Panel de Ingeniería")

# Objetivos
st.sidebar.subheader("🎯 Objetivos")
sec_entrada = st.sidebar.number_input("Entrada (seg/bolsa)", value=3.0, step=0.5, help="Ritmo al que caen las bolsas al inicio")
target_robot = st.sidebar.number_input("Target Robot (b/h)", value=600, step=50)

st.sidebar.divider()
st.sidebar.subheader("🔧 Motores y Reductores")

# Selector de Grupo
grupo_seleccionado = st.sidebar.selectbox("Editar Grupo:", list(grupos_control.keys()))
cintas_del_grupo = grupos_control[grupo_seleccionado]
cinta_lider = cintas_del_grupo[0] 
conf_actual = st.session_state.equipos_config[cinta_lider]
tipo_equipo = layout_props[cinta_lider]['type']

if tipo_equipo == "cinta":
    c1, c2 = st.sidebar.columns(2)
    new_rpm_motor = c1.number_input("RPM Motor", value=int(conf_actual['motor_rpm']), step=50)
    new_reductor_i = c2.number_input("Reductor i", value=int(conf_actual['reductor_i']), step=5)
    
    rpm_eje = new_rpm_motor / new_reductor_i if new_reductor_i > 0 else 0
    st.sidebar.caption(f"Salida Reductor: {rpm_eje:.1f} RPM")

    new_rodillo = st.sidebar.number_input("Ø Rodillo (mm)", value=int(conf_actual['rodillo_mm']), step=5)
    
    if new_rodillo > 0:
        v_m_min = (rpm_eje * math.pi * new_rodillo) / 1000
        v_m_s = v_m_min / 60
    else:
        v_m_min, v_m_s = 0, 0
    
    st.sidebar.success(f"Velocidad: {v_m_min:.2f} m/min")

    for c in cintas_del_grupo:
        st.session_state.equipos_config[c].update({
            "motor_rpm": new_rpm_motor,
            "reductor_i": new_reductor_i,
            "rodillo_mm": new_rodillo,
            "velocidad_m_s": v_m_s
        })

else:
    st.sidebar.info("Caída por gravedad")
    v_m_s = 1.2
    for c in cintas_del_grupo:
        st.session_state.equipos_config[c]["velocidad_m_s"] = v_m_s

# --- 5. SIMULACIÓN ---
def simular_con_robot(layout, configs, intervalo, duracion=45, paso=0.1):
    frames = []
    bolsas = []
    llegadas_robot = [] # Para contar throughput real
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
            
            avance = cinta_conf['velocidad_m_s'] * paso
            b['dist'] += avance
            
            # Fin de cinta
            if b['dist'] >= cinta_conf['largo_m']:
                next_list = cinta_props['next']
                if not next_list:
                    pass 
                elif next_list[0] == "ROBOT":
                    # REGISTRAMOS LA LLEGADA
                    llegadas_robot.append(t_actual)
                    # Bolsa sale de pantalla
                else:
                    nueva_cinta = next_list[0]
                    nueva_props = layout[nueva_cinta]
                    
                    # Offset de caída visual
                    if cinta_props['dir'] == (0, -1):
                        drop_x = cinta_props['x'] + (cinta_props['w'] / 2)
                    else:
                        drop_x = cinta_props['x'] + cinta_props['w']
                        
                    if nueva_props['dir'] == (1, 0):
                        offset_entrada = max(0.0, drop_x - nueva_props['x'])
                    else:
                        offset_entrada = 0.0
                        
                    b['cinta'] = nueva_cinta
                    b['dist'] = offset_entrada
                    
                    # Actualización visual instantánea tras salto
                    if nueva_props['dir'] == (1,0):
                        b['y'] = nueva_props['y'] + nueva_props['h']/2
                        b['x'] = nueva_props['x'] + offset_entrada
                    
                    bolsas_activas.append(b)
            else:
                # Movimiento Visual
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
                
        # Choques
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
        tamano = [12 if b['estado'] == 'choque' else 10 for b in bolsas] # Puntos más grandes
        
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colores, 's': tamano})
        
    return frames, llegadas_robot

# Ejecutar
datos_anim, llegadas = simular_con_robot(layout_props, st.session_state.equipos_config, sec_entrada)

# --- 6. VISUALIZACIÓN ---
col_main, col_stats = st.columns([3, 1])

with col_main:
    fig = go.Figure()
    # Dibujar Cintas (FONDO)
    for k, v in layout_props.items():
        # layer="below" asegura que las cintas estén SIEMPRE detrás de los puntos
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444", width=1), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=f"<b>{k}</b>", showarrow=False, font=dict(size=10))

    # Trace Bolsas (PUNTOS)
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="Bolsas"))

    # Animación
    plotly_frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=f['s'], line=dict(width=1, color="white")))]) for f in datos_anim]
    fig.frames = plotly_frames

    fig.update_layout(
        height=600, 
        xaxis=dict(visible=False, range=[-1, 35], fixedrange=True), 
        yaxis=dict(visible=False, range=[0, 10], scaleanchor="x", scaleratio=1, fixedrange=True),
        plot_bgcolor="#eff2f6",
        margin=dict(l=10, r=10, t=10, b=10),
        updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=0.95, buttons=[dict(label="▶️ PLAY", method="animate", args=[None, dict(frame=dict(duration=50, redraw=True), fromcurrent=True)])])]
    )
    st.plotly_chart(fig, use_container_width=True)

with col_stats:
    st.subheader("📊 Diagnóstico de Flujo")
    
    # Cálculos de KPI
    if len(llegadas) > 2:
        tiempo_total = llegadas[-1] - llegadas[0]
        if tiempo_total > 0:
            ritmo_real_hora = (len(llegadas) / tiempo_total) * 3600
        else:
            ritmo_real_hora = 0
    else:
        ritmo_real_hora = 0

    # Semáforo del Robot
    delta = ritmo_real_hora - target_robot
    st.metric("Ritmo Real (Bolsas/h)", f"{ritmo_real_hora:.0f}", delta=f"{delta:.0f} vs Target")
    
    if ritmo_real_hora < target_robot * 0.85:
        st.error(f"🛑 **INSUFICIENTE**\n\nEl robot necesita {target_robot}, llegan {ritmo_real_hora:.0f}. Sube velocidad o entrada.")
    elif ritmo_real_hora > target_robot * 1.15:
        st.warning(f"⚠️ **SATURACIÓN**\n\nEstás enviando demasiadas bolsas. El robot no dará abasto.")
    else:
        st.success(f"✅ **ÓPTIMO**\n\nFlujo balanceado. El robot trabaja al ritmo correcto.")

    st.divider()
    
    # Resumen de Velocidades Críticas
    st.markdown("**Velocidades Configuradas:**")
    for nombre in ["Cinta 1", "Cinta 7", "Cinta 13"]:
        c = st.session_state.equipos_config[nombre]
        v = c['velocidad_m_s'] * 60
        st.text(f"{nombre}: {v:.1f} m/min")

    # Alerta Choques
    hay_choque = any('red' in str(f['c']) for f in datos_anim) # Check simple
    if hay_choque:
        st.error("🚨 **ALERTA**: Bolsas chocando/solapadas. Revisa velocidades de entrada.")
