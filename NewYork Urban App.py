import streamlit as st
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, text
import folium
import plotly.express as px
from folium.features import GeoJsonTooltip
from streamlit_folium import st_folium


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="NYC Urban Geospatial Dashboard",
    page_icon="🏙️",
    layout="wide"
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

#DB_NAME = "nyc"
#DB_USER = "postgres"
#DB_PASSWORD = "Postgresql321"
#DB_HOST = "localhost"
#DB_PORT = "5432"

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# =========================================================
# LAND-USE DEFINITIONS
# =========================================================

landuse_names = {
    "01": "One & Two Family Buildings",
    "02": "Multi-Family Walk-Up Buildings",
    "03": "Multi-Family Elevator Buildings",
    "04": "Mixed Residential & Commercial Buildings",
    "05": "Commercial & Office Buildings",
    "06": "Industrial & Manufacturing",
    "07": "Transportation & Utility",
    "08": "Public Facilities & Institutions",
    "09": "Open Space & Outdoor Recreation",
    "10": "Parking Facilities",
    "11": "Vacant Land"
}


landuse_colors = {
    "01": "#1f77b4",
    "02": "#2ca02c",
    "03": "#ff7f0e",
    "04": "#9467bd",
    "05": "#d62728",
    "06": "#8c564b",
    "07": "#17becf",
    "08": "#e377c2",
    "09": "#bcbd22",
    "10": "#7f7f7f",
    "11": "#f2cf5b"
}


highlight_color = "#00A6A6"
neutral_color = "#BDBDBD"


# =========================================================
# TITLE
# =========================================================

st.title("🏙️ NewYork City Geospatial Dashboard")

#st.caption(
#    "PostgreSQL + PostGIS + GeoPandas + Folium + Streamlit"
#)


# =========================================================
# DATABASE CONNECTION TEST
# =========================================================

try:

    with engine.connect() as conn:

        db_info = conn.execute(
            text(
                """
                SELECT
                    current_database(),
                    current_user,
                    PostGIS_Version();
                """
            )
        ).fetchone()

    #st.success("Database connected")
       

except Exception as e:

    st.error(
        f"Database connection failed: {e}"
    )

    st.stop()


# =========================================================
# ABOUT
# =========================================================

with st.expander("About this dashboard", expanded=True):

    st.write(
        """
        This dashboard provides an interactive geospatial analysis of
        New York City building land use, tree distribution, building
        density, and urban greenness using PostgreSQL and PostGIS.

        The dashboard integrates spatial database analysis,
        statistical summaries, interactive mapping, and visualization
        through Python, GeoPandas, Folium, and Streamlit.

        Building analysis uses NYC building footprint and land-use data.
        Tree analysis examines the spatial relationship between trees
        and building land-use categories at selected distances.
        Density and greenness analysis summarizes building and tree
        density using a 1-km spatial grid.
        """
    )


# =========================================================
# LOAD LAND-USE OPTIONS
# =========================================================

landuse_query = """
    SELECT DISTINCT
        landuse,
        landuse_name
    FROM public.building_landuse
    ORDER BY landuse;
"""

landuse_df = pd.read_sql(
    landuse_query,
    engine
)

landuse_options = [
    "All Land Uses"
] + landuse_df["landuse_name"].dropna().tolist()


# =========================================================
# DASHBOARD PANELS
# =========================================================

controls_col, charts_col, stats_col = st.columns(
    [1.4, 3.8, 1.5]
)


# =========================================================
# DASHBOARD CONTROLS
# =========================================================

with controls_col:

    st.subheader("Dashboard Controls")

    analysis_type = st.selectbox(
        "Analysis",
        [
            "Building Analysis",
            "Tree Analysis",
            "Density & Greenness"
        ]
    )

    selected_landuse = st.selectbox(
        "Building Land Use",
        landuse_options
    )

    map_limit = st.selectbox(
        "Maximum Features on Map",
        [500, 1000, 2000],
        index=1
    )

    tree_distance = st.selectbox(
        "Tree Association Distance",
        [5, 10, 15, 25, 40],
        index=1,
        format_func=lambda x: f"{x} m"
    )

    tree_layer = st.radio(
        "Tree Map",
        [
            "Associated Trees",
            "All Trees"
        ]
    )


