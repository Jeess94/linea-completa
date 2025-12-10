import streamlit as st
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador Dinámico")
st.title("🏭 Simulador: Geometría Dinámica")
st.markdown("Ahora el **dibujo cambia** según las medidas que ingreses. Si agrandás una cinta, el resto se acomoda automáticamente.")

# --- 1. CONFIGURACIÓN INICIAL (VALORES POR DEFECTO) ---
if 'config_cintas' not in st.session_state:
    st.session_state.config_cintas = {
        # Entradas
        "Cinta 1": {"largo": 4.0, "velocidad": 1.5},
        "Cinta 2": {"largo": 4.0, "velocidad": 1.5},
        # Bajadas
        "Cinta 3": {"largo": 3.0, "velocidad": 1.5},
        "Cinta 4": {"largo": 3.0, "velocidad": 1.5},
        # Línea Principal (Cadena)
        "Cinta 7":  {"largo": 8.0, "velocidad": 1.5},
        "Cinta 8":  {"largo": 2.0, "velocidad": 1.5},
        "Cinta 9":  {"largo": 2.0, "velocidad": 1.5},
        "Cinta 10": {"largo": 8.0, "velocidad": 1.5},
        "Cinta 11": {"largo": 4.0, "velocidad": 1.5},
    }

# --- 2. PANEL DE CONTROL ---
st.sidebar.header("🎛️ Control de Planta")

# A) Producción
st.sidebar.subheader("1. Producción")
segundos_input = st.sidebar.number_input("⏱️ Intervalo entre bolsas (seg):", 0.5, 60.0, 5.0, 0.5)
st.sidebar.info(f"Ritmo: **{3600/segundos_input:.0f} bolsas/hora**")

# B) Medidas y Velocidades
st.sidebar.divider()
st.sidebar.subheader("2. Dimensiones y Velocidad")

cinta_sel = st.sidebar.selectbox("Editar Cinta:", list(st.session_state.config_cintas.keys()))
datos = st.session_state.config_cintas[cinta_sel]

c1, c2 = st.sidebar.columns(2)
nuevo_l = c1.number_input(f"Largo {cinta_sel} (m)", value=float(datos['largo']), step=0.5, min_value=1.0)
nuevo_v = c2.number_input(f"Velocidad {cinta_sel} (m/s)", value=float(datos['velocidad']), step=0.1, min_value=0.1)

# Guardar cambios
st.session_state.config_cintas[cinta_sel]['largo'] = nuevo_l
st.session_state.config_cintas[cinta_sel]['velocidad'] = nuevo_v

duracion_sim = st.sidebar.slider("Duración Simulación (seg)", 30, 300, 100)

