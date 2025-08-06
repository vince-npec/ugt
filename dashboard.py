import streamlit as st
import pandas as pd
import plotly.express as px
import zipfile
import re

# Set page configuration
st.set_page_config(layout="wide")

# ──────────────────────────────
# Header with logos and custom title
# ──────────────────────────────
st.markdown("""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
        <img src="https://raw.githubusercontent.com/vince-npec/ugt/main/Module-1-icon.png" width="104"/>
        <h1 style="text-align: center; color: white; flex-grow: 1; margin: 0; font-size: 2.6rem; font-weight: 400;">
            Visualization Dashboard | <b style="font-weight:700;">NPEC Ecotrons</b>
        </h1>
        <img src="https://raw.githubusercontent.com/vince-npec/ugt/main/NPEC-dashboard-logo.png" width="80"/>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

# ──────────────────────────────
# Room assignment mapping
# ──────────────────────────────
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

# ──────────────────────────────
# Load multiple CSVs
# ──────────────────────────────
def load_data(uploaded_files, max_rows=MAX_ROWS):
    data_frames = []
    total_rows = 0
    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file, delimiter=';')
            device_name = uploaded_file.name.split('_')[0]
            if device_name == "Fire":
                device_name = "Fire bug"
            elif device_name == "Stag":
                device_name = "Stag beetle"
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

# ──────────────────────────────
# Load from ZIP
# ──────────────────────────────
def load_data_from_zip(zip_file, max_rows=MAX_ROWS):
    data_frames = []
    total_rows = 0
    with zipfile.ZipFile(zip_file) as z:
        for filename in z.namelist():
            if filename.endswith('.csv') and not filename.startswith('__MACOSX/'):
                with z.open(filename) as f:
                    try:
                        df = pd.read_csv(f, delimiter=';')
                        device_name = filename.split('/')[0].split('_')[0]
                        if device_name == "Fire":
                            device_name = "Fire bug"
                        elif device_name == "Stag":
                            device_name = "Stag beetle"
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

# ──────────────────────────────
# Upload widgets, with file size warning for ZIP
# ──────────────────────────────
st.title('Upload CSV or ZIP files')
uploaded_files = st.file_uploader("Upload CSV files", accept_multiple_files=True, type="csv")
uploaded_zip = st.file_uploader("Upload a ZIP file containing CSV files", type="zip")

if uploaded_zip and hasattr(uploaded_zip, "size") and uploaded_zip.size > 50_000_000:
    st.warning("Uploaded ZIP is quite large; this may take a while or could crash the dashboard.")

data = pd.DataFrame()

# Load data
if uploaded_files:
    data = load_data(uploaded_files)
elif uploaded_zip:
    data = load_data_from_zip(uploaded_zip)
else:
    st.stop()

if data.empty:
    st.stop()

# ──────────────────────────────
# Timestamp handling
# ──────────────────────────────
try:
    data['timestamp'] = pd.to_datetime(data['timestamp'], format='%d.%m.%Y %H:%M:%S')
except Exception as e:
    st.error(f"Error converting timestamp: {e}")
    st.stop()

# ──────────────────────────────
# User can choose sampling frequency
# ──────────────────────────────
sampling_options = {
    "Raw (10 min)": "10T",
    "30 min": "30T",
    "Hourly": "1H",
    "Daily": "1D"
}
selected_freq_label = st.selectbox("Select Data Frequency (downsampling)", list(sampling_options.keys()), index=0)
selected_freq = sampling_options[selected_freq_label]

def resample_data(df, freq):
    if freq == "10T":
        return df

    numeric_cols = df.select_dtypes(include='number').columns
    if 'timestamp' not in df.columns:
        return df

    resampled_frames = []
    for (device, room), group in df.groupby(['device', 'room']):
        group = group.set_index('timestamp').sort_index()
        resampled = group[numeric_cols].resample(freq).mean()
        resampled['device'] = device
        resampled['room'] = room
        resampled = resampled.reset_index()
        resampled_frames.append(resampled)
    if resampled_frames:
        return pd.concat(resampled_frames, ignore_index=True)
    else:
        return df

data = resample_data(data, selected_freq)

# ──────────────────────────────
# Interpolate numeric columns only
# ──────────────────────────────
numeric_cols = data.select_dtypes(include='number').columns
data[numeric_cols] = data[numeric_cols].interpolate().ffill().bfill()

# Reorder columns
columns = ['device', 'room'] + [col for col in data.columns if col not in ['device', 'room']]
data = data[columns]

# ──────────────────────────────
# Dynamic parameter detection (not hardcoded)
# ──────────────────────────────
def looks_like_data_point(col):
    try:
        float(str(col))  # is a number (including -1500.00, 793.03.1, etc.)
        return True
    except:
        pass
    # Timestamp-like (e.g., '31.07.2025 00:10:00')
    if re.match(r'^\d{2}\.\d{2}\.\d{4}', str(col)):
        return True
    # Optionally: filter very short columns (often spurious), e.g., 1-char or 2-char
    if len(str(col)) < 3:
        return True
    return False

all_columns = [
    col for col in data.columns
    if col not in ['timestamp', 'device', 'room'] and not looks_like_data_point(col)
]

devices = data['device'].unique()
device_options = ['All'] + devices.tolist()
rooms = data['room'].unique()
room_options = ['All'] + rooms.tolist()

# Optional: Smart guess at "standard" parameters (not used for filtering)
standard_parameters = [
    'Atmosphere temperature (°C)', 'Atmosphere humidity (% RH)',
    'FRT tension 1 (kPa)', 'FRT tension 2 (kPa)', 'FRT tension 3 (kPa)',
    'SMT temperature 1 (°C)', 'SMT temperature 2 (°C)', 'SMT temperature 3 (°C)',
    'SMT water content 1 (%)', 'SMT water content 2 (%)', 'SMT water content 3 (%)'
]

# ──────────────────────────────
# UI filters
# ──────────────────────────────
st.title('Sensor Data Dashboard')

selected_rooms = st.multiselect('Select Rooms', room_options, default='All')
if 'All' in selected_rooms:
    selected_rooms = rooms.tolist()

selected_devices = st.multiselect('Select Devices', device_options, default='All')
if 'All' in selected_devices:
    selected_devices = devices.tolist()

parameter_options = ['Standard Parameters'] + all_columns if all_columns else ['Standard Parameters']
selected_parameters = st.multiselect('Select Parameters', parameter_options)

if 'Standard Parameters' in selected_parameters:
    selected_parameters = [param for param in selected_parameters if param != 'Standard Parameters'] + [
        param for param in standard_parameters if param in all_columns]

try:
    start_date, end_date = st.date_input('Select Date Range', [data['timestamp'].min(), data['timestamp'].max()])
    if start_date > end_date:
        st.error("Error: End date must be after start date.")
        st.stop()
except Exception as e:
    st.error(f"Error with date input: {e}")
    st.stop()

# ──────────────────────────────
# Data filtering
# ──────────────────────────────
filtered_data = data[
    (data['room'].isin(selected_rooms)) &
    (data['device'].isin(selected_devices)) &
    (data['timestamp'] >= pd.to_datetime(start_date)) &
    (data['timestamp'] <= pd.to_datetime(end_date))
]

# ──────────────────────────────
# Plotting
# ──────────────────────────────
if selected_parameters and not filtered_data.empty:
    for parameter in selected_parameters:
        fig = px.line()
        for device in selected_devices:
            device_data = filtered_data[filtered_data['device'] == device]
            fig.add_scatter(
                x=device_data['timestamp'],
                y=device_data[parameter],
                mode='lines',
                name=f'{device} - {parameter}',
                connectgaps=False
            )
        fig.update_layout(
            title=f'Time Series Comparison for {parameter}',
            xaxis_title='Timestamp',
            yaxis_title=parameter,
            width=1200,
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader('Raw Data')
    st.dataframe(filtered_data.head(100))
    if len(filtered_data) > 100:
        st.info(f"Showing first 100 of {len(filtered_data)} rows out of {len(filtered_data)} total.")
else:
    st.write("No data available for the selected parameters and date range.")

# ──────────────────────────────
# Footer
# ──────────────────────────────
st.markdown("<hr style='margin-top:50px; margin-bottom:10px;'>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: grey; font-size: 14px;'>"
    "© 2025 NPEC Ecotron Module - Visualization Dashboard by Dr. Vinicius Lube | "
    "Phenomics Engineer Innovation Lead"
    "</p>",
    unsafe_allow_html=True
)
