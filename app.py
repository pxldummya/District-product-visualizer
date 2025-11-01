import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects
import matplotlib.lines as mlines
import ast
import zipfile
import os
import random
from shapely.geometry import Point
import json
import io

st.set_page_config(layout="wide")
st.title("District Product Map")
# PSA for users
st.info("📌 Uploading a shapefile is optional. The app will use the default shapefile if none is uploaded.\n\n"
        "➡️ Start by clicking 'Generate Map' to see the current layout first 🙂")

def random_point_in_polygon_no_overlap(polygon, existing_points, min_dist=0.01, max_attempts=100):
    """
    Generate a random point inside the polygon that does NOT overlap
    with existing points (within a min_dist).
    """
    buffered = polygon.buffer(-0.02)  # shrink boundary slightly
    if buffered.is_empty or not buffered.is_valid:
        buffered = polygon

    minx, miny, maxx, maxy = buffered.bounds

    for _ in range(max_attempts):
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        point = Point(x, y)

        if not buffered.contains(point):
            continue

        too_close = any(point.distance(p) < min_dist for p in existing_points)
        if not too_close:
            return point

    return polygon.centroid  # fallback if all attempts fail

# -------------------------------
# 1. PASTE YOUR DICTIONARIES HERE
# -------------------------------
district_list = [
    "Chipinge",
    "Chimanimani",
    "Buhera",
    "Bikita",
    "Mudzi",
    "Rushinga",
    "Mt Darwin",
    "UMP",
    "Mutoko",
    "Chivi",
    "Mwenezi",
    "Mberengwa",
    "Beitbridge",
    "Hwange",
    "Lupane",
    "Nyanga",
    "Matoba",
    "Kwekwe",
    "Binga",
    "Mbire"
]

product_codes = {
    1: "Baobab",
    2: "KMS",
    3: "Ximenia",
    4: "Marula",
    5: "Trichelia",
    6: "Rosella",
    7: "Resurrection",
    8: "Zumbani",
    9: "Mongongo",
    10: "Kigelia"
}
# district_products = { ... }
district_products = {
    "Chipinge": [1, 2,3, 4,5, 6],
    "Chimanimani": [1,2,3,4, 6,10],
    "Buhera": [1, 2, 3,4,6],
    "Bikita": [1],
    "Mudzi": [1,2,3,4,6],
    "Rushinga": [1,2,3,4,6],
    "Mount Darwin": [1,2,3,4,6],
    "Uzumba Maramba Pfungwe": [1,2,3,4,6],
    "Mutoko": [1,2,3,4,6,7],
    "Chivi": [2,3,4,7],
    "Mwenezi": [4],
    "Mberengwa": [4],
    "Beitbridge": [2, 3, 4],
    "Hwange": [2,3],
    "Lupane": [2,3],
    "Nyanga": [3,8],
    "Matobo": [2,4],
    "Kwekwe": [2,3, 9],
    "Binga": [1,2,3,5,6],
    "Mbire": [1,6]
}
district_acronyms = {
    "Uzumba Maramba Pfungwe": "UMP",
    "Mount Darwin": "Mt Darwin",

}
# district_groups = { ... }
product_colors = {
    1: "#E41A1C",  # Red       (Baobab)
    2: "#377EB8",  # Blue      (KMS)
    3: "#4DAF4A",  # Green     (Ximenia)
    4: "#984EA3",  # Purple    (Marula)
    5: "#FF7F00",  # Orange    (Trichelia)
    6: "#A65628",  # Brown     (Rosella)
    7: "#F781BF",  # Pink      (Resurrection)
    8: "#999999",  # Gray      (Zumbani)
    9: "#FFD700",  # Gold      (Mongongo)
    10: "#1B9E77"  # Teal-Green (Kigelia)
}


product_codes = {
    1: "Baobab",
    2: "KMS",
    3: "Ximenia",
    4: "Marula",
    5: "Trichelia",
    6: "Rosella",
    7: "Resurrection",
    8: "Zumbani",
    9: "Mongongo",
    10: "Kigelia"
}

