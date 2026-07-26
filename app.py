import streamlit as st
import pandas as pd
import math

# إعدادات الصفحة
st.set_page_config(
    page_title="Breadfast - Fleet & Capacity Distribution",
    page_icon="🚚",
    layout="wide"
)

# Custom Styling (Breadfast Colors & Fixes)
st.markdown("""
<style>
    .stApp {
        background-color: #F9F9FB !important;
        color: #222222 !important;
    }
    p, span, label, h1, h2, h3, h4, h5, h6, div {
        color: #222222 !important;
    }
    .main-header {
        background-color: #AA0082 !important;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    .main-header h1 {
        color: #FFFFFF !important;
        margin: 0;
        font-weight: 800;
    }
    .main-header p {
        color: #FFC107 !important;
        margin-top: 5px;
        font-weight: 600;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border-left: 6px solid #AA0082 !important;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }
    div[data-testid="stMetric"] label {
        color: #555555 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #AA0082 !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="main-header">
    <h1>🍞 Breadfast Logistics Planning</h1>
    <p>Fleet Capacity & Branch Distribution Plan</p>
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
    # إستخراج قائمة الفروع المتاحة
    dest1 = rack_df['Destination#1'].dropna().unique() if 'Destination#1' in rack_df.columns else []
    dest2 = rack_df['Destination#2'].dropna().unique() if 'Destination#2' in rack_df.columns else []
    all_branches = sorted(list(set(dest1).union(set(dest2))))

    st.sidebar.header("⚙️ Dispatch Mode")
    dispatch_type = st.sidebar.radio("اختر طريقة توزيع الشحنة:", ["شاحنة مشتركة (Multi-Branch Truck)", "فرع واحد (Single Branch)"])

    st.markdown("### 📥 إدخال كميات البلان (Demand Input)")

    branch_inputs = {}
    
    if dispatch_type == "شاحنة مشتركة (Multi-Branch Truck)":
        st.info("💡 قم باختيار الفروع المربوطة ببعضها حسب خريطة التوزيع، وادخل إجمالي عدد الـ Racks المخططة لكل فرع.")
        
        col1, col2 = st.columns(2)
        with col1:
            branch_1 = st.selectbox("الفرع الأول (Destination #1):", ["-- اختر الفرع --"] + all_branches)
            if branch_1 != "-- اختر الفرع --":
                racks_b1 = st.number_input(f"عدد الـ Racks لـ ({branch_1}):", min_value=0.0, value=0.0, step=0.5, key="b1")
                branch_inputs[branch_1] = racks_b1

        with col2:
            # تصفية الفروع المقترحة للفرع الثاني بناءً على الإكسيل
            possible_dest2 = []
            if branch_1 != "-- اختر الفرع --":
                mapped_rows = rack_df[rack_df['Destination#1'] == branch_1]
                possible_dest2 = mapped_rows['Destination#2'].dropna().unique().tolist()
            
            selectable_b2 = possible_dest2 if possible_dest2 else all_branches
            branch_2 = st.selectbox("الفرع الثاني (Destination #2 - اختياري):", ["-- لا يوجد فرع ثاني --"] + selectable_b2)
            
            if branch_2 != "-- لا يوجد فرع ثاني --":
                racks_b2 = st.number_input(f"عدد الـ Racks لـ ({branch_2}):", min_value=0.0, value=0.0, step=0.5, key="b2")
                branch_inputs[branch_2] = racks_b2

    else:
        selected_branch = st.selectbox("اختر الفرع المستهدف:", all_branches)
        racks_single = st.number_input(f"إجمالي عدد الـ Racks المطلوب إرسالها لـ ({selected_branch}):", min_value=0.0, value=0.0, step=0.5)
        if racks_single > 0:
            branch_inputs[selected_branch] = racks_single

    # تحديد نوع الشاحنة المخصصة لهذه الفروع من شيت الإكسيل
    truck_type = "Standard"
    if branch_inputs:
        first_branch = list(branch_inputs.keys())[0]
        match_row = rack_df[(rack_df['Destination#1'] == first_branch) | (rack_df['Destination#2'] == first_branch)]
        if not match_row.empty and 'Truck Type' in match_row.columns:
            truck_type = match_row['Truck Type'].iloc[0]

    # خيار تعديل نوع الشاحنة لو البلان غير نوع العربية
    truck_type = st.sidebar.selectbox("نوع الشاحنة المستخدمة (Truck Type):", list(TRUCK_CAPACITIES.keys()), index=list(TRUCK_CAPACITIES.keys()).index(truck_type) if truck_type in TRUCK_CAPACITIES else 0)
    
    max_truck_cap = TRUCK_CAPACITIES[truck_type]

    # --- الحسابات والنتائج ---
    total_racks_demand = sum(branch_inputs.values())

    if total_racks_demand > 0:
        st.markdown("---")
        st.markdown("## 📊 نتائج تحليل وسعة الشاحنة (Truck Capacity Analysis)")

        trucks_needed = math.ceil(total_racks_demand / max_truck_cap)
        overall_fill_pct = (total_racks_demand / (trucks_needed * max_truck_cap)) * 100

        # الكروت الأساسية
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي الـ Racks المطلوب", f"{total_racks_demand:.1f}")
        m2.metric("نوع العربية والسعة", f"{truck_type} ({max_truck_cap} Rack)")
        m3.metric("عدد الشاحنات المطلوبة", f"{trucks_needed} عربية")
        m4.metric("نسبة تحميل الأسطول الإجمالية", f"{overall_fill_pct:.1f}%")

        st.markdown("### 🚚 توزيع حمولة الشاحنة الواحدة والنسب لكل فرع:")

        # تفاصيل الشاحنة الأولى
        breakdown_data = []
        for b_name, b_racks in branch_inputs.items():
            b_pct_of_truck = (b_racks / max_truck_cap) * 100
            b_pct_of_total_order = (b_racks / total_racks_demand) * 100
            
            breakdown_data.append({
                "اسم الفرع (Branch)": b_name,
                "عدد الـ Racks": b_racks,
                "نسبة إشغال العربية الأولى (Truck Fill %)": f"{b_pct_of_truck:.1f}%",
                "نسبته من إجمالي الطلبية": f"{b_pct_of_total_order:.1f}%"
            })

        st.table(pd.DataFrame(breakdown_data))

        # تنبيهات ذكية بناءً على نسبة التعبئة
        if overall_fill_pct > 100:
            st.error(f"⚠️ **تنبيه:** الحجم الكلي ({total_racks_demand} Rack) أكبر من سعة شاحنة واحدة {truck_type} ({max_truck_cap} Rack)! ستحتاج إلى **{trucks_needed} شاحنات**.")
        elif overall_fill_pct >= 85:
            st.success(f"✅ **استغلال ممتاز للشاحنة!** العربية متقفلة بنسبة **{overall_fill_pct:.1f}%**.")
        else:
            st.warning(f"⚠️ **تحذير:** العربية طالعة مش مليانة قوي (نسبة التحميل **{overall_fill_pct:.1f}%** فقط). تفكر تزود طلبية أو تدمج فرع كمان؟")

else:
    st.error("رجاء التأكد من وجود ملف 'Rack Capacity.xlsx' في المشروع.")
