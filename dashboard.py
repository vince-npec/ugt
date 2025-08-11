import streamlit as st
import pandas as pd
import plotly.express as px
import zipfile
import re
from typing import List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Visualization Dashboard | NPEC Ecotrons", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# DEVICE DIRECTORY (SIDEBAR)
# ─────────────────────────────────────────────────────────────────────────────
DEVICES: List[Tuple[str, str]] = [
    ("Ulysses", "http://192.168.162.8/visu/#/main"),
    ("Admiral", "http://192.168.162.9/visu/#/main"),
    ("Scarab", "http://192.168.162.10/visu/#/main"),
    ("Ladybug", "http://192.168.162.11/visu/#/main"),
    ("Stag beetle", "http://192.168.162.12/visu/#/main"),
    ("Mosquito", "http://192.168.162.13/visu/#/main"),
    ("Flea", "http://192.168.162.14/visu/#/main"),
    ("Yellowjacket", "http://192.168.162.15/visu/#/main"),
    ("Dragonfly", "http://192.168.162.16/visu/#/main"),
    ("Moth", "http://192.168.162.17/visu/#/main"),
    ("Cockroach", "http://192.168.162.18/visu/#/main"),
    ("Fly", "http://192.168.162.19/visu/#/main"),
    ("Mantis", "http://192.168.162.20/visu/#/main"),
    ("Tick", "http://192.168.162.21/visu/#/main"),
    ("Termite", "http://192.168.162.22/visu/#/main"),
    ("Giraffe", "http://192.168.162.23/visu/#/main"),
    ("Millipede", "http://192.168.162.24/visu/#/main"),
    ("Fire bug", "http://192.168.162.25/visu/#/main"),
    ("Centipede", "http://192.168.162.26/visu/#/main"),
    ("Tarantula", "http://192.168.162.27/visu/#/main"),
    ("Dung beetle", "http://192.168.162.28/visu/#/main"),
    ("Ant", "http://192.168.162.29/visu/#/main"),
    ("Hornet", "http://192.168.162.30/visu/#/main"),
    ("Maybug", "http://192.168.162.31/visu/#/main"),
    ("Bumblebee", "http://192.168.162.32/visu/#/main"),
    ("Honeybee", "http://192.168.162.33/visu/#/main"),
    ("Stink", "http://192.168.162.34/visu/#/main"),
    ("Hercules", "http://192.168.162.35/visu/#/main"),
    ("Strider", "http://192.168.162.36/visu/#/main"),
    ("Stick", "http://192.168.162.37/visu/#/main"),
    ("Longhorn", "http://192.168.162.38/visu/#/main"),
    ("Weaver", "http://192.168.162.39/visu/#/main"),
    ("Scorpion", "http://192.168.162.40/visu/#/main"),
    ("Caterpillar", "http://192.168.162.41/visu/#/main"),
    ("Potato beetle", "http://192.168.162.42/visu/#/main"),
    ("Cricket", "http://192.168.162.43/visu/#/main"),
]

EMOJI = {
    "Ulysses":"🦋","Admiral":"🦋","Scarab":"🪲","Ladybug":"🐞","Stag beetle":"🪲",
    "Mosquito":"🦟","Flea":"🪳","Yellowjacket":"🐝","Dragonfly":"🐉","Moth":"🦋",
    "Cockroach":"🪳","Fly":"🪰","Mantis":"🦗","Tick":"🕷️","Termite":"🐜","Giraffe":"🦒",
    "Millipede":"🪱","Fire bug":"🔥","Centipede":"🪱","Tarantula":"🕷️","Dung beetle":"🪲",
    "Ant":"🐜","Hornet":"🐝","Maybug":"🪲","Bumblebee":"🐝","Honeybee":"🐝","Stink":"💨",
    "Hercules":"💪","Strider":"🚶","Stick":"🪵","Longhorn":"🐂","Weaver":"🧵","Scorpion":"🦂",
    "Caterpillar":"🐛","Potato beetle":"🥔🪲","Cricket":"🦗",
}