# =========================================================
# BUILDING SUMMARY
# =========================================================

building_summary_query = """

    SELECT
        landuse,
        landuse_name,
        COUNT(*) AS building_count,

        ROUND(
            COUNT(*) * 100.0 /
            SUM(COUNT(*)) OVER (),
            2
        ) AS percent_of_buildings

    FROM public.building_landuse

    GROUP BY
        landuse,
        landuse_name

    ORDER BY
        building_count DESC;

"""

building_summary = pd.read_sql(
    building_summary_query,
    engine
)


# =========================================================
# TREE SUMMARY
# =========================================================

tree_summary_query = """

    SELECT
        landuse,
        landuse_name,
        distance_m,
        tree_count

    FROM public.tree_landuse_summary

    ORDER BY
        landuse,
        distance_m;

"""

tree_summary = pd.read_sql(
    tree_summary_query,
    engine
)


# =========================================================
# BUILDING DENSITY
# =========================================================

density_query = """

    SELECT
        grid_id,
        area_km2,
        building_count,
        buildings_per_km2

    FROM public.building_density_grid

    ORDER BY grid_id;

"""

density_df = pd.read_sql(
    density_query,
    engine
)


# =========================================================
# URBAN GREENNESS
# =========================================================

greenness_query = """

    SELECT
        grid_id,
        area_km2,
        building_count,
        buildings_per_km2,
        tree_count,
        trees_per_km2

    FROM public.urban_greenness_density

    ORDER BY grid_id;

"""

greenness_df = pd.read_sql(
    greenness_query,
    engine
)


# =========================================================
# SELECTED LAND-USE INFORMATION
# =========================================================

if selected_landuse != "All Land Uses":

    selected_row = building_summary[
        building_summary["landuse_name"] == selected_landuse
    ]

    if not selected_row.empty:

        selected_landuse_code = str(
            selected_row.iloc[0]["landuse"]
        )

        selected_count = int(
            selected_row.iloc[0]["building_count"]
        )

        selected_percent = float(
            selected_row.iloc[0]["percent_of_buildings"]
        )

        selected_rank = (
            building_summary["building_count"]
            .rank(
                method="min",
                ascending=False
            )
            .loc[selected_row.index[0]]
        )

        selected_color = landuse_colors.get(
            selected_landuse_code,
            highlight_color
        )

    else:

        selected_landuse_code = None
        selected_count = 0
        selected_percent = 0
        selected_rank = None
        selected_color = highlight_color

else:

    selected_landuse_code = None
    selected_count = None
    selected_percent = None
    selected_rank = None
    selected_color = None


# =========================================================
# CHARTS & GRAPHS
# =========================================================

