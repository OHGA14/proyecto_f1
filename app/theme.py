"""CSS global del dashboard (estilo editorial oscuro)."""
import textwrap

import streamlit as st


def apply_theme():
    """Inyecta el CSS global. Llamar una vez, después de set_page_config."""
    st.markdown(textwrap.dedent("""

    <style>

        /* Clean Professional / Broadcast Engineering */

        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

        .stApp {

            background-color: #0e1117; /* Dark background */

            color: #ffffff;

            font-family: 'Roboto', sans-serif;

        }

        /* Sidebar: minimal, no heavy shadows */

        section[data-testid="stSidebar"] {

            background-color: transparent;

            border-right: 1px solid #222;

        }

        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {

            color: #ffffff !important;

            font-weight: 600;

        }

        /* Widgets: subtle containers */

        .stSelectbox div[data-baseweb="select"] > div,

        .stSlider div[data-baseweb="base-input"],

        .stRadio div[role="radiogroup"] label {

            background-color: rgba(255,255,255,0.03) !important;

            border: 1px solid #333 !important;

            color: #ddd !important;

            font-family: 'Roboto', sans-serif;

        }

        /* Tabs: barra segmentada, pestaña activa = pill rojo destacado */
        .stTabs [data-baseweb="tab-list"] {
            gap: 5px;
            background: rgba(255,255,255,0.025);
            padding: 5px;
            border-radius: 11px;
            border: 1px solid #23252d;
            margin-bottom: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            background: transparent;
            color: #b3bac6;
            border: none;
            border-radius: 8px;
            font-family: 'Roboto', sans-serif;
            font-weight: 700;
            font-size: 13.5px;
            letter-spacing: .9px;
            text-transform: uppercase;
            padding: 0 20px;
            transition: color .16s ease, background .16s ease, box-shadow .16s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #ffffff;
            background: rgba(255,255,255,0.06);
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(180deg, rgba(255,45,45,.22), rgba(255,45,45,.12)) !important;
            color: #ffffff !important;
            border: none !important;
            box-shadow: inset 0 0 0 1px rgba(255,60,60,.5), 0 2px 10px rgba(255,45,45,.12);
        }
        .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { background-color: transparent !important; }

        /* Driver card: broadcast premium (acento de color de equipo + glow + hover) */
        .driver-card {
            position: relative;
            background: rgba(255,255,255,0.03);
            border: 1px solid #2a2f3a;
            border-radius: 10px;
            padding: 14px 16px 15px;
            overflow: hidden;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }
        .driver-card::before {
            content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, var(--tc, #888), transparent 88%);
        }
        .driver-card::after {
            content: ""; position: absolute; top: -45%; right: -18%;
            width: 130px; height: 130px; border-radius: 50%;
            background: radial-gradient(circle, var(--tc, #888) 0%, transparent 70%);
            opacity: .14; pointer-events: none;
        }
        .driver-card:hover {
            transform: translateY(-3px);
            border-color: var(--tc, #444);
            box-shadow: 0 8px 26px rgba(0,0,0,.5);
        }
        .dc-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .dc-name { font-size: 23px; font-weight: 800; letter-spacing: .3px; line-height: 1; }
        .dc-pos { color: #0e1117; font-weight: 800; font-size: 12px; padding: 3px 10px; border-radius: 20px; box-shadow: 0 1px 6px rgba(0,0,0,.35); }
        .dc-body { display: flex; justify-content: space-between; align-items: flex-end; }
        .dc-label { font-size: 10px; color: #7a8290; text-transform: uppercase; letter-spacing: 1.4px; margin-bottom: 3px; }
        .dc-time { font-size: 34px; font-weight: 800; color: #fff; line-height: 1; font-variant-numeric: tabular-nums; text-shadow: 0 1px 10px rgba(0,0,0,.4); }
        .dc-lapval { font-size: 19px; font-weight: 600; color: #cfd4dc; font-variant-numeric: tabular-nums; }
        .dc-pts { font-size: 10px; font-weight: 800; color: #e8eaed; background: rgba(255,255,255,0.07);
            border: 1px solid #3a3f48; border-radius: 10px; padding: 1px 7px; white-space: nowrap;
            letter-spacing: .3px; font-variant-numeric: tabular-nums; }
        .dc-bars { margin-top: 11px; display: flex; flex-direction: column; gap: 5px; }
        .dc-brow { display: flex; align-items: center; gap: 8px; }
        .dc-blab { font-size: 8.5px; letter-spacing: .6px; text-transform: uppercase; color: #8a919c;
            width: 62px; flex: 0 0 auto; }
        .dc-btrack { flex: 1 1 auto; height: 6px; background: rgba(255,255,255,0.07); border-radius: 4px; overflow: hidden; }
        .dc-bfill { height: 100%; border-radius: 4px; }
        .dc-bval { font-size: 10px; font-weight: 700; color: #cfd4dc; width: 34px; text-align: right;
            flex: 0 0 auto; font-variant-numeric: tabular-nums; }

        /* Sidebar: filtros como pills, acento rojo cuando están activos */
        section[data-testid="stSidebar"] .stRadio label {
            border-radius: 20px !important;
            padding: 3px 12px !important;
            transition: all .15s ease;
        }
        section[data-testid="stSidebar"] .stRadio label:hover {
            border-color: #555 !important;
            background: rgba(255,255,255,0.06) !important;
        }
        section[data-testid="stSidebar"] .stRadio label:has(input:checked) {
            background: linear-gradient(180deg, rgba(255,45,45,.20), rgba(255,45,45,.07)) !important;
            border-color: rgba(255,45,45,.55) !important;
            color: #fff !important;
            box-shadow: 0 0 10px rgba(255,45,45,.15);
        }
        /* Encabezados de sección del sidebar (### ...) con acento */
        section[data-testid="stSidebar"] h3 {
            border-left: 3px solid #FF2D2D;
            padding-left: 9px;
            margin-top: 6px;
        }
        /* Títulos de sección del área principal = placa de acento (broadcast) */
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] h3,
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] h4 {
            border-left: 3px solid #FF2D2D;
            padding-left: 12px;
            letter-spacing: .4px;
        }
        /* st.markdown("**TÍTULO**") = párrafo que SOLO contiene negrita → placa de acento */
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] p:has(> strong:only-child) {
            border-left: 3px solid #FF2D2D;
            padding-left: 12px;
            margin: 16px 0 6px 0;
        }
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] p:has(> strong:only-child) > strong {
            text-transform: uppercase;
            letter-spacing: .8px;
            font-size: 13.5px;
            font-weight: 700;
            color: #eef0f3;
        }
        /* ── Animaciones sutiles ── */
        @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .driver-card { animation: fadeUp .45s cubic-bezier(.2,.7,.3,1) both; }
        .stTabs [data-baseweb="tab-panel"] > div { animation: fadeIn .3s ease both; }
        /* transiciones suaves en controles interactivos */
        .stButton button, .stDownloadButton button,
        section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
        .stSlider [role="slider"] { transition: all .18s ease; }
        .stButton button:hover { transform: translateY(-1px); }

        /* Buttons: clean */

        button[kind="primary"] {

            background: linear-gradient(180deg, #2b2b2b, #232323) !important;

            border: 1px solid #3a3a3a !important;

            border-radius: 4px;

            color: #fff !important;

            font-family: 'Roboto', sans-serif !important;

            font-weight: 500;

        }

        /* Tables: minimal horizontal rules */

        table { border-collapse: collapse; width: 100%; }

        th { text-align: left; color: #aaa; font-weight: 600; padding: 10px 8px; font-family: 'Roboto', sans-serif; }

        td { color: #ddd; padding: 8px 8px; }

        tr + tr td { border-top: 1px solid rgba(255,255,255,0.03); }

        /* Insight boxes */
        .insight-box {
            background: rgba(255,255,255,0.03);
            border: 1px solid #333;
            border-left: 3px solid #4a9eff;
            border-radius: 6px;
            padding: 14px 18px;
            margin: 10px 0;
            font-family: 'Roboto', sans-serif;
        }
        .insight-title {
            color: #4a9eff;
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 6px;
        }
        .insight-box p, .insight-box span {
            color: #ccc;
            font-size: 13px;
            line-height: 1.5;
        }

        /* Contenido principal más ANCHO: menos padding lateral y superior, así las
           gráficas se pegan hacia el sidebar (pilotos) y aprovechan todo el ancho. */
        .stMainBlockContainer, .block-container {
            padding-left: 1.2rem !important;
            padding-right: 1.2rem !important;
            padding-top: 2.2rem !important;
            max-width: 100% !important;
        }

    </style>

    """), unsafe_allow_html=True)