# --- 3. MOTOR DE GEOMETRÍA DINÁMICA (EL CEREBRO VISUAL) ---
def calcular_layout(configs):
    layout = {}
    
    # --- NIVEL SUPERIOR ---
    # Cinta 1: Empieza en 0
    l1 = configs["Cinta 1"]["largo"]
    layout["Cinta 1"] = {"x": 0, "y": 10, "w": l1, "h": 1, "color": "#FFD700", "next": ["Cinta 3"], "dir": (1,0)}
    
    # Cinta 3 (Bajada 1): Conectada al final de Cinta 1
    l3 = configs["Cinta 3"]["largo"] # Es vertical, largo = altura
    layout["Cinta 3"] = {"x": l1, "y": 10 - l3, "w": 1, "h": l3, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)}

    # Espacio entre bajadas (definimos una separación fija de 3 metros entre bajadas)
    separacion_bajadas = 3.0
    
    # Cinta 4 (Bajada 2): A la derecha de la 3
    l4 = configs["Cinta 4"]["largo"]
    pos_x_c4 = l1 + 1 + separacion_bajadas # X de C1 + Ancho C3 + Separación
    layout["Cinta 4"] = {"x": pos_x_c4, "y": 10 - l4, "w": 1, "h": l4, "color": "#FFD700", "next": ["Cinta 7"], "dir": (0,-1)}

    # Cinta 2: Viene de la derecha hacia la Cinta 4
    l2 = configs["Cinta 2"]["largo"]
    # Su final (izquierda) debe coincidir con C4. Su inicio (derecha) es Final + Largo.
    layout["Cinta 2"] = {"x": pos_x_c4 + 1, "y": 10, "w": l2, "h": 1, "color": "#FFD700", "next": ["Cinta 4"], "dir": (-1,0)}

    # --- NIVEL INFERIOR (Calculado en base a las de arriba) ---
    # La altura Y depende de la bajada más larga para que no se superpongan
    max_bajada = max(l3, l4)
    y_inferior = 10 - max_bajada - 0.5 # Un poco más abajo
    
    # Cinta 7: Empieza un poco antes que la bajada de C3 para recogerla
    inicio_c7 = l1 - 1.0 # Un metro antes de donde cae C3
    l7 = configs["Cinta 7"]["largo"]
    layout["Cinta 7"] = {"x": inicio_c7, "y": y_inferior, "w": l7, "h": 1.5, "color": "#FFD700", "next": ["Cinta 8"], "dir": (1,0)}
    
    # --- ENCADENAMIENTO AUTOMÁTICO (7 -> 8 -> 9 -> 10 -> 11) ---
    cursor_x = inicio_c7 + l7
    
    # Cinta 8
    l8 = configs["Cinta 8"]["largo"]
    layout["Cinta 8"] = {"x": cursor_x, "y": y_inferior, "w": l8, "h": 1.5, "color": "#FFD700", "next": ["Cinta 9"], "dir": (1,0)}
    cursor_x += l8
    
    # Cinta 9
    l9 = configs["Cinta 9"]["largo"]
    layout["Cinta 9"] = {"x": cursor_x, "y": y_inferior, "w": l9, "h": 1.5, "color": "#FFD700", "next": ["Cinta 10"], "dir": (1,0)}
    cursor_x += l9
    
    # Cinta 10
    l10 = configs["Cinta 10"]["largo"]
    layout["Cinta 10"] = {"x": cursor_x, "y": y_inferior, "w": l10, "h": 1.5, "color": "#FFD700", "next": ["Cinta 11"], "dir": (1,0)}
    cursor_x += l10
    
    # Cinta 11 (Salida Vertical)
    l11 = configs["Cinta 11"]["largo"]
    # Esta sube, así que Y es base, H es largo
    layout["Cinta 11"] = {"x": cursor_x, "y": y_inferior, "w": 1.5, "h": l11, "color": "#FFD700", "next": [], "dir": (0,1)}
    
    return layout

# Calculamos el layout actual basado en tus inputs
layout_props = calcular_layout(st.session_state.config_cintas)

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
            # Inicio: C1 (0) o C2 (final derecho)
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
            
            # Mover
            avance = c_conf['velocidad'] * paso
            b['dist'] += avance
            
            # Fin de cinta
            if b['dist'] >= c_conf['largo']:
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
    # Calcular límites del gráfico dinámicamente para que no quede nada afuera
    max_x = 0
    max_y = 12
    for k, v in layout_props.items():
        fig.add_shape(type="rect", x0=v['x'], y0=v['y'], x1=v['x']+v['w'], y1=v['y']+v['h'], 
                      fillcolor=v['color'], line=dict(color="#444"), layer="below")
        fig.add_annotation(x=v['x']+v['w']/2, y=v['y']+v['h']/2, text=k, showarrow=False, font=dict(size=10))
        # Actualizar limite derecho
        max_x = max(max_x, v['x'] + v['w'])

    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", name="Bolsas"))
    fig.frames = [go.Frame(data=[go.Scatter(x=f['x'], y=f['y'], mode="markers", marker=dict(color=f['c'], size=12))]) for f in datos]
    
    fig.update_layout(
        height=600, 
        xaxis=dict(visible=False, range=[-1, max_x + 2], fixedrange=False), # Rango dinámico
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
    rate_h = 3600 / segundos_input
    st.metric("Entrada Configurada", f"{rate_h:.0f} bolsas/h")
    
    hubo_choques = any('red' in str(f['c']) for f in datos)
    
    if len(salidas) > 0:
        if hubo_choques:
            st.error("🚨 **CHOQUES DETECTADOS**")
        else:
            st.success(f"✅ **FLUJO CORRECTO**\n\nSalen {len(salidas)} bolsas en esta prueba.")
    else:
        st.info("Simulando...")