with charts_col:

    # =====================================================
    # BUILDING ANALYSIS
    # =====================================================

    if analysis_type == "Building Analysis":

        chart_df = building_summary.copy()

        chart_df["landuse_name"] = chart_df[
            "landuse_name"
        ].fillna(
            "Unknown / Unclassified"
        )

        chart_df["percent_of_buildings"] = chart_df[
            "percent_of_buildings"
        ].astype(float)

        chart_df = chart_df.sort_values(
            "building_count"
        )

        chart_df["chart_label"] = chart_df[
            "landuse_name"
        ].replace({
            "One & Two Family Buildings":
                "One & Two Family",
            "Multi-Family Walk-Up Buildings":
                "Multi-Family Walk-Up",
            "Multi-Family Elevator Buildings":
                "Multi-Family Elevator",
            "Mixed Residential & Commercial Buildings":
                "Mixed Residential / Commercial",
            "Commercial & Office Buildings":
                "Commercial & Office",
            "Industrial & Manufacturing":
                "Industrial & Manufacturing",
            "Transportation & Utility":
                "Transportation & Utility",
            "Public Facilities & Institutions":
                "Public Facilities",
            "Open Space & Outdoor Recreation":
                "Open Space & Recreation",
            "Parking Facilities":
                "Parking",
            "Vacant Land":
                "Vacant Land"
        })

        chart_colors = {
            row["landuse_name"]:
                landuse_colors.get(
                    str(row["landuse"]),
                    neutral_color
                )
            for _, row in chart_df.iterrows()
        }

        st.caption(
            "Building distribution by NYC land-use category"
        )

        fig = px.bar(
            chart_df,
            x="building_count",
            y="chart_label",
            orientation="h",
            text=chart_df[
                "percent_of_buildings"
            ].map(
                lambda x: f"{x:.1f}%"
            ),
            color="landuse_name",
            color_discrete_map=chart_colors
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=12),
            width=0.65,
            marker_line_width=0
        )

        fig.update_layout(
            height=380,
            margin=dict(
                l=0,
                r=45,
                t=5,
                b=8
            ),
            showlegend=False,
            xaxis=dict(
                title="Buildings",
                title_font=dict(size=12),
                tickfont=dict(size=11),
                showgrid=True,
                zeroline=False
            ),
            yaxis=dict(
                title=None,
                tickfont=dict(size=11),
                automargin=True
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "responsive": True
            }
        )


    # =====================================================
    # TREE ANALYSIS
    # =====================================================

    elif analysis_type == "Tree Analysis":

        tree_chart_df = tree_summary.copy()

        tree_chart_df["landuse_name"] = (
            tree_chart_df["landuse_name"]
            .fillna("Unknown / Unclassified")
        )

        if selected_landuse == "All Land Uses":

            st.caption(
                "Tree association with building land-use categories "
                "across distance thresholds"
            )

            fig = px.line(
                tree_chart_df,
                x="distance_m",
                y="tree_count",
                color="landuse_name",
                markers=True,
                color_discrete_map={
                    row["landuse_name"]:
                        landuse_colors.get(
                            str(row["landuse"]),
                            neutral_color
                        )
                    for _, row in (
                        tree_chart_df[
                            [
                                "landuse",
                                "landuse_name"
                            ]
                        ]
                        .drop_duplicates()
                        .iterrows()
                    )
                }
            )

        else:

            tree_chart_df = tree_chart_df[
                tree_chart_df["landuse_name"]
                == selected_landuse
            ].copy()

            st.caption(
                f"Tree association with {selected_landuse}"
            )

            fig = px.line(
                tree_chart_df,
                x="distance_m",
                y="tree_count",
                markers=True
            )

            fig.update_traces(
                line_color=selected_color,
                marker_color=selected_color
            )

        fig.update_traces(
            line_width=3,
            marker_size=8
        )

        fig.update_layout(
            height=380,
            margin=dict(
                l=0,
                r=20,
                t=25,
                b=10
            ),
            xaxis=dict(
                title="Association Distance (m)",
                title_font=dict(size=12),
                tickfont=dict(size=11),
                dtick=5,
                showgrid=True,
                zeroline=False
            ),
            yaxis=dict(
                title="Tree Count",
                title_font=dict(size=12),
                tickfont=dict(size=11),
                showgrid=True,
                zeroline=False
            ),
            legend=dict(
                title=None,
                font=dict(size=10)
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "responsive": True
            }
        )


    # =====================================================
    # DENSITY & GREENNESS
    # =====================================================

    else:

        chart_df = greenness_df.copy()

        chart_df["grid_id"] = chart_df[
            "grid_id"
        ].astype(str)

        st.caption(
            "Relationship between building density and tree density "
            "across 1-km grid cells"
        )

        fig = px.scatter(
            chart_df,
            x="buildings_per_km2",
            y="trees_per_km2",
            hover_data=[
                "grid_id",
                "building_count",
                "tree_count"
            ],
        )

        fig.update_traces(
            marker=dict(
                size=8,
                opacity=0.65
            )
        )

        fig.update_layout(
            height=380,
            margin=dict(
                l=0,
                r=20,
                t=25,
                b=10
            ),
            showlegend=False,
            xaxis=dict(
                title="Buildings / km²",
                title_font=dict(size=12),
                tickfont=dict(size=11),
                showgrid=True,
                zeroline=False
            ),
            yaxis=dict(
                title="Trees / km²",
                title_font=dict(size=12),
                tickfont=dict(size=11),
                showgrid=True,
                zeroline=False
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "responsive": True
            }
        )


# =========================================================
# STATISTICS
# =========================================================

