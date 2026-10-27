"""Browse the collected ThemeForest themes: streamlit run app.py."""

import json
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st


ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Care Themes | Theme Explorer", page_icon="🏥", layout="wide")


def load_themes():
    themes = {}
    for category in ("hospital", "clinic"):
        path = ROOT / f"{category}.json"
        if not path.exists():
            st.warning(f"{path.name} is missing. Run code.py to collect themes.")
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(rows, list):
                raise ValueError("Expected a JSON array")
            for row in rows:
                if not isinstance(row, dict) or not row.get("website_link"):
                    continue
                key = row["website_link"]
                if key not in themes:
                    themes[key] = {**row, "categories": []}
                if category not in themes[key]["categories"]:
                    themes[key]["categories"].append(category)
        except (ValueError, OSError) as exc:
            st.error(f"Cannot read {path.name}: {exc}")
    return list(themes.values())


def valid_link(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"https", "http"} and bool(parsed.netloc)


themes = load_themes()

st.markdown("""
<style>
[data-testid="stSidebar"] {background: #0e1117; color: #f1f5f9; border-right: 1px solid #293241;}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top: 1.8rem;}
[data-testid="stSidebar"] h2 {font-size: 1.35rem; letter-spacing: -.04em; color: #f1f5f9;}
[data-testid="stSidebar"] [data-testid="stMetric"] {background: #171e29; border: 1px solid #303b4c;
    border-radius: 12px; padding: 10px 12px; margin-bottom: 8px;}
[data-testid="stSidebar"] [data-testid="stMetricValue"] {font-size: 1.55rem; color: #5eead4;}
[data-testid="stSidebar"] [data-baseweb="select"] > div {border-radius: 9px; background: #171e29; color: #f1f5f9;}
[data-testid="stSidebar"] [data-testid="stExpander"] {background: #131923; border: 1px solid #293241; border-radius: 12px;}
[data-testid="stSidebar"] label {font-size: .85rem; color: #e2e8f0;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color: #a8b6c8;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {color: #e2e8f0;}
[data-testid="stSidebar"] input {background: #171e29; color: #f1f5f9;}
[data-testid="stSidebar"] button {background: #171e29; color: #f1f5f9; border-color: #303b4c;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ?? Care Themes")
    st.caption("YOUR HEALTHCARE THEME LIBRARY")
    with st.expander("Collection overview", expanded=True):
        st.caption("Find your next healthcare website. Explore themes, descriptions and live demos.")
        left, right = st.columns(2)
        left.metric("Unique themes", len(themes))
        right.metric("With demos", sum(valid_link(t.get("demo_link")) for t in themes))
        left.metric("Hospital", sum("hospital" in t["categories"] for t in themes))
        right.metric("Clinic", sum("clinic" in t["categories"] for t in themes))
    st.caption("BROWSE COLLECTION")
    query = st.text_input("Search themes", placeholder="Search name or technology...")
    category = st.selectbox("Category", ["All themes", "Hospital", "Clinic"])
    with st.expander("Filter & display", expanded=True):
        availability = st.selectbox("Link availability", ["All themes", "With live demo", "With mobile link", "With demo and mobile"])
        demo_only = availability in {"With live demo", "With demo and mobile"}
        mobile_only = availability in {"With mobile link", "With demo and mobile"}
        sort = st.selectbox("Sort by", ["Name A?Z", "Name Z?A"])
        page_size = st.selectbox("Rows per page", [12, 24, 48])
    navigation = st.container()
    st.divider()
    if st.button("Refresh collection", use_container_width=True):
        st.rerun()
    st.caption("Hospital & clinic themes ? ThemeForest")


filtered = [t for t in themes
            if (category == "All themes" or category.lower() in t["categories"])
            and (not query.strip() or query.strip().casefold() in
                 f"{t.get('name', '')} {t.get('description', '')}".casefold())
            and (not demo_only or valid_link(t.get("demo_link")))
            and (not mobile_only or valid_link(t.get("mobile_link")))]
filtered.sort(key=lambda t: t.get("name", "").casefold(), reverse=sort == "Name Z–A")

heading, download = st.columns([3, 1])
heading.subheader(f"{len(filtered)} themes found")
download.download_button("Download results · JSON", json.dumps(filtered, ensure_ascii=False, indent=2),
                         file_name="filtered_themes.json", mime="application/json",
                         use_container_width=True)

if not filtered:
    st.info("No themes match these filters. Try another search or category.")
else:
    pages = (len(filtered) + page_size - 1) // page_size
    filters = (category, query, demo_only, mobile_only, sort, page_size)
    if st.session_state.get("table_filters") != filters:
        st.session_state["table_page"] = 1
        st.session_state["table_filters"] = filters
    st.session_state["table_page"] = min(st.session_state.get("table_page", 1), pages)

    def change_page(delta):
        st.session_state["table_page"] += delta

    previous, following = st.columns(2)
    previous.button("Previous", disabled=st.session_state["table_page"] <= 1,
                    on_click=change_page, args=(-1,), use_container_width=True)
    with navigation:
        st.caption("PAGINATION")
        st.selectbox("Page", range(1, pages + 1), key="table_page",
                     format_func=lambda n: f"Page {n} of {pages}")
    following.button("Next", disabled=st.session_state["table_page"] >= pages,
                     on_click=change_page, args=(1,), use_container_width=True)
    page = st.session_state["table_page"]
    start = (page - 1) * page_size
    visible = filtered[start:start + page_size]
    table_rows = [{
        "No.": start + index + 1,
        "Name": theme.get("name") or "Untitled theme",
        "Category": ", ".join(c.title() for c in theme["categories"]),
        "Description": (theme.get("description") or "Description unavailable.")[:180],
        "ThemeForest": theme.get("website_link") if valid_link(theme.get("website_link")) else None,
        "Live demo": theme.get("demo_link") if valid_link(theme.get("demo_link")) else None,
        "Mobile": theme.get("mobile_link") if valid_link(theme.get("mobile_link")) else None,
    } for index, theme in enumerate(visible)]
    st.caption(f"Showing {start + 1}?{min(start + page_size, len(filtered))} of {len(filtered)} themes")
    st.dataframe(
        table_rows,
        use_container_width=True,
        hide_index=True,
        column_order=["No.", "Name", "Category", "ThemeForest", "Live demo", "Mobile", "Description"],
        key=f"table-{category}-{query}-{demo_only}-{mobile_only}-{sort}-{page_size}-{page}",
        column_config={
            "No.": st.column_config.NumberColumn("No.", format="%d", width="small"),
            "Name": st.column_config.TextColumn("Theme name", width="large"),
            "Category": st.column_config.TextColumn(width="small"),
            "Description": st.column_config.TextColumn("Description preview", width="large"),
            "ThemeForest": st.column_config.LinkColumn(display_text="View theme"),
            "Live demo": st.column_config.LinkColumn(display_text="Open demo"),
            "Mobile": st.column_config.LinkColumn(display_text="Open mobile"),
        },
    )

st.caption("Some themes appear in both categories. The total counts each theme once. Links open external websites.")