district_groups = {
    "set1": ["Chipinge", "Chimanimani", "Bikita", "Buhera"],
    "set2": ["Hwange", "Binga"],
    "set3": ["Lupane"],
    "set4": ["Mberengwa", "Chivi", "Mwenezi", "Beitbridge"],
    "set5": ["Matobo"],
    "set6": ["Mbire"],
    "set7": ["Kwekwe"],
    "set8": ["Rushinga", "Mudzi", "Uzumba Maramba Pfungwe", "Mount Darwin"],
    "set9": ["Nyanga", "Mutoko"]
}

# Assign colors to each set (you can change these hex codes)
group_colors = {
    "set1": "#f4a582",  # light orange
    "set2": "#92c5de",  # light blue
    "set3": "#b2abd2",  # light purple
    "set4": "#a6dba0",  # light green
    "set5": "#fddbc7",  # peach
    "set6": "#d1e5f0",   # pale blue
    "set7": "#fee0b6",
    "set8": "#c7e9c0",
    "set9": "#f2d4e9"
}
# group_colors = { ... }
# product_codes = { ... }
# product_colors = { ... }
# district_acronyms = { ... }

# -------------------------------
# 2. Editable user inputs
# -------------------------------
# Product Codes
# Product Codes (editable JSON)
with st.expander("Edit Product Codes"):
    st.markdown("### 🧾 Product Codes")
    st.write("""
    Define product IDs and their names.
    
    Example format: `{ 1: 'Baobab', 2: 'KMS' }`
    
    - Each ID must be unique.
    - These IDs are used for color assignment on the map.
    - If you add new products, colors will be generated automatically below.
    """)

    product_codes_json = st.text_area(
        "Enter as JSON, e.g., { 1: 'Baobab', 2: 'KMS' }",
        value=json.dumps(product_codes, indent=2)
    )
    product_codes = json.loads(product_codes_json)

# Product Colors (with color pickers)
with st.expander("Edit Product Colors"):
    st.markdown("### 🎨 Product Colors")
    st.write("""
    Assign a unique color to each product ID for clear visualization on the map.
    
    - Use the color pickers below to customize each product’s color.
    - Colors help distinguish products when plotted in different districts.
    - If new products were added above, random colors will be generated automatically.
    """)

    for code, color in product_colors.items():
        product_colors[code] = st.color_picker(
            f"Color for {product_codes.get(code, code)}", value=color
        )

# Ensure all products have colors (auto-assign missing ones)
for pid in product_codes.keys():
    if pid not in product_colors:
        random_color = "#%06x" % random.randint(0, 0xFFFFFF)
        product_colors[pid] = random_color

# District Products
with st.expander("Edit District Products"):
    st.markdown("### 🏭 District Products")
    st.write("""
    Define which products are found in each district.  
    Example format: `{ "Chipinge": [1, 2], "Bikita": [3, 5] }`
    
    - Use the product **IDs** (from the Product Codes section).  
    - A district can have multiple products.
    - Only district with products need to be specified.
    """)

    district_products_json = st.text_area(
        "Enter as JSON, e.g., { 'Chipinge': [1, 2], 'Bikita': [3, 5] }",
        value=json.dumps(district_products, indent=2)
    )
    district_products = json.loads(district_products_json)


# District Groups
with st.expander("Edit District Groups"):
    st.markdown("### 🗺️ District Groups")
    st.write("""
    Define which districts belong to which set (e.g., officers or management zones).  
    Example format: `{ "Set1": ["Chipinge", "Bikita"], "Set2": ["Mutare", "Chimanimani"] }`
    
    - Each set groups together related districts.
    - You can rename the sets to actual officer names or team names.
    - **⚠️ Warning:** If the same district appears in more than one set, the district will be shaded according to the *last* set that contains it.  
      (The district will take the shading color of that final set.)
    """)

    district_groups_json = st.text_area(
        "Enter as JSON, e.g., { 'Set1': ['Chipinge','Bikita'] }",
        value=json.dumps(district_groups, indent=2)
    )
    district_groups = json.loads(district_groups_json)


# Group Colors (with color pickers)
with st.expander("Edit District Group Colors"):
    for group_name, color in group_colors.items():
        group_colors[group_name] = st.color_picker(f"Color for {group_name}", value=color)




# District Acronyms