# Room/type (from your table)
META = {
    "ulysses":("Ecolab 1","Advanced"), "admiral":("Ecolab 1","Advanced"), "scarab":("Ecolab 1","Advanced"),
    "ladybug":("Ecolab 1","Advanced"), "yellowjacket":("Ecolab 1","Advanced"), "flea":("Ecolab 1","Advanced"),
    "mosquito":("Ecolab 1","Advanced"), "stagbeetle":("Ecolab 1","Advanced"),
    "dragonfly":("Ecolab 2","Basic"), "moth":("Ecolab 2","Basic"), "cockroach":("Ecolab 2","Basic"),
    "fly":("Ecolab 2","Basic"), "mantis":("Ecolab 2","Basic"), "tick":("Ecolab 2","Basic"),
    "termite":("Ecolab 2","Basic"), "giraffe":("Ecolab 2","Basic"), "millipede":("Ecolab 2","Basic"),
    "firebug":("Ecolab 2","Basic"), "centipede":("Ecolab 2","Basic"), "tarantula":("Ecolab 2","Basic"),
    "dungbeetle":("Ecolab 3","Basic"), "ant":("Ecolab 3","Basic"), "hornet":("Ecolab 3","Basic"),
    "maybug":("Ecolab 3","Basic"), "bumblebee":("Ecolab 3","Basic"), "honeybee":("Ecolab 3","Basic"),
    "stink":("Ecolab 3","Basic"), "hercules":("Ecolab 3","Basic"), "strider":("Ecolab 3","Basic"),
    "stick":("Ecolab 3","Basic"), "longhorn":("Ecolab 3","Basic"),
    "weaver":("Ecolab 3","Basic"), "scorpion":("Ecolab 3","Basic"),
    "caterpillar":("Ecolab 3","Basic"), "potatobeetle":("Ecolab 3","Basic"), "cricket":("Ecolab 3","Basic"),
}
def meta_for(name: str):
    return META.get(name.lower().replace(" ", ""), ("Ecolab 3", "Basic"))

def ip_from(url: str) -> str:
    try:
        return url.split("//",1)[1].split("/",1)[0]
    except Exception:
        return url

# Sidebar directory (collapsible in Streamlit UI)
st.sidebar.title("Devices")
q = st.sidebar.text_input("Filter by name or IP", value="")
room_filter = st.sidebar.selectbox("Room", ["All","Ecolab 1","Ecolab 2","Ecolab 3"])

# Group & render
rooms_order = ["Ecolab 1","Ecolab 2","Ecolab 3"] if room_filter=="All" else [room_filter]
for room_name in rooms_order:
    with st.sidebar.expander(room_name, expanded=True):
        for name, url in DEVICES:
            room, typ = meta_for(name)
            if room_name != room and room_filter != "All":
                continue
            if q and (q.lower() not in name.lower() and q.lower() not in ip_from(url)):
                continue
            emoji = EMOJI.get(name, "🔗")
            st.markdown(
                f"**{emoji} {name}**  \n"
                f"`{ip_from(url)}` • *{typ}*  \n"
                f"[Open ↗]({url})",
                help=f"{room} • {typ}"
            )

st.sidebar.markdown("---")
st.sidebar.caption("Tip: collapse the sidebar with the chevron (>) to give charts more room.")

# ─────────────────────────────────────────────────────────────────────────────
# HEADER WITH LOGOS + TITLE (NPEC logo smaller)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
        <img src="https://raw.githubusercontent.com/vince-npec/ugt/main/Module-1-icon.png"
             alt="Ecotron Module"
             style="height: 189px; width: auto;" />
        <h1 style="text-align: center; color: white; flex-grow: 1; margin: 0; font-size: 2.6rem; font-weight: 400;">
            Visualization Dashboard | <b style="font-weight:700;">NPEC Ecotrons</b>
        </h1>
        <img src="https://raw.githubusercontent.com/vince-npec/ugt/main/NPEC-dashboard-logo.png"
             alt="NPEC"
             style="height: 189px; width: auto;" />
    </div>
