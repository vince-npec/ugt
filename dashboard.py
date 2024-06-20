import streamlit as st
import pandas as pd
import plotly.express as px
import zipfile

# Set page configuration
st.set_page_config(layout="wide")

# Function to load multiple CSV files into a single DataFrame
def load_data(uploaded_files):
    data_frames = []
    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file, delimiter=';')
            # Infer device name from the filename
            df['device'] = uploaded_file.name.split('_')[0]  # Modify this line as needed
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
                        df['device'] = filename.split('/')[0].split('_')[0]  # Modify this line as needed
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

# Get all column names for selection
all_columns = data.columns.tolist()
if 'timestamp' in all_columns: all_columns.remove('timestamp')
if 'device' in all_columns: all_columns.remove('device')

# Get unique devices
devices = data['device'].unique()

# Streamlit layout
st.title('Sensor Data Dashboard')

selected_devices = st.multiselect('Select Devices', devices, default=devices.tolist())
selected_parameters = st.multiselect('Select Parameters', all_columns, default=all_columns[:1])

start_date, end_date = st.date_input('Select Date Range', [data['timestamp'].min(), data['timestamp'].max()])

filtered_data = data[(data['device'].isin(selected_devices)) & (data['timestamp'] >= pd.to_datetime(start_date)) & (data['timestamp'] <= pd.to_datetime(end_date))]

if selected_parameters and not filtered_data.empty:
    fig = px.line()
    for parameter in selected_parameters:
        for device in selected_devices:
            device_data = filtered_data[filtered_data['device'] == device]
            fig.add_scatter(x=device_data['timestamp'], y=device_data[parameter], mode='lines', name=f'{device} - {parameter}', connectgaps=False)
    fig.update_layout(title='Time Series Comparison', xaxis_title='Timestamp', yaxis_title='Values', width=1200, height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    # Display the filtered data as a table below the plot
    st.subheader('Raw Data')
    st.dataframe(filtered_data)
else:
    st.write("No data available for the selected parameters and date range.")