with stats_col:

    st.subheader("Statistics")

    # -----------------------------------------------------
    # BUILDING STATISTICS
    # -----------------------------------------------------

    if analysis_type == "Building Analysis":

        if selected_landuse == "All Land Uses":

            total_buildings = int(
                building_summary["building_count"].sum()
            )

            number_categories = len(
                building_summary
            )

            largest_category = (
                building_summary
                .sort_values(
                    "building_count",
                    ascending=False
                )
                .iloc[0]["landuse_name"]
            )

            st.metric(
                "Total Buildings",
                f"{total_buildings:,}"
            )

            st.markdown(
                '<div style="font-size:0.75rem;color:#666;">Largest Category</div>',
                unsafe_allow_html=True
                )
            st.markdown(
                f'<div style="font-size:0.95rem;font-weight:600;line-height:1.2;white-space:normal;overflow-wrap:break-word;">{largest_category}</div>',
                unsafe_allow_html=True
                )
                     
        else:

            ranked_buildings = (
                building_summary
                .sort_values(
                    "building_count",
                    ascending=False
                )
                .reset_index(drop=True)
            )

            selected_position = ranked_buildings.index[
                ranked_buildings["landuse_name"]
                == selected_landuse
            ][0]

            if selected_position > 0:

                category_above = (
                    ranked_buildings
                    .iloc[selected_position - 1]
                    ["landuse_name"]
                )

            else:

                category_above = "None"

            if selected_position < len(
                ranked_buildings
            ) - 1:

                category_below = (
                    ranked_buildings
                    .iloc[selected_position + 1]
                    ["landuse_name"]
                )

            else:

                category_below = "None"

            st.metric(
                "Buildings",
                f"{selected_count:,}"
            )

            st.metric(
                "Rank",
                f"{int(selected_rank)}"
                if selected_rank is not None
                else "N/A"
            )

            st.markdown(
                '<div style="font-size:0.75rem;color:#666;">Category Above</div>',
                unsafe_allow_html=True
                )
            st.markdown(
                f'<div style="font-size:0.95rem;font-weight:600;line-height:1.2;white-space:normal;overflow-wrap:break-word;">{category_above}</div>',
                unsafe_allow_html=True
                )
            st.markdown(
                '<div style="font-size:0.75rem;color:#666;margin-top:0.7rem;">Category Below</div>',
                unsafe_allow_html=True
                )
            st.markdown(
                f'<div style="font-size:0.95rem;font-weight:600;line-height:1.2;white-space:normal;overflow-wrap:break-word;">{category_below}</div>',
                unsafe_allow_html=True
                )
            
    # -----------------------------------------------------
    # TREE STATISTICS
    # -----------------------------------------------------

    elif analysis_type == "Tree Analysis":

        if selected_landuse != "All Land Uses":

            tree_stats = tree_summary[
                tree_summary["landuse_name"]
                == selected_landuse
            ]

        else:

            tree_stats = (
                tree_summary
                .groupby(
                    "distance_m",
                    as_index=False
                )["tree_count"]
                .sum()
            )

        if not tree_stats.empty:

            selected_distance = tree_stats[
                tree_stats["distance_m"]
                == tree_distance
            ]

            if not selected_distance.empty:

                tree_count = int(
                    selected_distance.iloc[0]
                    ["tree_count"]
                )

                st.metric(
                    f"Trees within {tree_distance} m",
                    f"{tree_count:,}"
                )

            max_tree_distance = int(
                tree_stats["distance_m"].max()
            )

            st.metric(
                "Maximum Distance",
                f"{max_tree_distance} m"
            )

            total_tree_records = int(
                tree_stats["tree_count"].max()
            )

            st.metric(
                "Maximum Tree Count",
                f"{total_tree_records:,}"
            )

        else:

            st.info(
                "No tree statistics available."
            )


    # -----------------------------------------------------
    # DENSITY STATISTICS
    # -----------------------------------------------------

    else:

        st.metric(
            "Grid Cells",
            f"{len(greenness_df):,}"
        )

        st.metric(
            "Mean Buildings / km²",
            f"{greenness_df['buildings_per_km2'].mean():,.2f}"
        )

        st.metric(
            "Mean Trees / km²",
            f"{greenness_df['trees_per_km2'].mean():,.2f}"
        )

        st.metric(
            "Maximum Buildings / km²",
            f"{greenness_df['buildings_per_km2'].max():,.2f}"
        )

