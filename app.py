import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(
    page_title="Breadfast - Logistics Planning",
    page_icon="📦",
    layout="wide"
)

# Custom Styling (Light Theme & Breadfast Colors - Fixes Black Text/Sidebar)
st.markdown("""
<style>
    /* Force Light Background Globally */
    .stApp, [data-testid="stSidebar"] {
        background-color: #F8F9FA !important;
        color: #111111 !important;
    }

    /* Fix Text Visibility in Main Area & Sidebar */
    p, span, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div {
        color: #111111 !important;
    }

    /* Header Styling */
    .main-header {
        background-color: #AA0082 !important;
        padding: 22px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.12);
    }
    .main-header h1 {
        color: #FFFFFF !important;
        margin: 0;
        font-weight: 800;
        font-size: 2rem;
    }
    .main-header p {
        color: #FFC107 !important;
        margin-top: 6px;
        font-weight: 600;
        font-size: 1rem;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border-left: 6px solid #AA0082 !important;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetric"] label {
        color: #555555 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #AA0082 !important;
        font-weight: bold !important;
    }

    /* Fix Inputs Background and Text */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border: 1px solid #AA0082 !important;
        border-radius: 6px !important;
    }
    input {
        color: #111111 !important;
        background-color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="main-header">
    <h1>🍞 Breadfast Logistics Planning</h1>
    <p>Automated Fleet Capacity & SKU Demand Distribution</p>
</div>
""", unsafe_allow_html=True)

# Constants & Data Loader
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
    # Get all dynamic branches
    dest1 = rack_df['Destination#1'].dropna().unique() if 'Destination#1' in rack_df.columns else []
    dest2 = rack_df['Destination#2'].dropna().unique() if 'Destination#2' in rack_df.columns else []
    all_branches = sorted(list(set(dest1).union(set(dest2))))

    # Sidebar Options
    st.sidebar.header("⚙️ Dispatch Configuration")
    selected_branch = st.sidebar.selectbox("Select Target Branch", all_branches)

    # Filter SKUs belonging to the selected branch
    branch_skus = rack_df[
        (rack_df['Destination#1'] == selected_branch) | 
        (rack_df['Destination#2'] == selected_branch)
    ].copy()

    # Determine Truck Type from dataset
    detected_truck_type = "Standard"
    if not branch_skus.empty and 'Truck Type' in branch_skus.columns:
        detected_truck_type = branch_skus['Truck Type'].iloc[0]

    selected_truck_type = st.sidebar.selectbox(
        "Truck Type", 
        list(TRUCK_CAPACITIES.keys()), 
        index=list(TRUCK_CAPACITIES.keys()).index(detected_truck_type) if detected_truck_type in TRUCK_CAPACITIES else 0
    )

    truck_max_capacity = TRUCK_CAPACITIES[selected_truck_type]

    st.markdown(f"### 📍 Target Branch: **{selected_branch}**")

    if branch_skus.empty:
        st.warning(f"No mapped SKUs found for branch: {selected_branch}")
    else:
        st.markdown("#### 📦 Enter Demand Quantities per SKU")
        
        input_records = []
        col1, col2 = st.columns(2)

        # Loop through SKUs mapped to this branch
        for idx, row in branch_skus.reset_index(drop=True).iterrows():
            sku_name = row.get('SKU', f"Item #{idx+1}")
            category = row.get('Category', 'N/A')
            units_per_container = row.get('Item per container', 1)
            
            with col1 if idx % 2 == 0 else col2:
                demand_qty = st.number_input(
                    f"**{sku_name}** ({category}) - Units/Rack: {units_per_container}",
                    min_value=0,
                    value=0,
                    step=10,
                    key=f"sku_input_{idx}"
                )

                if demand_qty > 0:
                    racks_needed = demand_qty / units_per_container if units_per_container > 0 else 0
                    input_records.append({
                        "SKU": sku_name,
                        "Category": category,
                        "Demand (Units)": demand_qty,
                        "Units/Rack": units_per_container,
                        "Calculated Racks": racks_needed
                    })

        # Calculations & Analytics
        if input_records:
            summary_df = pd.DataFrame(input_records)
            total_racks = summary_df['Calculated Racks'].sum()
            
            trucks_needed = math.ceil(total_racks / truck_max_capacity) if truck_max_capacity > 0 else 0
            overall_fill_pct = (total_racks / (trucks_needed * truck_max_capacity) * 100) if trucks_needed > 0 else 0

            # Calculate individual SKU contribution to truck capacity
            summary_df['Truck Fill Contribution %'] = summary_df['Calculated Racks'].apply(
                lambda r: f"{(r / truck_max_capacity * 100):.1f}%"
            )

            st.markdown("---")
            st.markdown("### 🚛 Fleet Capacity Summary")

            # Dashboard Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Racks Demand", f"{total_racks:.2f}")
            m2.metric("Truck Type & Capacity", f"{selected_truck_type} ({truck_max_capacity} Racks)")
            m3.metric("Required Trucks", f"{trucks_needed}")
            m4.metric("Fleet Fill %", f"{overall_fill_pct:.1f}%")

            st.markdown("#### 📋 Order Breakdown by SKU")
            st.dataframe(summary_df, use_container_width=True)

            # Capacity Alerts
            if overall_fill_pct >= 85 and overall_fill_pct <= 100:
                st.success(f"✅ Optimal truck utilization! Fleet is filled at **{overall_fill_pct:.1f}%**.")
            elif overall_fill_pct > 100:
                st.error(f"⚠️ Demand exceeds single truck capacity! Need **{trucks_needed} trucks**.")
            else:
                st.warning(f"⚠️ Truck capacity is underutilized (**{overall_fill_pct:.1f}%** fill rate).")
        else:
            st.info("Enter quantities for the SKUs above to calculate total racks and truck fill percentage.")
else:
    st.error("Please ensure 'Rack Capacity.xlsx' is uploaded in your GitHub repository.")
