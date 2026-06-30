import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import json
import random
import math
import time

def render_echarts(options, height="300px"):
    options_json = json.dumps(options)
    h_int = int(height.replace("px", ""))
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <style>
            html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background-color: transparent; }}
            #chart_container {{ width: 100%; height: {height}; }}
        </style>
    </head>
    <body>
        <div id="chart_container"></div>
        <script>
            var chartDom = document.getElementById('chart_container');
            var myChart = echarts.init(chartDom, 'dark');
            var option = {options_json};
            myChart.setOption(option);
            window.addEventListener('resize', function() {{
                myChart.resize();
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=h_int + 5, scrolling=False)

# ==========================================
# 1. Fuzzy Logic Engine Import
# ==========================================
try:
    from fuzzy_engine import (
        Server_Temp_Sets,
        Workload_Sets,
        Ambient_Temp_Sets,
        Cooling_Sets,
        interpolate,
        fuzzify,
        evaluate_rules,
        defuzzify,
        RULES
    )
except ImportError:
    from data_center.fuzzy_engine import (
        Server_Temp_Sets,
        Workload_Sets,
        Ambient_Temp_Sets,
        Cooling_Sets,
        interpolate,
        fuzzify,
        evaluate_rules,
        defuzzify,
        RULES
    )

# ==========================================
# 2. Static Streamlit UI & Interactive ECharts Twin
# ==========================================

st.set_page_config(
    page_title="Data Center Fuzzy Cooling Twin",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dark aesthetic and glassmorphism styling
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00e676 !important;
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Data Center Fuzzy Cooling Twin")
st.caption("Static Batch Simulation & Step-by-Step Interactive Fuzzy Logic Inspector")

# Sidebar - Static Input Configuration
st.sidebar.header("🎲 Simulation Starting Inputs")

# Randomization Logic
if "init_temp" not in st.session_state:
    st.session_state.init_temp = 25.0
if "init_workload" not in st.session_state:
    st.session_state.init_workload = 40.0
if "init_ambient" not in st.session_state:
    st.session_state.init_ambient = 22.0

if st.sidebar.button("🎲 Randomize Starting Inputs", use_container_width=True):
    st.session_state.init_temp = round(random.uniform(15.0, 75.0), 1)
    st.session_state.init_workload = round(random.uniform(10.0, 90.0), 1)
    st.session_state.init_ambient = round(random.uniform(12.0, 38.0), 1)
    st.rerun()

init_temp = st.sidebar.number_input("Initial Server Temp (°C)", min_value=10.0, max_value=90.0, value=float(st.session_state.init_temp), step=0.5, format="%.2f")
init_work = st.sidebar.number_input("Initial Workload (%)", min_value=0.0, max_value=100.0, value=float(st.session_state.init_workload), step=0.5, format="%.2f")
init_amb = st.sidebar.number_input("Initial Ambient Temp (°C)", min_value=10.0, max_value=45.0, value=float(st.session_state.init_ambient), step=0.5, format="%.2f")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Simulation Settings")
sim_steps = st.sidebar.slider("📈 Simulation Run Steps", 20, 500, 150)
elec_price = st.sidebar.slider("💰 Electricity Price (₱/kWh)", 8.00, 15.00, 11.50, step=0.10, help="Philippine commercial tariff range (e.g., Meralco)")
base_ambient = st.sidebar.slider("❄️ CRAC Target Temp Setpoint (°C)", 10.0, 35.0, 22.0, help="The target temperature set on the computer room air conditioners (CRAC). The room ambient temperature fluctuates dynamically around this target based on server heat output.")
heat_dissipation_steps = st.sidebar.slider("⏳ Heat Dissipation Steps", 0, 10, 4, help="Phase lag (delay steps) between fan action changes and actual heat reduction. Higher lag causes thermal overshoot/oscillations.")
work_volatility = st.sidebar.slider("🎲 Workload Volatility (%)", 0, 100, 40, help="Stochasticness of workload. Higher values cause sudden workload spikes and larger step variations.")

# Batch run trigger
run_clicked = st.sidebar.button("▶️ Run Simulation", type="primary", use_container_width=True)

# Cache / persist history in Session State to prevent random regeneration on UI interaction
if "sim_history" not in st.session_state or run_clicked:
    history = {
        "Time": [], "Server_Temp": [], "Ambient_Temp": [], 
        "Workload": [], "Cooling_Output": [], "Total_Cost": []
    }
    
    current_temp = init_temp
    current_work = init_work
    current_ambient = init_amb
    current_cost = 0.0
    cooling_queue = []
    
    for step in range(sim_steps):
        # 1. Stochastic Workload (Volatility fraction scales jump chance & jump magnitude)
        vol_frac = work_volatility / 100.0
        jump_chance = 0.05 + 0.20 * vol_frac
        
        if random.random() < jump_chance:
            max_jump = int(10 + 35 * vol_frac)
            jump = random.choice([-max_jump, -max_jump // 2, max_jump // 2, max_jump])
            current_work = max(0.0, min(100.0, current_work + jump))
        else:
            max_delta = 2.0 + 10.0 * vol_frac
            delta_w = random.uniform(-max_delta, max_delta)
            current_work = max(0.0, min(100.0, current_work + delta_w))
        
        # 2. Fuzzy Logic Inference (uses current room ambient temp)
        mem_temp = fuzzify(current_temp, Server_Temp_Sets)
        mem_work = fuzzify(current_work, Workload_Sets)
        mem_amb = fuzzify(current_ambient, Ambient_Temp_Sets)
        
        agg_rules = evaluate_rules(mem_temp, mem_work, mem_amb)
        cooling_output = defuzzify(agg_rules)
        
        # Queue/Delay mechanism for cooling response
        cooling_queue.append(cooling_output)
        if len(cooling_queue) > heat_dissipation_steps:
            applied_cooling = cooling_queue.pop(0)
        else:
            applied_cooling = cooling_queue[0]
        
        # 3. Thermal Physics Proxy (With cooling delay and thermal noise)
        heat_generated = current_work * 0.16  
        ambient_influence = (current_ambient - current_temp) * 0.18
        cooling_effect = applied_cooling * 0.12 
        
        # Injected thermal noise + stochastic burst spikes
        thermal_noise = random.uniform(-0.4, 0.4)
        if random.random() < 0.05:
            thermal_noise += random.uniform(1.8, 3.2)  # localized heat spike
            
        current_temp = current_temp + heat_generated + ambient_influence - cooling_effect + thermal_noise
        current_temp = max(10.0, min(100.0, current_temp))
        
        # 4. Sealed Data Center Room Dynamics (Exhaust heat feeds room ambient; CRAC extracts it)
        # Server fans blow out heat proportional to fan power, raising room temp
        heat_dumped_to_room = applied_cooling * 0.05
        # CRAC system extracts heat proportional to the difference between room temp and setpoint (increased from 0.14 to 0.38)
        crac_cooling = (current_ambient - base_ambient) * 0.38
        ambient_change = heat_dumped_to_room - crac_cooling + random.uniform(-0.15, 0.15)
        
        current_ambient = current_ambient + ambient_change
        current_ambient = max(10.0, min(50.0, current_ambient))
        
        # 5. Cost calculation
        cooling_power_kw = (cooling_output / 100.0) * 50.0 
        step_cost = cooling_power_kw * elec_price
        current_cost += step_cost
        
        history["Time"].append(step)
        history["Server_Temp"].append(current_temp)
        history["Ambient_Temp"].append(current_ambient)
        history["Workload"].append(current_work)
        history["Cooling_Output"].append(cooling_output)
        history["Total_Cost"].append(current_cost)
        
    st.session_state.sim_history = history

history = st.session_state.sim_history
df = pd.DataFrame(history)
time_labels = [str(t) for t in df["Time"]]

# --- KPI Section (Electricity is just a number) ---
st.subheader("📊 Simulation Performance Summary")
avg_temp = df["Server_Temp"].mean()
max_temp = df["Server_Temp"].max()
avg_work = df["Workload"].mean()
total_cost = history["Total_Cost"][-1]

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total Electricity Cost", f"₱{total_cost:,.2f}")
col2.metric("🌡️ Average Server Temp", f"{avg_temp:.1f} °C")
col3.metric("🔥 Max Server Temp", f"{max_temp:.1f} °C")
col4.metric("⚙️ Average CPU Workload", f"{avg_work:.1f}%")

st.markdown("<br>", unsafe_allow_html=True)

# --- Horizontal Stretching Charts ---
st.subheader("📈 Time-Series Telemetry")

# 1. Temperature Dynamics Chart (Full width)
option_temp = {
    "title": {"text": "Server vs Ambient Temperature Profile", "textStyle": {"color": "#ffffff", "fontSize": 14}},
    "tooltip": {"trigger": "axis"},
    "legend": {"data": ["Server Temp (°C)", "Ambient Temp (°C)"], "textStyle": {"color": "#ccc"}, "top": 25},
    "grid": {"left": "2%", "right": "2%", "bottom": "3%", "containLabel": True},
    "xAxis": {"type": "category", "boundaryGap": False, "data": time_labels, "axisLabel": {"color": "#888"}},
    "yAxis": {"type": "value", "scale": True, "axisLabel": {"color": "#888", "formatter": "{value} °C"}, "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.05)"}}},
    "series": [
        {
            "name": "Server Temp (°C)",
            "type": "line",
            "smooth": True,
            "showSymbol": False,
            "data": [round(v, 1) for v in df["Server_Temp"]],
            "lineStyle": {"width": 3, "color": "#ff4b4b"},
            "itemStyle": {"color": "#ff4b4b"}
        },
        {
            "name": "Ambient Temp (°C)",
            "type": "line",
            "smooth": True,
            "showSymbol": False,
            "data": [round(v, 1) for v in df["Ambient_Temp"]],
            "lineStyle": {"width": 2, "type": "dashed", "color": "#00b0ff"},
            "itemStyle": {"color": "#00b0ff"}
        }
    ]
}
render_echarts(options=option_temp, height="350px")

st.markdown("<br>", unsafe_allow_html=True)
# 2. Workload & Cooling Output Chart (Full width)
option_work = {
    "title": {"text": "Data Center Workload vs Cooling Power Utilized", "textStyle": {"color": "#ffffff", "fontSize": 14}},
    "tooltip": {"trigger": "axis"},
    "legend": {"data": ["Workload (%)", "Cooling Power Utilized (%)"], "textStyle": {"color": "#ccc"}, "top": 25},
    "grid": {"left": "2%", "right": "2%", "bottom": "3%", "containLabel": True},
    "xAxis": {"type": "category", "boundaryGap": False, "data": time_labels, "axisLabel": {"color": "#888"}},
    "yAxis": {"type": "value", "min": 0, "max": 100, "axisLabel": {"color": "#888", "formatter": "{value}%"}, "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.05)"}}},
    "series": [
        {
            "name": "Workload (%)",
            "type": "line",
            "smooth": True,
            "showSymbol": False,
            "data": [round(v, 1) for v in df["Workload"]],
            "areaStyle": {"color": "rgba(171, 71, 188, 0.1)"},
            "lineStyle": {"width": 2, "color": "#ab47bc"},
            "itemStyle": {"color": "#ab47bc"}
        },
        {
            "name": "Cooling Power Utilized (%)",
            "type": "line",
            "smooth": True,
            "showSymbol": False,
            "data": [round(v, 1) for v in df["Cooling_Output"]],
            "lineStyle": {"width": 3, "color": "#00e676"},
            "itemStyle": {"color": "#00e676"}
        }
    ]
}
render_echarts(options=option_work, height="350px")

st.markdown("<hr>", unsafe_allow_html=True)

# --- Interactive Inspector Section ---
st.subheader("🔍 Step-by-Step Fuzzy Logic Inspector")
st.write("Drag the slider to view the exact fuzzification, rule fires, and output aggregation for any specific step in the history.")

inspect_step = st.slider("Select Simulation Step to Inspect:", 0, len(df) - 1, len(df) - 1)

ins_temp = history["Server_Temp"][inspect_step]
ins_work = history["Workload"][inspect_step]
ins_amb = history["Ambient_Temp"][inspect_step]
ins_cooling = history["Cooling_Output"][inspect_step]

# Recalculate fuzzy state for inspected step
mem_temp = fuzzify(ins_temp, Server_Temp_Sets)
mem_work = fuzzify(ins_work, Workload_Sets)
mem_amb = fuzzify(ins_amb, Ambient_Temp_Sets)
agg_rules = evaluate_rules(mem_temp, mem_work, mem_amb)

st.markdown(f"#### 🔍 Fuzzy State at Step **{inspect_step}** (Server Temp: **{ins_temp:.1f} °C**, Workload: **{ins_work:.1f}%**, Ambient: **{ins_amb:.1f} °C**, Cooling Power Utilized: **{ins_cooling:.1f}%**)")

tab_viz, tab_rules = st.tabs(["🧠 Fuzzification & Defuzzification Curves", "📜 Fired Rule Activation Matrix"])

with tab_viz:
    def build_echarts_fuzzy_variable(sets_dict, current_val, title, unit, colors):
        x_min = min([s["X"][0] for s in sets_dict.values()])
        x_max = max([s["X"][-1] for s in sets_dict.values()])
        steps = 80
        x_pts = [round(x_min + i * (x_max - x_min) / steps, 1) for i in range(steps + 1)]
        
        series_list = []
        for idx, (label, params) in enumerate(sets_dict.items()):
            y_pts = [round(interpolate(x, params["X"], params["Y"]), 3) for x in x_pts]
            series_list.append({
                "name": label,
                "type": "line",
                "smooth": True,
                "showSymbol": False,
                "data": [[x_pts[i], y_pts[i]] for i in range(len(x_pts))],
                "lineStyle": {"width": 2.5, "color": colors[idx % len(colors)]},
                "itemStyle": {"color": colors[idx % len(colors)]}
            })
            
        series_list[0]["markLine"] = {
            "symbol": ["none", "none"],
            "label": {"show": True, "formatter": f"Current: {current_val:.1f}{unit}", "color": "#fff", "fontSize": 12},
            "lineStyle": {"type": "dashed", "color": "#ffffff", "width": 2},
            "data": [{"xAxis": round(current_val, 1)}]
        }
        
        option = {
            "title": {"text": title, "textStyle": {"color": "#ffffff", "fontSize": 13}},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": list(sets_dict.keys()), "textStyle": {"color": "#ccc"}, "top": 20},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "xAxis": {"type": "value", "min": x_min, "max": x_max, "axisLabel": {"color": "#888"}},
            "yAxis": {"type": "value", "min": 0, "max": 1.1, "axisLabel": {"color": "#888"}},
            "series": series_list
        }
        return option

    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        render_echarts(
            options=build_echarts_fuzzy_variable(Server_Temp_Sets, ins_temp, "Server Temperature", "°C", ['#4caf50', '#ff9800', '#f44336']),
            height="240px"
        )
        st.write("**Membership Degrees (μ):**")
        for k, v in mem_temp.items():
            st.progress(v, text=f"{k}: {v:.2f}")
            
    with f_col2:
        render_echarts(
            options=build_echarts_fuzzy_variable(Workload_Sets, ins_work, "Server Workload", "%", ['#81c784', '#ba68c8', '#e57373']),
            height="240px"
        )
        st.write("**Membership Degrees (μ):**")
        for k, v in mem_work.items():
            st.progress(v, text=f"{k}: {v:.2f}")
            
    with f_col3:
        render_echarts(
            options=build_echarts_fuzzy_variable(Ambient_Temp_Sets, ins_amb, "Ambient Temperature", "°C", ['#64b5f6', '#ffd54f', '#ff8a65']),
            height="240px"
        )
        st.write("**Membership Degrees (μ):**")
        for k, v in mem_amb.items():
            st.progress(v, text=f"{k}: {v:.2f}")

    st.markdown("---")
    
    c_out1, c_out2 = st.columns([2, 1])
    with c_out1:
        colors_out = {'Low': '#4caf50', 'Medium': '#2196f3', 'High': '#ff9800', 'Maximum': '#f44336'}
        x_pts = [i for i in range(101)]
        
        series_out = []
        for idx, (label, params) in enumerate(Cooling_Sets.items()):
            y_pts = [interpolate(x, params["X"], params["Y"]) for x in x_pts]
            clip_level = agg_rules[label]
            y_clipped = [round(min(y, clip_level), 3) for y in y_pts]
            
            series_out.append({
                "name": f"{label} (Clip: {clip_level:.2f})",
                "type": "line",
                "smooth": True,
                "showSymbol": False,
                "data": [[x_pts[i], y_clipped[i]] for i in range(len(x_pts))],
                "areaStyle": {"color": colors_out[label], "opacity": 0.25},
                "lineStyle": {"width": 2, "color": colors_out[label]},
                "itemStyle": {"color": colors_out[label]}
            })
            
        series_out[0]["markLine"] = {
            "symbol": ["none", "none"],
            "label": {"show": True, "formatter": f"Centroid: {ins_cooling:.1f}%", "color": "#00e676", "fontSize": 13, "fontWeight": "bold"},
            "lineStyle": {"type": "solid", "color": "#00e676", "width": 3},
            "data": [{"xAxis": round(ins_cooling, 1)}]
        }
        
        option_out = {
            "title": {"text": "Cooling Output Aggregation & Centroid Calculation", "textStyle": {"color": "#ffffff", "fontSize": 13}},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": [f"{label} (Clip: {agg_rules[label]:.2f})" for label in Cooling_Sets.keys()], "textStyle": {"color": "#ccc"}, "top": 20},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "xAxis": {"type": "value", "min": 0, "max": 100, "axisLabel": {"color": "#888"}},
            "yAxis": {"type": "value", "min": 0, "max": 1.1, "axisLabel": {"color": "#888"}},
            "series": series_out
        }
        render_echarts(options=option_out, height="280px")
        
    with c_out2:
        st.markdown("#### Clipped Output Activation Strengths")
        for label, strength in agg_rules.items():
            st.metric(f"Output Set: {label}", f"{strength:.2f}", help=f"Clipping strength for {label} cooling category at inspected step.")

with tab_rules:
    st.subheader("📜 27-Rule Activation Inspector")
    st.write("Fired rules for the inspected step evaluated using Mamdani minimum-clipping.")
    
    active_rules_data = []
    for idx, rule in enumerate(RULES, 1):
        t_label = rule["if"]["Temp"]
        w_label = rule["if"]["Workload"]
        a_label = rule["if"]["Ambient"]
        
        s_t = mem_temp[t_label]
        s_w = mem_work[w_label]
        s_a = mem_amb[a_label]
        
        rule_strength = min(s_t, s_w, s_a)
        
        if rule_strength > 0:
            active_rules_data.append({
                "Rule ID": f"Rule #{idx}",
                "Server Temp IF": f"{t_label} (μ={s_t:.2f})",
                "Workload IF": f"{w_label} (μ={s_w:.2f})",
                "Ambient IF": f"{a_label} (μ={s_a:.2f})",
                "Fired Strength": f"{rule_strength:.3f}",
                "THEN Cooling": rule["then"]
            })
            
    if active_rules_data:
        df_rules = pd.DataFrame(active_rules_data)
        st.dataframe(
            df_rules,
            use_container_width=True,
            column_config={
                "Fired Strength": st.column_config.ProgressColumn(
                    "Fired Strength", min_value=0.0, max_value=1.0, format="%.3f"
                )
            },
            hide_index=True
        )
    else:
        st.warning("No rules active for the inspected state.")