""", unsafe_allow_html=True)
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS (your stable code, unchanged)
# ─────────────────────────────────────────────────────────────────────────────
room_assignments = {
    "Ulysses": "Room 1", "Admiral": "Room 1", "Scarab": "Room 1",
    "Ladybug": "Room 1", "Yellowjacket": "Room 1", "Flea": "Room 1",
    "Mosquito": "Room 1", "Stag beetle": "Room 1", "Stag_Bettle": "Room 1",
    "Cockroach": "Room 2", "Termite": "Room 2", "Centipede": "Room 2",
    "Fly": "Room 2", "Giraffe": "Room 2", "Tarantula": "Room 2",
    "Fire bug": "Room 2", "Fire_Bug": "Room 2", "Tick": "Room 2",
    "Moth": "Room 2", "Millipede": "Room 2", "Mantis": "Room 2", "Dragonfly": "Room 2"
}
MAX_ROWS = 50000

def load_data(uploaded_files, max_rows=MAX_ROWS):
    data_frames, total_rows = [], 0
    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file, delimiter=';')
            device_name = uploaded_file.name.split('_')[0]
            if device_name == "Fire": device_name = "Fire bug"
            elif device_name == "Stag": device_name = "Stag beetle"
            df['device'] = device_name
            df['room'] = room_assignments.get(device_name, "Unknown")
            if not df.empty:
                if total_rows + len(df) > max_rows:
                    df = df.iloc[:max_rows - total_rows]
                data_frames.append(df)
                total_rows += len(df)
                if total_rows >= max_rows:
                    st.warning(f"Loaded {max_rows} rows (limit reached for performance).")
                    break
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
    if not data_frames:
        st.error("No data frames were created from the uploaded files.")
        return pd.DataFrame()
    return pd.concat(data_frames, ignore_index=True)

def load_data_from_zip(zip_file, max_rows=MAX_ROWS):
    data_frames, total_rows = [], 0
    with zipfile.ZipFile(zip_file) as z:
        for filename in z.namelist():
            if filename.endswith('.csv') and not filename.startswith('__MACOSX/'):
                with z.open(filename) as f:
                    try:
                        df = pd.read_csv(f, delimiter=';')
                        device_name = filename.split('/')[0].split('_')[0]
                        if device_name == "Fire": device_name = "Fire bug"
                        elif device_name == "Stag": device_name = "Stag beetle"
                        df['device'] = device_name
                        df['room'] = room_assignments.get(device_name, "Unknown")
                        if not df.empty:
                            if total_rows + len(df) > max_rows:
                                df = df.iloc[:max_rows - total_rows]
                            data_frames.append(df)
                            total_rows += len(df)
                            if total_rows >= max_rows:
                                st.warning(f"Loaded {max_rows} rows (limit reached for performance).")
                                break
                    except Exception as e:
                        st.error(f"Error reading {filename}: {e}")
    if not data_frames:
        st.error("No data frames were created from the ZIP file.")
        return pd.DataFrame()
    return pd.concat(data_frames, ignore_index=True)

st.title('Upload CSV or ZIP files')
uploaded_files = st.file_uploader("Upload CSV files", accept_multiple_files=True, type="csv")
uploaded_zip = st.file_uploader("Upload a ZIP file containing CSV files", type="zip")
if uploaded_zip and hasattr(uploaded_zip, "size") and uploaded_zip.size > 50_000_000:
    st.warning("Uploaded ZIP is quite large; this may take a while or could crash the dashboard.")

data = pd.DataFrame()
if uploaded_files:
    data = load_data(uploaded_files)
elif uploaded_zip:
    data = load_data_from_zip(uploaded_zip)
else:
    st.stop()

if data.empty:
    st.stop()

try:
    data['timestamp'] = pd.to_datetime(data['timestamp'], format='%d.%m.%Y %H:%M:%S')
except Exception as e:
    st.error(f"Error converting timestamp: {e}")
    st.stop()

sampling_options = {"Raw (10 min)": "10T", "30 min": "30T", "Hourly": "1H", "Daily": "1D"}
selected_freq_label = st.selectbox("Select Data Frequency (downsampling)", list(sampling_options.keys()), index=0)
selected_freq = sampling_options[selected_freq_label]

def resample_data(df, freq):
    if freq == "10T": return df
    numeric_cols = df.select_dtypes(include='number').columns
    if 'timestamp' not in df.columns: return df
    frames = []
    for (device, room), group in df.groupby(['device', 'room']):
        group = group.set_index('timestamp').sort_index()
        resampled = group[numeric_cols].resample(freq).mean()
        resampled['device'] = device
        resampled['room'] = room
        frames.append(resampled.reset_index())
    return pd.concat(frames, ignore_index=True) if frames else df

data = resample_data(data, selected_freq)

numeric_cols = data.select_dtypes(include='number').columns
data[numeric_cols] = data[numeric_cols].interpolate().ffill().bfill()

columns = ['device', 'room'] + [c for c in data.columns if c not in ['device', 'room']]
data = data[columns]

def looks_like_data_point(col):
    try:
        float(str(col)); return True
    except: pass
    if re.match(r'^\d{2}\.\d{2}\.\d{4}', str(col)): return True
    if len(str(col)) < 3: return True
    return False

all_columns = [c for c in data.columns if c not in ['timestamp','device','room'] and not looks_like_data_point(c)]

standard_parameters = [
    'Atmosphere temperature (°C)', 'Atmosphere humidity (% RH)',
    'FRT tension 1 (kPa)', 'FRT tension 2 (kPa)', 'FRT tension 3 (kPa)',
    'SMT temperature 1 (°C)', 'SMT temperature 2 (°C)', 'SMT temperature 3 (°C)',
    'SMT water content 1 (%)', 'SMT water content 2 (%)', 'SMT water content 3 (%)'
]
dcc_parameters = [
    'SMT water content 1 (%)', 'SMT water content 2 (%)', 'SMT water content 3 (%)',
    'Current Days Irrigation (L)', 'Lysimeter weight (Kg)', 'LBC tank weight (Kg)'
]

devices_list = data['device'].unique()
device_options = ['All'] + devices_list.tolist()
rooms_list = data['room'].unique()
room_options = ['All'] + rooms_list.tolist()

st.title('Sensor Data Dashboard')

selected_rooms = st.multiselect('Select Rooms', room_options, default='All')
if 'All' in selected_rooms:
    selected_rooms = rooms_list.tolist()

selected_devices = st.multiselect('Select Devices', device_options, default='All')
if 'All' in selected_devices:
    selected_devices = devices_list.tolist()

parameter_options = ['Standard Parameters', 'DCC project'] + all_columns if all_columns else ['Standard Parameters', 'DCC project']
selected_parameters = st.multiselect('Select Parameters', parameter_options)

final_parameters, seen = [], set()
if 'Standard Parameters' in selected_parameters:
    final_parameters += [p for p in standard_parameters if p in all_columns]
if 'DCC project' in selected_parameters:
    final_parameters += [p for p in dcc_parameters if p in all_columns]
final_parameters += [p for p in selected_parameters if p not in ['Standard Parameters', 'DCC project']]
final_parameters = [x for x in final_parameters if not (x in seen or seen.add(x))]

try:
    start_date, end_date = st.date_input('Select Date Range', [data['timestamp'].min(), data['timestamp'].max()])
    if start_date > end_date:
        st.error("Error: End date must be after start date."); st.stop()
except Exception as e:
    st.error(f"Error with date input: {e}"); st.stop()

filtered_data = data[
    (data['room'].isin(selected_rooms)) &
    (data['device'].isin(selected_devices)) &
    (data['timestamp'] >= pd.to_datetime(start_date)) &
    (data['timestamp'] <= pd.to_datetime(end_date))
]

if final_parameters and not filtered_data.empty:
    for parameter in final_parameters:
        fig = px.line()
        for device in selected_devices:
            ddf = filtered_data[filtered_data['device'] == device]
            if parameter in ddf.columns:
                fig.add_scatter(x=ddf['timestamp'], y=ddf[parameter],
                                mode='lines', name=f'{device} - {parameter}', connectgaps=False)
        fig.update_layout(title=f'Time Series Comparison for {parameter}',
                          xaxis_title='Timestamp', yaxis_title=parameter, height=600)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader('Raw Data')
    st.dataframe(filtered_data.head(100))
    if len(filtered_data) > 100:
        st.info(f"Showing first 100 of {len(filtered_data)} rows out of {len(filtered_data)} total.")
else:
    st.write("No data available for the selected parameters and date range.")

st.markdown("<hr style='margin-top:50px; margin-bottom:10px;'>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: grey; font-size: 14px;'>"
    "© 2025 NPEC Ecotron Module - Visualization Dashboard by Dr. Vinicius Lube | "
    "Phenomics Engineer Innovation Lead</p>",
    unsafe_allow_html=True
)
