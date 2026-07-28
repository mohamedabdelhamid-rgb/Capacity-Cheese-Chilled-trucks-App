import streamlit as st
import pandas as pd
import math

# --------------------------------------------------
# Page Setup
# --------------------------------------------------
st.set_page_config(
    page_title="Breadfast Logistics Planner",
    page_icon="🚚",
    layout="wide"
)

# --------------------------------------------------
# Styling
# --------------------------------------------------
st.markdown("""
<style>
    .stApp, [data-testid="stSidebar"] {
        background-color: #FAF7FB;
    }

    .main-header {
        background-color: #AA0082;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }

    .main-header h1 {
        color: white;
        margin: 0;
    }

    .main-header p {
        color: #FFD966;
        margin-top: 5px;
    }

    div[data-testid="stMetric"] {
        background-color: white;
        border-left: 5px solid #AA0082;
        padding: 12px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🍞 Breadfast Logistics Planning</h1>
    <p>All Teams - All Categories - All Branches</p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Config
# --------------------------------------------------
RACK_FILE = "Rack Capacity.xlsx"

TEAM_SHEETS = {
    "Cheese Team": "Cheese Team",
    "Chilled Team": "Chilled Team"
}

TRUCK_CAPACITIES = {
    "Standard Chiller Truck": 70,
    "NKR Truck": 150,
    "Jumbo Chiller Truck": 300
}

# --------------------------------------------------
# Load All Sheets
# --------------------------------------------------
@st.cache_data
def load_all_data():

    all_data = []

    for sheet in TEAM_SHEETS.values():

        try:

            df = pd.read_excel(
                RACK_FILE,
                sheet_name=sheet
            )

            df.columns = df.columns.str.strip()

            for col in [
                'Destination#1',
                'Destination#2',
                'Category',
                'SKU'
            ]:

                if col in df.columns:
                    df[col] = (
                        df[col]
                        .astype(str)
                        .str.strip()
                    )

            df["Team"] = sheet

            all_data.append(df)

        except Exception as e:
            st.error(f"Error loading {sheet}: {e}")

    return pd.concat(
        all_data,
        ignore_index=True
    )

rack_df = load_all_data()

# --------------------------------------------------
# Sidebar
# --------------------------------------------------
st.sidebar.header("⚙️ Trip Settings")

dest1 = rack_df["Destination#1"].dropna().unique().tolist()
dest2 = rack_df["Destination#2"].dropna().unique().tolist()

all_branches = sorted(
    list(
        set(dest1 + dest2)
    )
)

selected_branches = st.sidebar.multiselect(
    "Select Branch(es)",
    options=all_branches,
    default=all_branches
)

selected_truck_type = st.sidebar.selectbox(
    "Truck Type",
    list(TRUCK_CAPACITIES.keys())
)

truck_capacity = TRUCK_CAPACITIES[selected_truck_type]

st.sidebar.markdown(
    f"### Capacity: {truck_capacity} Racks"
)

# --------------------------------------------------
# Filter Branches
# --------------------------------------------------
condition = pd.Series(
    False,
    index=rack_df.index
)

condition |= rack_df["Destination#1"].isin(selected_branches)
condition |= rack_df["Destination#2"].isin(selected_branches)

filtered_df = rack_df[condition].copy()

# --------------------------------------------------
# Header
# --------------------------------------------------
st.markdown("## 🧑‍🤝‍🧑 All Teams")

st.markdown(
    f"### 📍 Selected Branches: {len(selected_branches)}"
)

input_records = []

# --------------------------------------------------
# Display Teams / Categories / Products
# --------------------------------------------------
teams = filtered_df["Team"].unique()

for team in teams:

    team_df = filtered_df[
        filtered_df["Team"] == team
    ]

    st.markdown(f"## 🚚 {team}")

    categories = (
        team_df["Category"]
        .dropna()
        .unique()
    )

    for cat in categories:

        cat_df = team_df[
            team_df["Category"] == cat
        ]

        with st.expander(
            f"📂 {cat} ({len(cat_df)} Products)",
            expanded=False
        ):

            col1, col2 = st.columns(2)

            for idx, row in cat_df.reset_index(drop=True).iterrows():

                sku = row["SKU"]

                units_per_rack = row.get(
                    "Item per container",
                    1
                )

                with col1 if idx % 2 == 0 else col2:

                    qty = st.number_input(
                        f"{sku} (Units/Rack: {units_per_rack})",
                        min_value=0,
                        value=0,
                        step=10,
                        key=f"{team}_{cat}_{idx}"
                    )

                    if qty > 0:

                        racks = (
                            qty / units_per_rack
                            if units_per_rack > 0
                            else 0
                        )

                        input_records.append({
                            "Team": team,
                            "Category": cat,
                            "SKU": sku,
                            "Demand (Units)": qty,
                            "Units/Rack": units_per_rack,
                            "Calculated Racks": racks
                        })

# --------------------------------------------------
# Summary
# --------------------------------------------------
if input_records:

    summary_df = pd.DataFrame(
        input_records
    )

    total_racks = summary_df[
        "Calculated Racks"
    ].sum()

    trucks_needed = math.ceil(
        total_racks / truck_capacity
    )

    fill_pct = (
        total_racks /
        (trucks_needed * truck_capacity)
        * 100
    )

    st.markdown("---")
    st.markdown("## 🚛 Fleet Summary")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Racks",
        f"{total_racks:.2f}"
    )

    c2.metric(
        "Truck Capacity",
        truck_capacity
    )

    c3.metric(
        "Required Trucks",
        trucks_needed
    )

    c4.metric(
        "Fill %",
        f"{fill_pct:.1f}%"
    )

    st.dataframe(
        summary_df,
        use_container_width=True
    )

else:

    st.info(
        "Enter quantities for products to calculate racks and trucks."
    )
