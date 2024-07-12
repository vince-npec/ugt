import streamlit as st
import pandas as pd
import plotly.express as px
import zipfile

# Set page configuration
st.set_page_config(layout="wide")

# Define the mapping from device names to room assignments
room_assignments = {
    "Ulysses": "Room 1",
    "Admiral": "Room 1",
    "Scarab": "Room 1",
    "Ladybug": "Room 1",
    "Yellowjacket": "Room 1",
    "Flea": "Room 1",
    "Mosquito": "Room 1",
    "Stag beetle": "Room 1",
    "Cockroach": "Room 2",
    "Termite": "Room 2",
    "Centipede": "Room 2",
    "Fly": "Room 2",
    "Giraffe": "Room 2",
    "Tarantula": "Room 2",
    "Fire bug": "Room 2",
    "Tick": "Room 2",
    "Moth": "Room 2",
    "Millipede": "Room 2",
    "Mantis": "Room 2",
    "Dragonfly": "Room 2"
}

# Function to load multiple CSV files into a single DataFrame
def load_data(uploaded_files):
    data_frames = []
    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file, delimiter=';')
            # Infer device name from the filename
            device_name = uploaded_file.name.split('_')[0]
            df['device'] = device_name
            df['room'] = room_assignments.get(device_name, "Unknown")
            data_frames.append(df)
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
    
    if not data_frames:
        st.error("No data frames were created from the uploaded files.")
        return pd.DataFrame()
    
    combined_df = pd.concat(data_frames, ignore_index=True)
    return combined_df

# Function to load multiple CSV files from a ZIP into a single DataFrame
def load_data_from_zip(zip_file):
    data_frames = []
    with zipfile.ZipFile(zip_file) as z:
        for filename in z.namelist():
            if filename.endswith('.csv') and not filename.startswith('__MACOSX/'):
                with z.open(filename) as f:
                    try:
                        df = pd.read_csv(f, delimiter=';')
                        # Infer device name from the filename
                        device_name = filename.split('/')[0].split('_')[0]
                        df['device'] = device_name
                        df['room'] = room_assignments.get(device_name, "Unknown")
                        data_frames.append(df)
                    except Exception as e:
                        st.error(f"Error reading {filename}: {e}")
    
    if not data_frames:
        st.error("No data frames were created from the ZIP file.")
        return pd.DataFrame()
    
    combined_df = pd.concat(data_frames, ignore_index=True)
    return combined_df

# Upload CSV or ZIP files
st.title('Upload CSV or ZIP files')
uploaded_files = st.file_uploader("Upload CSV files", accept_multiple_files=True, type="csv")
uploaded_zip = st.file_uploader("Upload a ZIP file containing CSV files", type="zip")

data = pd.DataFrame()

# Load data from uploaded files
if uploaded_files:
    data = load_data(uploaded_files)
elif uploaded_zip:
    data = load_data_from_zip(uploaded_zip)

if data.empty:
    st.stop()

# Convert timestamp to datetime
try:
    data['timestamp'] = pd.to_datetime(data['timestamp'], format='%d.%m.%Y %H:%M:%S')
except Exception as e:
    st.error(f"Error converting timestamp: {e}")
    st.stop()

# Handle missing values
data = data.interpolate().ffill().bfill()

# Reorder columns to have 'device' as the first column
columns = ['device', 'room'] + [col for col in data.columns if col not in ['device', 'room']]
data = data[columns]

# Get all column names for selection
all_columns = data.columns.tolist()
if 'timestamp' in all_columns: all_columns.remove('timestamp')
if 'device' in all_columns: all_columns.remove('device')
if 'room' in all_columns: all_columns.remove('room')

# Define 'Mariana' parameters
mariana_parameters = [
    'Atmosphere temperature (°C)', 'Atmosphere humidity (% RH)', 
    'FRT tension 1 (kPa)', 'FRT tension 2 (kPa)', 'FRT tension 3 (kPa)', 
    'SMT temperature 1 (°C)', 'SMT temperature 2 (°C)', 'SMT temperature 3 (°C)', 
    'SMT water content 1 (%)', 'SMT water content 2 (%)', 'SMT water content 3 (%)'
]

# Get unique devices and rooms
devices = data['device'].unique()
device_options = ['All'] + devices.tolist()
rooms = data['room'].unique()
room_options = ['All'] + rooms.tolist()

# Streamlit layout
st.title('Sensor Data Dashboard')

# Room selection
selected_rooms = st.multiselect('Select Rooms', room_options, default='All')
if 'All' in selected_rooms:
    selected_rooms = rooms.tolist()

# Device selection
selected_devices = st.multiselect('Select Devices', device_options, default='All')
if 'All' in selected_devices:
    selected_devices = devices.tolist()

parameter_options = ['Mariana'] + all_columns
selected_parameters = st.multiselect('Select Parameters', parameter_options, default=parameter_options[:1])

# Automatically select 'Mariana' parameters if 'Mariana' is chosen
if 'Mariana' in selected_parameters:
    selected_parameters = [param for param in selected_parameters if param != 'Mariana'] + [param for param in mariana_parameters if param in all_columns]

# Check if start_date and end_date are valid
try:
    start_date, end_date = st.date_input('Select Date Range', [data['timestamp'].min(), data['timestamp'].max()])
    if start_date > end_date:
        st.error("Error: End date must be after start date.")
        st.stop()
except Exception as e:
    st.error(f"Error with date input: {e}")
    st.stop()

# Filter data by selected rooms, devices, and date range
filtered_data = data[(data['room'].isin(selected_rooms)) & (data['device'].isin(selected_devices)) & (data['timestamp'] >= pd.to_datetime(start_date)) & (data['timestamp'] <= pd.to_datetime(end_date))]

if selected_parameters and not filtered_data.empty:
    for parameter in selected_parameters:
        fig = px.line()
        for device in selected_devices:
            device_data = filtered_data[filtered_data['device'] == device]
            fig.add_scatter(x=device_data['timestamp'], y=device_data[parameter], mode='lines', name=f'{device} - {parameter}', connectgaps=False)
        fig.update_layout(title=f'Time Series Comparison for {parameter}', xaxis_title='Timestamp', yaxis_title=parameter, width=1200, height=600)
        st.plotly_chart(fig, use_container_width=True)
    
    # Display the filtered data as a table below the plots
    st.subheader('Raw Data')
    st.dataframe(filtered_data)
else:
    st.write("No data available for the selected parameters and date range.")
