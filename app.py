import streamlit as st
import pandas as pd
import math

# Page Setup
st.set_page_config(
    page_title="Breadfast Logistics Planner",
    page_icon="🚚",
    layout="wide"
)

# Custom Styling - Force Light Mode & High Contrast (No Dark Theme Glitches)
st.markdown("""
<style>
    /* Force Light Background Globally */
    .stApp, [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        color: #111111 !important;
    }
    
    /* Ensure All Texts Are Clearly Visible */
    p, span, label, h1, h2, h3, h4, h5, h6, div, .stMarkdown {
        color: #111111 !important;
    }

    /* Corporate Header */
    .main-header {
        background-color: #AA0082 !important;
        padding: 22px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .main-header h1 {
        color: #FFFFFF !important;
        margin: 0;
        font-weight: 800;
        font-size: 2.2rem;
    }
    .main-header p {
        color: #FFC107 !important;
        margin-top: 6px;
        font-weight: 600;
        font-size: 1.1rem;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #F8F9FA !important;
        border-left: 5px solid #AA0082 !important;
        padding: 12px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label {
        color: #444444 !important;
        font-weight: bold !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #AA0082 !important;
        font-weight: bold !important;
    }

    /* Form Fields Styling */
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
    <p>Multi-Branch & Full Category Truck Capacity Allocator</p>
</div>
""", unsafe_allow_html=True)

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
    # Get List of All Branches across Destination columns
    dest1 = rack_df['Destination#1'].dropna().unique().tolist() if 'Destination#1' in rack_df.columns else []
    dest2 = rack_df['Destination#2'].dropna().unique().tolist() if 'Destination#2' in rack_df.columns else []
    all_branches = sorted(list(set(dest1 + dest2)))

    # Sidebar - Dispatch Settings
    st.sidebar.header("⚙️ Dispatch Settings")
    
    # 1. Select Multiple Branches for the Same Truck Route
    selected_branches = st.sidebar.multiselect(
        "Select Branch(es) for Truck Route:",
        options=all_branches,
        default=[all_branches[0]] if all_branches else []
    )

    selected_truck_type = st.sidebar.selectbox("Select Truck Type:", list(TRUCK_CAPACITIES.keys()), index=0)
    truck_max_capacity = TRUCK_CAPACITIES[selected_truck_type]

    if not selected_branches:
        st.info("Please select at least one branch from the sidebar to view products.")
    else:
        st.markdown(f"### 📍 Route Branches: **{', '.join(selected_branches)}**")

        # Filter all SKUs mapped to ANY of the selected branches
        condition = pd.Series(False, index=rack_df.index)
        if 'Destination#1' in rack_df.columns:
            condition |= rack_df['Destination#1'].isin(selected_branches)
        if 'Destination#2' in rack_df.columns:
            condition |= rack_df['Destination#2'].isin(selected_branches)
            
        filtered_df = rack_df[condition].copy()

        if filtered_df.empty:
            st.warning("No products specifically mapped to these branches. Showing all products from dataset:")
            filtered_df = rack_df.copy()

        st.markdown("#### 📦 Enter Demand Quantities (Units) per Product Category")

        # Group Products by Category
        categories = filtered_df['Category'].dropna().unique() if 'Category' in filtered_df.columns else ['All Products']
        
        input_records = []

        # Display SKUs categorized
        for cat in categories:
            cat_skus = filtered_df[filtered_df['Category'] == cat] if 'Category' in filtered_df.columns else filtered_df
            
            with st.expander(f"📂 Category: **{cat}** ({len(cat_skus)} Products)", expanded=True):
                col1, col2 = st.columns(2)
                
                for idx, row in cat_skus.reset_index(drop=True).iterrows():
                    sku_name = row.get('SKU', f"Item #{idx+1}")
                    units_per_container = row.get('Item per container', 1)
                    
                    with col1 if idx % 2 == 0 else col2:
                        demand_qty = st.number_input(
                            f"**{sku_name}** (Units/Rack: {units_per_container})",
                            min_value=0,
                            value=0,
                            step=10,
                            key=f"input_{cat}_{idx}_{sku_name}"
                        )

                        if demand_qty > 0:
                            racks_needed = demand_qty / units_per_container if units_per_container > 0 else 0
                            input_records.append({
                                "Category": cat,
                                "SKU": sku_name,
                                "Demand (Units)": demand_qty,
                                "Units/Rack": units_per_container,
                                "Calculated Racks": racks_needed
                            })

        # Calculation Output
        if input_records:
            summary_df = pd.DataFrame(input_records)
            total_racks = summary_df['Calculated Racks'].sum()
            
            trucks_needed = math.ceil(total_racks / truck_max_capacity) if truck_max_capacity > 0 else 0
            overall_fill_pct = (total_racks / (trucks_needed * truck_max_capacity) * 100) if trucks_needed > 0 else 0

            # Calculate fill % per SKU based on 1 truck capacity
            summary_df['Truck Capacity Share %'] = summary_df['Calculated Racks'].apply(
                lambda r: f"{(r / truck_max_capacity * 100):.1f}%"
            )

            st.markdown("---")
            st.markdown("### 🚛 Fleet & Truck Fill Metrics")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Racks Needed", f"{total_racks:.2f}")
            m2.metric("Truck Type & Limit", f"{selected_truck_type} ({truck_max_capacity} Racks)")
            m3.metric("Required Trucks", f"{trucks_needed}")
            m4.metric("Truck Fill %", f"{overall_fill_pct:.1f}%")

            st.markdown("#### 📋 Order & Truck Share Summary")
            st.dataframe(summary_df, use_container_width=True)

            if overall_fill_pct > 100:
                st.error(f"⚠️ Demand exceeds single truck capacity! Need **{trucks_needed} trucks**.")
            elif overall_fill_pct >= 85:
                st.success(f"✅ Optimal truck usage! Filled at **{overall_fill_pct:.1f}%**.")
            else:
                st.warning(f"⚠️ Low capacity utilization (**{overall_fill_pct:.1f}%**). Consider adding more stock.")
        else:
            st.info("Enter quantities for products above to view capacity calculation.")
else:
    st.error("File 'Rack Capacity.xlsx' not found. Please upload it to your repository.")
