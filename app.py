import streamlit as st
import plotly.graph_objects as go
import math
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador de Planta Horizontal")
st.title("🏭 Simulador de Planta (Layout Horizontal)")
st.markdown("Todas las cintas son **horizontales**. Las cintas 3 y 4 son transferencias transversales (90°) hacia la línea principal.")

# --- 1. LAYOUT FÍSICO (VISTA DE PLANTA TOP-DOWN) ---
layout_props = {
    # Entradas
    "Cinta 1":  {"x": 0,    "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},
    "Cinta 2":  {"x": 6,    "y": 8, "w": 3, "h": 1, "type": "cinta", "color": "#FFD700", "next": ["Cinta 4"], "dir": (1,0)},
    
    # Cintas Transversales (Mueven material hacia la línea principal)
    # Visualmente van hacia abajo en el mapa 2D, pero son cintas planas.
    "Cinta 3":  {"x": 3.5,  "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    "Cinta 4":  {"x": 5.0,  "y": 4.5, "w": 1, "h": 3, "type": "cinta", "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},
    
    # Línea Principal
    "Cinta 7":  {"x": 2,    "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)},
    "Cinta 8":  {"x": 10.5, "y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5, "y": 2, "w": 1.5,"h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5, "y": 2, "w": 8,  "h": 1.5, "type": "cinta", "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    
    # Elevador / Salida (Corte de simulación)
    "Cinta 11": {"x": 23,   "y": 2, "w": 1.5, "h": 3.5, "type": "cinta", "color": "#FFD700", "next": [], "dir": (0,1)},
}

# --- 2. GRUPOS DE CONTROL ---
grupos_control = {
    "Entrada (Cintas 1 y 2)": ["Cinta 1", "Cinta 2"],
    "Transversales (Cintas 3 y 4)": ["Cinta 3", "Cinta 4"], # Nombre corregido
    "Principal (Cinta 7)": ["Cinta 7"],
    "Transferencias (8, 9, 10)": ["Cinta 8", "Cinta 9", "Cinta 10"],
    "Salida (Cinta 11)": ["Cinta 11"]
}

# --- 3. ESTADO INICIAL ---
if 'equipos_config' not in st.session_state:
    st.session_state.equipos_config = {}
    for nombre, props in layout_props.items():
        # LÓGICA DE LONGITUD:
        # Si la cinta se dibuja más alta que ancha en el plano, su longitud es 'h'.
        # Si es más ancha que alta, su longitud es 'w'.
        es_transversal = props['dir'] == (0, 1) or props['dir'] == (0, -1)
        largo_def = props['h'] if es_transversal else props['w']
        
        # Ajuste específico para C7 (Largo real visual)
        if nombre == "Cinta 7": largo_def = 8.0 
        
        st.session_state.equipos_config[nombre] = {
            "largo_m": largo_def,
            "motor_rpm": 1450,
            "reductor_i": 30,
            "rodillo_mm": 120,
            "velocidad_m_s": 0.0
        }

# --- 4. BARRA LATERAL ---
st.sidebar.header("🎛️ Panel de Ingeniería")

st.sidebar.subheader("🎯 Objetivos")
sec_entrada = st.sidebar.number_input("Entrada (seg/bolsa)", value=3.0, step=0.5)
target_output = st.sidebar.number_input("Target Salida (b/h)", value=600, step=50)

st.sidebar.divider()
st.sidebar.subheader("🔧 Motores y Reductores")

# Selector
grupo_seleccionado = st.sidebar.selectbox("Editar Grupo:", list(grupos_control.keys()))
cintas_del_grupo = grupos_control[grupo_seleccionado]
cinta_lider = cintas_del_grupo[0] 
conf_actual = st.session_state.equipos_config[cinta_lider]

# Inputs
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

# Guardar cambios
for c in cintas_del_grupo:
    st.session_state.equipos_config[c].update({
        "motor_rpm": new_rpm_motor,
        "reductor_i": new_reductor_i,
        "rodillo_mm": new_rodillo,
        "velocidad_m_s": v_m_s
    })

# --- 5. SIMULACIÓN ---
def simular_flujo(layout, configs, intervalo, duracion=40, paso=0.1):
    frames = []
    bolsas = []
    llegadas_final = [] 
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
            
            # Movimiento Físico
            avance = cinta_conf['velocidad_m_s'] * paso
            b['dist'] += avance
            
            # Fin de Cinta
            if b['dist'] >= cinta_conf['largo_m']:
                next_list = cinta_props['next']
                
                if not next_list:
                    llegadas_final.append(t_actual)
                else:
                    nueva_cinta = next_list[0]
                    nueva_props = layout[nueva_cinta]
                    
                    # CÁLCULO DE POSICIÓN DE TRANSFERENCIA (OFFSET)
                    # 1. ¿Dónde estoy en X/Y global al terminar mi cinta?
                    if cinta_props['dir'] == (0, -1): # Terminando Transversal (C3/C4)
                        fin_x = cinta_props['x'] + (cinta_props['w'] / 2)
                    else: # Terminando Horizontal Normal
                        fin_x = cinta_props['x'] + cinta_props['w']
                        
                    # 2. ¿Cuánto debo avanzar en la nueva cinta para coincidir con ese punto?
                    if nueva_props['dir'] == (1, 0): # Entrando a Horizontal (ej. Cinta 7)
                        offset = max(0.0, fin_x - nueva_props['x'])
                    else:
                        offset = 0.0
                    
                    b['cinta'] = nueva_cinta
                    b['dist'] = offset
                    
                    # Actualizar coords visuales para el salto
                    if nueva_props['dir'] == (1,0): 
                        b['y'] = nueva_props['y'] + nueva_props['h']/2
                        b['x'] = nueva_props['x'] + offset
                    elif nueva_props['dir'] == (0,-1): # Entrando a Transversal
                         b['x'] = nueva_props['x'] + nueva_props['w']/2
                         b['y'] = nueva_props['y'] + nueva_props['h'] 
                    elif nueva_props['dir'] == (0,1):
                         b['x'] = nueva_props['x'] + nueva_props['w']/2
                         b['y'] = nueva_props['y'] 

                    bolsas_activas.append(b)
            else:
                # Movimiento Visual
                # Horizontal (Derecha)
                if cinta_props['dir'] == (1, 0): 
                    b['x'] = cinta_props['x'] + b['dist']
                    b['y'] = cinta_props['y'] + cinta_props['h']/2
                
                # Transversal (Hacia "abajo" en el mapa)
                elif cinta_props['dir'] == (0, -1): 
                    b['x'] = cinta_props['x'] + cinta_props['w']/2
                    b['y'] = (cinta_props['y'] + cinta_props['h']) - b['dist'] 
                
                # Transversal (Hacia "arriba" en el mapa - C11)
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
        tamano = [12 if b['estado'] == 'choque' else 10 for b in bolsas]
        
        frames.append({'x': [b['x'] for b in bolsas], 'y': [b['y'] for b in bolsas], 'c': colores, 's': tamano})
        
    return frames, llegadas_final

# Ejecutar
datos_anim, llegadas = simular_flujo(layout_props, st.session_state.equipos_config, sec_entrada)

# --- 6. VISUALIZACIÓN ---
col_main, col_stats = st.columns([3, 1])

with col_main:
    fig = go.Figure()
    # Cintas (Fondo)
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444", width=1), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=f"<b>{k}</b>", showarrow=False, font=dict(size=10))

    # Bolsas
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="Bolsas"))

    # Animación
    plotly_frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=f['s'], line=dict(width=1, color="white")))]) for f in datos_anim]
    fig.frames = plotly_frames

    fig.update_layout(
        height=600, 
        xaxis=dict(visible=False, range=[-1, 26], fixedrange=True), 
        yaxis=dict(visible=False, range=[0, 10], scaleanchor="x", scaleratio=1, fixedrange=True),
        plot_bgcolor="#eff2f6",
        margin=dict(l=10, r=10, t=10, b=10),
        updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=0.95, buttons=[dict(label="▶️ PLAY", method="animate", args=[None, dict(frame=dict(duration=50, redraw=True), fromcurrent=True)])])]
    )
    st.plotly_chart(fig, use_container_width=True)

with col_stats:
    st.subheader("📊 Resultados")
    
    if len(llegadas) > 2:
        tiempo = llegadas[-1] - llegadas[0]
        ritmo = (len(llegadas) / tiempo) * 3600 if tiempo > 0 else 0
    else:
        ritmo = 0

    delta = ritmo - target_output
    st.metric("Salida C11 (b/h)", f"{ritmo:.0f}", delta=f"{delta:.0f}")
    
    st.markdown("---")
    st.markdown("**Velocidades (m/min):**")
    
    def mostrar_v(nombre):
        c = st.session_state.equipos_config[nombre]
        v = c['velocidad_m_s'] * 60
        st.text(f"{nombre}: {v:.1f}")

    mostrar_v("Cinta 1")
    mostrar_v("Cinta 3")
    mostrar_v("Cinta 7")
    mostrar_v("Cinta 11")
    
    st.caption("Nota: Las Cintas 3 y 4 son transportadores planos transversales.")