# =========================================================
# INTERACTIVE MAP
# =========================================================

st.divider()

st.subheader("Interactive Map")


# =========================================================
# BUILDING MAP
# =========================================================

if analysis_type == "Building Analysis":

    if selected_landuse == "All Land Uses":

        building_map_query = f"""
            WITH ranked_buildings AS (
                SELECT
                    b.building_id,
                    l.landuse,
                    l.landuse_name,
                    b.geom,

                    ROW_NUMBER() OVER (
                        PARTITION BY l.landuse
                        ORDER BY b.building_id
                    ) AS rn

                FROM public.building_footprints_2263 b

                INNER JOIN public.building_landuse l
                    ON b.building_id = l.building_id
            )

            SELECT
                building_id,
                landuse,
                landuse_name,
                geom

            FROM ranked_buildings

            WHERE rn <= {max(1, map_limit // 11)}

            ORDER BY
                landuse,
                building_id;
        """

        building_gdf = gpd.read_postgis(
            building_map_query,
            engine,
            geom_col="geom"
        )

    else:

        building_map_query = """
            SELECT
                b.building_id,
                l.landuse,
                l.landuse_name,
                b.geom

            FROM public.building_footprints_2263 b

            INNER JOIN public.building_landuse l
                ON b.building_id = l.building_id

            WHERE l.landuse_name = %(landuse)s

            ORDER BY b.building_id

            LIMIT %(limit)s;
        """

        building_gdf = gpd.read_postgis(
            building_map_query,
            engine,
            geom_col="geom",
            params={
                "landuse": selected_landuse,
                "limit": map_limit
            }
        )


    # =====================================================
    # MAP CENTER
    # =====================================================

    if not building_gdf.empty:

        building_gdf = building_gdf.to_crs(
            epsg=4326
        )

        map_center = [
            building_gdf.geometry.centroid.y.mean(),
            building_gdf.geometry.centroid.x.mean()
        ]

    else:

        map_center = [
            40.7128,
            -74.0060
        ]


    m = folium.Map(
        location=map_center,
        zoom_start=11,
        tiles="Esri World Gray Canvas"
    )


    # =====================================================
    # BUILDING POLYGONS
    # =====================================================

    if not building_gdf.empty:

        def building_style(feature):

            landuse_code = str(
                feature["properties"].get(
                    "landuse",
                    ""
                )
            )

            if selected_landuse == "All Land Uses":

                fill_color = landuse_colors.get(
                    landuse_code,
                    neutral_color
                )

                return {
                    "fillColor": fill_color,
                    "color": fill_color,
                    "weight": 0.5,
                    "fillOpacity": 0.65
                }

            else:

                return {
                    "fillColor": selected_color,
                    "color": selected_color,
                    "weight": 0.8,
                    "fillOpacity": 0.65
                }


        folium.GeoJson(
            building_gdf,
            name="Building Land Use",
            style_function=building_style,
            tooltip=GeoJsonTooltip(
                fields=[
                    "building_id",
                    "landuse_name"
                ],
                aliases=[
                    "Building ID",
                    "Land Use"
                ],
                localize=True
            )
        ).add_to(m)


    # =====================================================
    # BUILDING CENTROIDS
    # =====================================================

    centroid_query = """
        SELECT
            b.building_id,
            l.landuse,
            l.landuse_name,
            ST_Centroid(b.geom) AS geom

        FROM public.building_footprints_2263 b

        INNER JOIN public.building_landuse l
            ON b.building_id = l.building_id
    """

    if selected_landuse != "All Land Uses":

        centroid_query += """
            WHERE l.landuse_name = %(landuse)s

            ORDER BY b.building_id

            LIMIT %(limit)s;
        """

        centroid_gdf = gpd.read_postgis(
            centroid_query,
            engine,
            geom_col="geom",
            params={
                "landuse": selected_landuse,
                "limit": map_limit
            }
        )

    else:

        centroid_query += f"""
            ORDER BY b.building_id
            LIMIT {map_limit};
        """

        centroid_gdf = gpd.read_postgis(
            centroid_query,
            engine,
            geom_col="geom"
        )


    if not centroid_gdf.empty:

        centroid_gdf = centroid_gdf.to_crs(
            epsg=4326
        )

        for _, row in centroid_gdf.iterrows():

            if selected_landuse == "All Land Uses":

                point_color = "#666666"

            else:

                point_color = selected_color

            folium.CircleMarker(
                location=[
                    row["geom"].y,
                    row["geom"].x
                ],
                radius=2,
                color=point_color,
                fill=True,
                fill_color=point_color,
                fill_opacity=0.45,
                weight=0.5,
                tooltip=(
                    f"Building ID: {row['building_id']}<br>"
                    f"Land Use: {row['landuse_name']}"
                )
            ).add_to(m)


