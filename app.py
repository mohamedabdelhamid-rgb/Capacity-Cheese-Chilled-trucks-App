import streamlit as st
import pandas as pd
import math

# إعدادات الصفحة
st.set_page_config(
    page_title="Breadfast - Truck Capacity Calculator",
    page_icon="📦",
    layout="wide"
)

# Breadfast Custom Styling (CSS)
st.markdown("""
<style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #F9F9FB;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Header Styling */
    .main-header {
        background-color: #AA0082;
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-weight: 700;
    }
    .main-header p {
        color: #FFC107;
        margin-top: 5px;
        font-weight: 500;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: white;
        border-left: 5px solid #AA0082;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label {
        color: #555555 !important;
        font-weight: 600;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #AA0082 !important;
        font-weight: bold;
    }

    /* Buttons */
    .stButton>button {
        background-color: #AA0082;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #880068;
        color: #FFC107;
    }

    /* Section Subheaders */
    .css-10trblm, .stSubheader {
        color: #AA0082 !important;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="main-header">
    <h1>🍞 Breadfast Logistics Planning</h1>
    <p>Automated Fleet Distribution & Truck Capacity Calculator</p>
</div>
""", unsafe_allow_html=True)

# File Loaders & Constants
RACK_FILE = "Rack Capacity.xlsx"
TRUCK_CAPACITIES = {
    "Standard": 70,
    "NKR": 150,
    "Jumbo": 200
}

@st.cache_data
def load_rack_data():
    try:
        df = pd.read_excel(RACK_FILE)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading '{RACK_FILE}': {e}")
        return None

rack_df = load_rack_data()

if rack_df is not None:
    # Extract unique branches dynamically from Destination#1 and Destination#2
    dest1 = rack_df['Destination#1'].dropna().unique() if 'Destination#1' in rack_df.columns else []
    dest2 = rack_df['Destination#2'].dropna().unique() if 'Destination#2' in rack_df.columns else []
    all_branches = sorted(list(set(dest1).union(set(dest2))))

    # Sidebar Options
    st.sidebar.header("⚙️ Dispatch Settings")
    selected_branch = st.sidebar.selectbox("Select Target Branch", all_branches)
    
    st.subheader(f"📊 Planning for Branch: {selected_branch}")
    
    # Filter SKUs for the selected branch
    branch_skus = rack_df[
        (rack_df['Destination#1'] == selected_branch) | 
        (rack_df['Destination#2'] == selected_branch)
    ].copy()

    if branch_skus.empty:
        st.warning(f"No SKUs mapped for branch: {selected_branch}")
    else:
        st.write("### Input Demand Quantities")
        
        # User input for quantities per SKU
        input_data = []
        col1, col2 = st.columns(2)
        
        for idx, row in branch_skus.reset_index(drop=True).iterrows():
            sku_name = row.get('SKU', f"Item {idx+1}")
            category = row.get('Category', 'N/A')
            items_per_container = row.get('Item per container', 1)
            truck_type = row.get('Truck Type', 'Standard')
            
            # Divide inputs across two columns for clean UX
            with col1 if idx % 2 == 0 else col2:
                qty = st.number_input(
                    f"{sku_name} ({category}) - Units per Container: {items_per_container}",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"sku_{idx}"
                )
                
                if qty > 0:
                    racks_needed = qty / items_per_container if items_per_container > 0 else 0
                    input_data.append({
                        'SKU': sku_name,
                        'Category': category,
                        'Quantity': qty,
                        'Items/Container': items_per_container,
                        'Racks Needed': racks_needed,
                        'Truck Type': truck_type
                    })

        if input_data:
            summary_df = pd.DataFrame(input_data)
            
            st.markdown("---")
            st.subheader("🚛 Fleet Calculation Summary")
            
            total_racks = summary_df['Racks Needed'].sum()
            
            # Truck assignment based on Truck Type column or default Standard
            assigned_truck_type = summary_df['Truck Type'].iloc[0] if 'Truck Type' in summary_df.columns else "Standard"
            truck_capacity = TRUCK_CAPACITIES.get(assigned_truck_type, 70)
            
            trucks_required = math.ceil(total_racks / truck_capacity) if truck_capacity > 0 else 0
            fill_percentage = (total_racks / (trucks_required * truck_capacity) * 100) if trucks_required > 0 else 0
            
            # Display Key Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Racks Required", f"{total_racks:.2f}")
            m2.metric("Assigned Truck Type", assigned_truck_type)
            m3.metric("Trucks Needed", f"{trucks_required}")
            m4.metric("Capacity Fill %", f"{fill_percentage:.1f}%")

            st.write("### Detailed Breakdown")
            st.dataframe(summary_df, use_container_width=True)
        else:
            st.info("Enter demand quantities above to calculate rack requirements and truck distribution.")
else:
    st.error("Please ensure 'Rack Capacity.xlsx' is uploaded to the root directory of your GitHub repository.")