# Convert JSON strings to Python dictionaries
district_products = ast.literal_eval(district_products_json)
district_groups = ast.literal_eval(district_groups_json)
product_codes = ast.literal_eval(product_codes_json)
#district_acronyms = ast.literal_eval(district_acronyms_json)

# -------------------------------
# 3. Upload shapefile zip
# -------------------------------
shp_file = st.file_uploader("Upload shapefile (.zip containing .shp/.shx/.dbf/.prj)", type="zip")

if shp_file:
    with zipfile.ZipFile(shp_file, 'r') as zip_ref:
        zip_ref.extractall("/tmp/shapefile")
    gdf = gpd.read_file("/tmp/shapefile/gadm41_ZWE_2.shp")
else:
# Use local default shapefile
    shp_file_path = "shapefile.zip"  # make sure this is in the same folder as app.py
    with zipfile.ZipFile(shp_file_path, 'r') as zip_ref:
        zip_ref.extractall("/tmp/shapefile")
    gdf = gpd.read_file("/tmp/shapefile/gadm41_ZWE_2.shp")
    district_column = "NAME_2"  # adjust if your shapefile has a different column name
    gdf = gdf[~gdf[district_column].str.endswith("Urban")]
    # -------------------------------
    # 4. Generate map button
    # -------------------------------
    dpi = st.slider("Select map resolution (DPI)", min_value=50, max_value=300, value=150)
    if st.button("Generate Map"):
        fig, ax = plt.subplots(figsize=(14,12), dpi = dpi)
    
        # Plot districts and shading
        gdf.plot(ax=ax, edgecolor='gray', facecolor='white', linewidth=0.8)
        for group_name, districts in district_groups.items():
            color = group_colors.get(group_name, "#ffffff")
            subset = gdf[gdf[district_column].isin(districts)]
            subset.plot(ax=ax, edgecolor='gray', facecolor=color, linewidth=0.8, zorder=1)

        plotted_products = set()
        # Loop over districts
        for idx, row in gdf.iterrows():
            district = row[district_column]
            polygon = row.geometry
            centroid = polygon.centroid
            product_ids = district_products.get(district, [])
            existing_points = []
                
            plotted_colors = {}
            if product_ids:  # districts with products
                for pid in product_ids:
                    point = random_point_in_polygon_no_overlap(polygon, existing_points, min_dist=0.05, max_attempts=30)
                    existing_points.append(point)
                    color = product_colors.get(pid, "black")
                    ax.plot(point.x, point.y, 'o', color=color, markersize=7)
                    plotted_products.add(pid)  # <- record which products actually appear
                    plotted_colors[pid] = color
                # Bold label
                label_text = district_acronyms.get(district, district)
                ax.text(centroid.x + 0.06, centroid.y + 0.06,
                        label_text, fontsize=8, ha='center', color='dimgray',
                        fontweight='bold',
                        path_effects=[PathEffects.Stroke(linewidth=1.5, foreground='white'), PathEffects.Normal()])
    
            else:  # districts without products
                ax.text(centroid.x, centroid.y, district, fontsize=6, ha='center', color='gray')
        
        # Ensure product_codes and product_colors have integer keys
        product_codes = {int(k): v for k, v in product_codes.items()}
        product_colors = {int(k): v for k, v in product_colors.items()}
        
       # Only include products that actually appear on the map
        if plotted_products:
                product_handles = [
                mlines.Line2D([], [], color=plotted_colors[pid], marker='o', linestyle='None', markersize=8, label=product_codes[pid])
                for pid in sorted(plotted_products)
                ]
                
                
                product_legend = ax.legend(handles=product_handles, title="Products", loc="lower left")
                ax.add_artist(product_legend)
                
                
                # District legend remains the same
        district_handles = [
                mlines.Line2D([], [], color=color, marker='s', linestyle='None', markersize=12, label=group_name)
                for group_name, color in group_colors.items()
                ]
        ax.legend(handles=district_handles, title="District Groups",
                loc='lower center', bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False)

        

        plt.axis('off')
        st.pyplot(fig, dpi = dpi)


        # Download button
       # Download button uses same DPI
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi)
        buf.seek(0)
        st.download_button(
            label="Download Plot as PNG",
            data=buf,
            file_name=f"district_products_map_{dpi}dpi.png",
            mime="image/png"
        )