# =========================================================
# TREE MAP
# =========================================================

elif analysis_type == "Tree Analysis":

    # -----------------------------------------------------
    # TREE LAYER
    # -----------------------------------------------------

    if tree_layer == "Associated Trees":

        if selected_landuse == "All Land Uses":

            tree_map_query = """

                SELECT
                    t.tree_id,
                    t.geom

                FROM public.nyc_2015_tree_census_2263 t

                WHERE EXISTS (

                    SELECT 1

                    FROM public.building_footprints_2263 b

                    WHERE ST_DWithin(
                        t.geom,
                        b.geom,
                        %(distance)s
                    )

                )

                ORDER BY t.tree_id

                LIMIT %(limit)s;

            """

            tree_gdf = gpd.read_postgis(
                tree_map_query,
                engine,
                geom_col="geom",
                params={
                    "distance": tree_distance * 3.28084,
                    "limit": map_limit
                }
            )

        else:

            tree_map_query = """

                SELECT
                    t.tree_id,
                    t.geom

                FROM public.nyc_2015_tree_census_2263 t

                WHERE EXISTS (

                    SELECT 1

                    FROM public.building_footprints_2263 b

                    INNER JOIN public.building_landuse l
                        ON b.building_id = l.building_id

                    WHERE
                        l.landuse_name = %(landuse)s

                        AND ST_DWithin(
                            t.geom,
                            b.geom,
                            %(distance)s
                        )

                )

                ORDER BY t.tree_id

                LIMIT %(limit)s;

            """

            tree_gdf = gpd.read_postgis(
                tree_map_query,
                engine,
                geom_col="geom",
                params={
                    "landuse": selected_landuse,
                    "distance": tree_distance * 3.28084,
                    "limit": map_limit
                }
            )

    else:

        tree_map_query = """

            SELECT
                tree_id,
                geom

            FROM public.nyc_2015_tree_census_2263

            ORDER BY tree_id

            LIMIT %(limit)s;

        """

        tree_gdf = gpd.read_postgis(
            tree_map_query,
            engine,
            geom_col="geom",
            params={
                "limit": map_limit
            }
        )


    # -----------------------------------------------------
    # TREE MAP CENTER
    # -----------------------------------------------------

    if not tree_gdf.empty:

        tree_gdf = tree_gdf.to_crs(
            epsg=4326
        )

        map_center = [
            tree_gdf.geometry.y.mean(),
            tree_gdf.geometry.x.mean()
        ]

    else:

        map_center = [
            40.7128,
            -74.0060
        ]


    m = folium.Map(
        location=map_center,
        zoom_start=11,
        tiles="Esri World Gray Canvas"
    )


    # -----------------------------------------------------
    # TREES
    # -----------------------------------------------------

    if not tree_gdf.empty:

        for _, row in tree_gdf.iterrows():

            point = row["geom"]

            folium.CircleMarker(
                location=[
                    point.y,
                    point.x
                ],
                radius=3,
                color=(
                    selected_color
                    if selected_landuse != "All Land Uses"
                    else highlight_color
                ),
                fill=True,
                fill_color=(
                    selected_color
                    if selected_landuse != "All Land Uses"
                    else highlight_color
                ),
                fill_opacity=0.75,
                weight=0.5,
                tooltip=f"Tree ID: {row['tree_id']}"
            ).add_to(m)


    # -----------------------------------------------------
    # ASSOCIATED BUILDINGS
    # -----------------------------------------------------

    if selected_landuse != "All Land Uses":

        associated_building_query = """

            SELECT DISTINCT
                b.building_id,
                l.landuse,
                l.landuse_name,
                b.geom

            FROM public.building_footprints_2263 b

            INNER JOIN public.building_landuse l
                ON b.building_id = l.building_id

            WHERE l.landuse_name = %(landuse)s

            LIMIT %(limit)s;

        """

        associated_buildings = gpd.read_postgis(
            associated_building_query,
            engine,
            geom_col="geom",
            params={
                "landuse": selected_landuse,
                "limit": map_limit
            }
        )

        if not associated_buildings.empty:

            associated_buildings = (
                associated_buildings
                .to_crs(epsg=4326)
            )

            folium.GeoJson(
                associated_buildings,
                name="Selected Buildings",
                style_function=lambda feature: {
                    "fillColor": "#FFFFFF",
                    "color": selected_color,
                    "weight": 1.0,
                    "fillOpacity": 0.05
                },
                tooltip=GeoJsonTooltip(
                    fields=[
                        "building_id",
                        "landuse_name"
                    ],
                    aliases=[
                        "Building ID",
                        "Land Use"
                    ]
                )
            ).add_to(m)


