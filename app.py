import streamlit as st
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador de Flujo Simplificado")
st.title("🏭 Simulador de Flujo: Control Manual")
st.markdown("Control directo de velocidad y cadencia. Rutas fijas: **C1->C3->C7** y **C2->C4->C7**.")

# --- 1. LAYOUT FÍSICO (COORDENADAS) ---
# Definimos las conexiones explícitas en 'next'
layout_props = {
    # Entradas
    "Cinta 1":  {"x": 0,    "y": 8, "w": 3, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)},   # Derecha
    "Cinta 2":  {"x": 6,    "y": 8, "w": 3, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (1,0)},   # Derecha
    
    # Transversales (Bajan)
    "Cinta 3":  {"x": 3.5,  "y": 4.5, "w": 1, "h": 3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},  # Abajo
    "Cinta 4":  {"x": 5.0,  "y": 4.5, "w": 1, "h": 3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)},  # Abajo
    
    # Línea Principal (Recolectora)
    "Cinta 7":  {"x": 2,    "y": 2, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)}, # Derecha
    "Cinta 8":  {"x": 10.5, "y": 2, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)},
    "Cinta 9":  {"x": 12.5, "y": 2, "w": 1.5,"h": 1.5, "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)},
    "Cinta 10": {"x": 14.5, "y": 2, "w": 8,  "h": 1.5, "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)},
    "Cinta 11": {"x": 23,   "y": 2, "w": 1.5, "h": 3.5, "color": "#FFD700", "next": [], "dir": (0,1)},          # Arriba (Final)
}

# --- 2. ESTADO INICIAL ---
if 'config_cintas' not in st.session_state:
    st.session_state.config_cintas = {}
    for nombre, props in layout_props.items():
        # Detectar largo visual por defecto
        es_vertical = props['dir'] == (0, 1) or props['dir'] == (0, -1)
        largo_def = props['h'] if es_vertical else props['w']
        if nombre == "Cinta 7": largo_def = 8.0 
        
        st.session_state.config_cintas[nombre] = {
            "largo": largo_def,
            "velocidad": 1.0 # m/s por defecto
        }

# --- 3. PANEL LATERAL (INPUTS SIMPLIFICADOS) ---
st.sidebar.header("🎛️ Control de Línea")

# A) CADENCIA DE BOLSAS
st.sidebar.subheader("📦 Producción")
bolsas_por_segundo = st.sidebar.number_input("Cadencia (Bolsas que salen por seg)", value=0.5, step=0.1, help="Ej: 0.5 = 1 bolsa cada 2 seg")
intervalo_creacion = 1.0 / bolsas_por_segundo if bolsas_por_segundo > 0 else 9999

# B) CONFIGURACIÓN DE CINTAS
st.sidebar.divider()
st.sidebar.subheader("🔧 Velocidades y Largos")

cinta_seleccionada = st.sidebar.selectbox("Editar Cinta:", list(layout_props.keys()))
conf_actual = st.session_state.config_cintas[cinta_seleccionada]

col1, col2 = st.sidebar.columns(2)
nueva_vel = col1.number_input(f"Velocidad {cinta_seleccionada} (m/s)", value=float(conf_actual['velocidad']), step=0.1)
nuevo_largo = col2.number_input(f"Largo {cinta_seleccionada} (m)", value=float(conf_actual['largo']), step=0.5)

# Guardar cambios
st.session_state.config_cintas[cinta_seleccionada]['velocidad'] = nueva_vel
st.session_state.config_cintas[cinta_seleccionada]['largo'] = nuevo_largo

# --- 4. MOTOR DE SIMULACIÓN ---
def ejecutar_simulacion(layout, configs, intervalo_sec, duracion=30, paso=0.1):
    frames = []
    bolsas = []
    t_acumulado = 0
    id_counter = 0
    pasos_totales = int(duracion / paso)
    
    for _ in range(pasos_totales):
        t_acumulado += paso
        
        # 1. GENERAR BOLSAS (Alternando Cinta 1 y Cinta 2)
        if t_acumulado >= intervalo_sec:
            t_acumulado = 0
            origen = "Cinta 1" if (id_counter % 2 == 0) else "Cinta 2"
            props = layout[origen]
            bolsas.append({
                'id': id_counter, 
                'cinta_actual': origen, 
                'distancia_recorrida': 0.0,
                'x': props['x'], 
                'y': props['y'] + props['h']/2, # Centrado en altura
                'estado': 'ok'
            })
            id_counter += 1
            
        bolsas_activas = []
        for b in bolsas:
            nombre_cinta = b['cinta_actual']
            props_cinta = layout[nombre_cinta]
            conf_cinta = configs[nombre_cinta]
            
            # 2. MOVER BOLSA
            avance = conf_cinta['velocidad'] * paso
            b['distancia_recorrida'] += avance
            
            # 3. VERIFICAR SI TERMINÓ LA CINTA ACTUAL
            if b['distancia_recorrida'] >= conf_cinta['largo']:
                siguientes = props_cinta['next']
                
                if not siguientes:
                    # Fin de recorrido (Cinta 11), la bolsa sale
                    pass 
                else:
                    nueva_cinta_nombre = siguientes[0]
                    nueva_props = layout[nueva_cinta_nombre]
                    
                    # --- CÁLCULO DE POSICIÓN DE CAÍDA (OFFSET) ---
                    # Calculamos dónde cae físicamente para que no vuelva al inicio de la nueva cinta
                    
                    # ¿Dónde termina visualmente la cinta actual?
                    if props_cinta['dir'] == (0, -1): # Viene bajando (C3, C4)
                        # El punto de caída es el centro X de la cinta vertical
                        punto_caida_x = props_cinta['x'] + (props_cinta['w'] / 2)
                    else: # Viene horizontal (C1, C2)
                        # El punto de caída es el final derecho X
                        punto_caida_x = props_cinta['x'] + props_cinta['w']
                        
                    # ¿Dónde empieza la nueva cinta?
                    inicio_nueva_x = nueva_props['x']
                    
                    # EL OFFSET es la diferencia. Ej: Cinta 3 cae en X=4. Cinta 7 empieza en X=2. Offset = 2m.
                    if nueva_props['dir'] == (1, 0): # Si entra a una horizontal
                        offset_entrada = max(0.0, punto_caida_x - inicio_nueva_x)
                    else:
                        offset_entrada = 0.0
                        
                    # Transferir bolsa
                    b['cinta_actual'] = nueva_cinta_nombre
                    b['distancia_recorrida'] = offset_entrada
                    
                    # Actualizar coordenadas visuales para el "teletransporte" a la nueva cinta
                    if nueva_props['dir'] == (1,0): # Horizontal
                        b['y'] = nueva_props['y'] + nueva_props['h']/2
                        b['x'] = nueva_props['x'] + offset_entrada
                    elif nueva_props['dir'] == (0,-1): # Vertical Bajada
                         b['x'] = nueva_props['x'] + nueva_props['w']/2
                         b['y'] = nueva_props['y'] + nueva_props['h'] 
                    elif nueva_props['dir'] == (0,1): # Vertical Subida
                         b['x'] = nueva_props['x'] + nueva_props['w']/2
                         b['y'] = nueva_props['y'] 

                    bolsas_activas.append(b)
            else:
                # 4. ACTUALIZAR VISUALIZACIÓN (Si sigue en la misma cinta)
                dist = b['distancia_recorrida']
                
                if props_cinta['dir'] == (1, 0): # Moviéndose a derecha
                    b['x'] = props_cinta['x'] + dist
                    b['y'] = props_cinta['y'] + props_cinta['h']/2
                    
                elif props_cinta['dir'] == (0, -1): # Moviéndose abajo (C3, C4)
                    b['x'] = props_cinta['x'] + props_cinta['w']/2
                    # En Plotly Y crece hacia arriba, así que restar distancia es bajar
                    b['y'] = (props_cinta['y'] + props_cinta['h']) - dist 
                    
                elif props_cinta['dir'] == (0, 1): # Moviéndose arriba (C11)
                    b['x'] = props_cinta['x'] + props_cinta['w']/2
                    b['y'] = props_cinta['y'] + dist
                
                bolsas_activas.append(b)
        
        bolsas = bolsas_activas
        # Guardar frame para animación
        frames.append({
            'x': [b['x'] for b in bolsas],
            'y': [b['y'] for b in bolsas]
        })
        
    return frames

# Ejecutar lógica
datos_animacion = ejecutar_simulacion(
    layout_props, 
    st.session_state.config_cintas, 
    intervalo_creacion
)

# --- 5. VISUALIZACIÓN GRÁFICA ---
col_grafico, col_datos = st.columns([3, 1])

with col_grafico:
    fig = go.Figure()
    
    # Dibujar Cintas (Fondo estático)
    for k, v in layout_props.items():
        fig.add_shape(type="rect", 
            x0=v['x'], y0=v['y'], 
            x1=v['x']+v['w'], y1=v['y']+v['h'], 
            fillcolor=v['color'], line=dict(color="#333", width=1), layer="below")
        
        # Etiqueta de nombre
        fig.add_annotation(
            x=v['x']+v['w']/2, y=v['y']+v['h']/2, 
            text=f"<b>{k}</b>", showarrow=False, 
            font=dict(size=10, color="black"))

    # Trace inicial de bolsas
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="Bolsas"))

    # Crear Animación
    frames_plotly = []
    for f in datos_animacion:
        frames_plotly.append(go.Frame(data=[
            go.Scatter(
                x=f['x'], y=f['y'], 
                mode="markers", 
                marker=dict(color="blue", size=10, line=dict(width=1, color="white"))
            )
        ]))
    fig.frames = frames_plotly

    # Configuración del lienzo
    fig.update_layout(
        height=600,
        xaxis=dict(visible=False, range=[-1, 26], fixedrange=True),
        yaxis=dict(visible=False, range=[0, 10], scaleanchor="x", scaleratio=1, fixedrange=True),
        plot_bgcolor="#f0f2f6",
        margin=dict(l=10, r=10, t=10, b=10),
        updatemenus=[dict(type="buttons", showactive=False, x=0.05, y=0.95, 
            buttons=[dict(label="▶️ PLAY", method="animate", 
                          args=[None, dict(frame=dict(duration=50, redraw=True), fromcurrent=True)])])]
    )
    st.plotly_chart(fig, use_container_width=True)

with col_datos:
    st.subheader("📊 Resumen")
    st.write(f"**Cadencia:** {bolsas_por_segundo} bolsas/seg")
    st.markdown("---")
    st.write("**Configuración Actual:**")
    
    # Mostrar tabla simple de velocidades
    for k, v in st.session_state.config_cintas.items():
        st.caption(f"**{k}:** {v['velocidad']} m/s (L: {v['largo']}m)")