# =========================================================
# DENSITY & GREENNESS MAP
# =========================================================

else:

    greenness_map_query = """
        SELECT
            grid_id,
            area_km2,
            building_count,
            buildings_per_km2,
            tree_count,
            trees_per_km2,
            geom

        FROM public.urban_greenness_density

        ORDER BY grid_id;
    """

    greenness_gdf = gpd.read_postgis(
        greenness_map_query,
        engine,
        geom_col="geom"
    )


    # =====================================================
    # MAP CENTER
    # =====================================================

    if not greenness_gdf.empty:

        greenness_gdf = greenness_gdf.to_crs(
            epsg=4326
        )

        map_center = [
            greenness_gdf.geometry.centroid.y.mean(),
            greenness_gdf.geometry.centroid.x.mean()
        ]

    else:

        map_center = [
            40.7128,
            -74.0060
        ]


    # =====================================================
    # MAP
    # =====================================================

    m = folium.Map(
        location=map_center,
        zoom_start=10,
        tiles="Esri World Gray Canvas"
    )


    # =====================================================
    # DENSITY GRID
    # =====================================================

    if not greenness_gdf.empty:

        min_density = greenness_gdf[
            "buildings_per_km2"
        ].min()

        max_density = greenness_gdf[
            "buildings_per_km2"
        ].max()


        def density_style(feature):

            value = feature["properties"][
                "buildings_per_km2"
            ]

            if max_density > min_density:

                normalized = (
                    value - min_density
                ) / (
                    max_density - min_density
                )

            else:

                normalized = 0.0


            red = int(
                255 * normalized
            )

            green = int(
                180 * (1 - normalized)
            )

            blue = int(
                80 * (1 - normalized)
            )

            return {
                "fillColor": (
                    f"rgb({red},{green},{blue})"
                ),
                "color": "#666666",
                "weight": 0.5,
                "fillOpacity": 0.65
            }


        folium.GeoJson(
            greenness_gdf,
            name="1-km Density Grid",
            style_function=density_style,
            tooltip=GeoJsonTooltip(
                fields=[
                    "grid_id",
                    "building_count",
                    "buildings_per_km2",
                    "tree_count",
                    "trees_per_km2"
                ],
                aliases=[
                    "Grid ID",
                    "Buildings",
                    "Buildings / km²",
                    "Trees",
                    "Trees / km²"
                ],
                localize=True
            )
        ).add_to(m)


# =========================================================
# LAYER CONTROL
# =========================================================

#folium.LayerControl(
#    collapsed=False
#).add_to(m)


# =========================================================
# DISPLAY MAP
# =========================================================

st_folium(m, width="100%", height=650)

st.markdown("---")

st.subheader("About the Author")

st.markdown(
    """
    **Sandip Rijal**  
    Geosciences | Remote Sensing & GIS | Geospatial Data Science

    Sandip Rijal specializes in remote sensing, GIS, geospatial data science, and
    spatial analysis, with research focused on environmental change, natural hazards,
    and urban and coastal systems.

    **Contact:** [sandip.rijal55@gmail.com](mailto:sandip.rijal55@gmail.com)
    """
)
