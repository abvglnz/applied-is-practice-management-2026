import os
from datetime import date

import pandas as pd
import requests
import streamlit as st

BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
TIMEOUT = 6

st.set_page_config(page_title="Практиканы басқару", page_icon="🎓", layout="wide")
dark_mode = st.sidebar.toggle("Қараңғы режим", key="dark_mode")
theme = """
:root { --bg:#f5f5f5; --surface:#ffffff; --surface2:#fafafa; --ink:#252b34;
  --muted:#707780; --line:#dedede; --accent:#3563a5; --accent-soft:#edf2f8;
  --nav:#505a69; --hero:#132447; --good:#238466; }
""" if not dark_mode else """
:root { --bg:#181b21; --surface:#22262e; --surface2:#292e37; --ink:#e7e9ed;
  --muted:#a2aab7; --line:#3c424d; --accent:#94b5e4; --accent-soft:#273346;
  --nav:#b8c0ce; --hero:#101b32; --good:#7cd7bc; }
"""
st.markdown(
    f"""<style>
    {theme}
    .stApp {{ background:var(--bg); color:var(--ink); }}
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {{ visibility:hidden; }}
    [data-testid="stAppViewContainer"] {{ background:var(--bg); }}
    [data-testid="stSidebar"] {{ background:var(--surface); border-right:1px solid var(--line); }}
    [data-testid="stSidebar"] > div:first-child {{ padding-top:1.4rem; }}
    .block-container {{ padding:1.6rem 2.5rem 3rem; max-width:1550px; }}
    h1,h2,h3,p,span,label {{ color:var(--ink); }}
    h1 {{ font-size:1.75rem!important; letter-spacing:-.5px; }}
    h2 {{ font-size:1.15rem!important; }}
    [data-testid="stSidebar"] .stRadio label {{ color:var(--nav); font-size:.91rem; }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ color:var(--muted); }}
    .brand {{ font-size:1.05rem; font-weight:700; margin:0 0 1.8rem .2rem; color:var(--ink); }}
    .brand-mark {{ display:inline-grid; place-items:center; width:32px; height:32px; margin-right:9px;
      background:var(--accent); color:white; border-radius:9px; font-size:17px; }}
    .side-caption {{ font-size:.66rem; letter-spacing:1.3px; color:var(--muted); margin:0 0 .6rem .2rem; }}
    .side-footer {{ border-top:1px solid var(--line); margin-top:2rem; padding-top:1rem;
      color:var(--muted); font-size:.75rem; line-height:1.7; }}
    .topline {{ display:flex; align-items:center; justify-content:space-between; padding:0 0 1.1rem;
      margin-bottom:1.25rem; border-bottom:1px solid var(--line); }}
    .topline small {{ color:var(--muted); font-size:.72rem; }}
    .topline strong {{ display:block; font-size:.92rem; color:var(--ink); }}
    .pill {{ display:inline-block; color:var(--accent); background:var(--accent-soft);
      padding:5px 10px; border-radius:4px; font-size:.7rem; }}
    .hero {{ display:flex; justify-content:space-between; align-items:center; gap:1rem; color:#f4f6ff;
      background:var(--hero); border-radius:12px; padding:1.7rem 2rem; margin:.4rem 0 1.3rem; }}
    .hero * {{ color:#f4f6ff!important; }}
    .hero .eyebrow {{ color:#aebaff!important; font-size:.68rem; letter-spacing:1.4px; }}
    .hero h2 {{ font-size:1.5rem!important; margin:.4rem 0; }}
    .hero p {{ color:#abb9d5!important; margin:.35rem 0 0; font-size:.85rem; }}
    .hero-mark {{ font-size:3.5rem; opacity:.75; padding:0 1rem; }}
    [data-testid="stMetric"] {{ background:var(--surface); border:1px solid var(--line);
      border-radius:9px; padding:.9rem 1rem; }}
    [data-testid="stMetricLabel"] {{ color:var(--muted)!important; font-size:.76rem; }}
    [data-testid="stMetricValue"] {{ color:var(--ink)!important; font-size:1.7rem; }}
    [data-testid="stDataFrame"] {{ border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
    .stButton button {{ border-radius:5px; border-color:var(--line); }}
    .stButton button[kind="primary"] {{ background:var(--accent); border-color:var(--accent); color:white; }}
    [data-testid="stForm"] {{ background:var(--surface); border:1px solid var(--line);
      border-radius:9px; padding:1rem; }}
    input, textarea, [data-baseweb="select"] > div {{ border-radius:5px!important; }}
    hr {{ border-color:var(--line); }}
    div[data-testid="stAlert"] {{ border-radius:6px; }}
    @media(max-width:760px) {{ .block-container {{ padding:.9rem 1rem 2rem; }}
      .hero {{ padding:1.2rem; }} .hero-mark {{ display:none; }} }}
    </style>""",
    unsafe_allow_html=True,
)

st.sidebar.markdown('<div class="brand"><span class="brand-mark">П</span>Практиканы басқару</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="side-caption">ПРАКТИКАНЫ БАСҚАРУ</div>', unsafe_allow_html=True)
section = st.sidebar.radio(
    "Бөлімді таңдаңыз",
    ["Шолу", "Практикалар", "Жоба туралы"],
    format_func=lambda item: {"Шолу": "⌂　Шолу", "Практикалар": "▤　Практикалар", "Жоба туралы": "ⓘ　Жоба туралы"}[item],
    label_visibility="collapsed",
    key="section",
)
st.sidebar.markdown(
    '<div class="side-footer">●　Оқу жобасы · №2 нұсқа<br><br>Кәсіби практика<br>жетекшісінің АЖО</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="topline"><div><small>Ақпараттық жүйелер кафедрасы</small><strong>Кәсіби практика</strong></div>'
    '<span class="pill">Жергілікті жүйе</span></div>',
    unsafe_allow_html=True,
)


def api_get(path: str, params: dict | None = None):
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def show_api_error(error: Exception):
    if isinstance(error, requests.HTTPError) and error.response is not None:
        try:
            detail = error.response.json().get("detail", "Сұрау орындалмады.")
        except ValueError:
            detail = "Серверден дұрыс жауап келмеді."
        st.error(str(detail))
    else:
        st.error("API серверіне қосыла алмадым. Бэкендтің іске қосылғанын тексеріңіз.")


try:
    students = api_get("/students")
    bases = api_get("/bases")
    supervisors = api_get("/supervisors")
    contracts = api_get("/contracts")
    all_placements = api_get("/placements")
except requests.RequestException as exc:
    show_api_error(exc)
    st.code("uvicorn course_backend.main:app --reload")
    st.stop()

if section == "Шолу":
    st.markdown(
        '<div class="hero"><div><span class="eyebrow">№2 ОҚУ ЖОБАСЫ</span>'
        '<h2>Кәсіби практиканы есепке алу</h2>'
        '<p>Студенттерді практикаға бөлу, мерзімдерді бақылау және жетекшілер жұмысын үйлестіру.</p>'
        '</div><div class="hero-mark">⌂</div></div>',
        unsafe_allow_html=True,
    )
    total_students = len({row["student_id"] for row in all_placements})
    total_bases = len({row["base_id"] for row in all_placements})
    total_supervisors = len({row["supervisor_id"] for row in all_placements})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Практика жазбалары", len(all_placements))
    c2.metric("Қамтылған студенттер", total_students)
    c3.metric("Практика базалары", total_bases)
    c4.metric("Жетекшілер", total_supervisors)
    st.write("")
    st.subheader("Соңғы практика жазбалары")
    if all_placements:
        table = pd.DataFrame(all_placements).rename(
            columns={"id": "ID", "student_name": "Студент", "base_name": "Практика базасы",
                     "supervisor_name": "Жетекші", "kind": "Практика түрі",
                     "start_date": "Басталу күні", "end_date": "Аяқталу күні"}
        )[["ID", "Студент", "Практика базасы", "Жетекші", "Практика түрі", "Басталу күні", "Аяқталу күні"]]
        st.dataframe(table, width="stretch", hide_index=True)
    else:
        st.info("Практика жазбалары әлі жоқ.")
    if st.button("Практикаларды басқару →", type="primary"):
        st.session_state["section"] = "Практикалар"
        st.rerun()

elif section == "Практикалар":
    st.title("Практикалар")
    st.caption("Тізімді іздеңіз, жаңа бөлініс қосыңыз немесе бар жазбаны өзгертіңіз.")
    filter_left, filter_right = st.columns([2, 1])
    search = filter_left.text_input("Студент, топ немесе практика базасы бойынша іздеу")
    kinds = ["Барлығы"] + sorted({row["kind"] for row in all_placements})
    selected_kind = filter_right.selectbox("Практика түрі", kinds)
    filters = {"search": search} if search else {}
    if selected_kind != "Барлығы":
        filters["kind"] = selected_kind
    try:
        placements = api_get("/placements", params=filters)
    except requests.RequestException as exc:
        show_api_error(exc)
        placements = []

    if placements:
        frame = pd.DataFrame(placements).rename(
            columns={"id": "ID", "student_name": "Студент", "base_name": "Практика базасы",
                     "supervisor_name": "Жетекші", "kind": "Практика түрі",
                     "start_date": "Басталу күні", "end_date": "Аяқталу күні"}
        )[["ID", "Студент", "Практика базасы", "Жетекші", "Практика түрі", "Басталу күні", "Аяқталу күні"]]
        st.dataframe(frame, width="stretch", hide_index=True)
    else:
        st.info("Сүзгіге сәйкес практика табылмады.")

    st.divider()
    col_add, col_delete = st.columns(2)
    with col_add:
        st.subheader("Практикаға бөлу")
        with st.form("placement_form", clear_on_submit=True):
            student = st.selectbox("Студент", students, format_func=lambda row: row["name"])
            base = st.selectbox("Практика базасы", bases, format_func=lambda row: row["name"])
            supervisor = st.selectbox("Жетекші", supervisors, format_func=lambda row: row["name"])
            contract = st.selectbox("Келісімшарт", contracts, format_func=lambda row: row["name"])
            kind = st.selectbox("Практика түрі", ["Оқу практикасы", "Өндірістік практика", "Дипломалды практика"])
            start_date = st.date_input("Басталу күні")
            end_date = st.date_input("Аяқталу күні")
            submitted = st.form_submit_button("Практикаға бөлу", type="primary")
        if submitted:
            payload = {"student_id": student["id"], "base_id": base["id"],
                       "supervisor_id": supervisor["id"], "contract_id": contract["id"],
                       "kind": kind, "start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
            try:
                response = requests.post(f"{BASE_URL}/placements", json=payload, timeout=TIMEOUT)
                response.raise_for_status()
                st.success("Практика сәтті тіркелді.")
                st.rerun()
            except requests.RequestException as exc:
                show_api_error(exc)

    with col_delete:
        st.subheader("Жазбаны жою")
        if placements:
            options = {row["id"]: f"#{row['id']} · {row['student_name']} · {row['base_name']}" for row in placements}
            delete_id = st.selectbox("Жойылатын практика", list(options), format_func=lambda key: options[key])
            confirmed = st.checkbox("Жоюды растаймын")
            if st.button("Таңдалған жазбаны жою", disabled=not confirmed):
                try:
                    response = requests.delete(f"{BASE_URL}/placements/{delete_id}", timeout=TIMEOUT)
                    response.raise_for_status()
                    st.success("Жазба жойылды.")
                    st.rerun()
                except requests.RequestException as exc:
                    show_api_error(exc)
        else:
            st.caption("Жоюға болатын жазба жоқ.")

    if placements:
        st.divider()
        st.subheader("Практика мерзімін өзгерту")
        options = {row["id"]: f"#{row['id']} · {row['student_name']} · {row['kind']}" for row in placements}
        edit_id = st.selectbox("Өзгертілетін практика", list(options), format_func=lambda key: options[key], key="edit_placement")
        current = next(row for row in placements if row["id"] == edit_id)
        with st.form("edit_placement_form"):
            new_kind = st.text_input("Практика түрі", value=current["kind"])
            new_start = st.date_input("Жаңа басталу күні", value=date.fromisoformat(current["start_date"]))
            new_end = st.date_input("Жаңа аяқталу күні", value=date.fromisoformat(current["end_date"]))
            update = st.form_submit_button("Өзгерісті сақтау")
        if update:
            try:
                response = requests.patch(
                    f"{BASE_URL}/placements/{edit_id}",
                    json={"kind": new_kind, "start_date": new_start.isoformat(), "end_date": new_end.isoformat()},
                    timeout=TIMEOUT,
                )
                response.raise_for_status()
                st.success("Практика ақпараты жаңартылды.")
                st.rerun()
            except requests.RequestException as exc:
                show_api_error(exc)

elif section == "Жоба туралы":
    st.title("Жоба туралы")
    st.caption("Кәсіби практика жетекшісінің автоматтандырылған жұмыс орны")
    st.markdown(
        """
        ### Жүйе не істейді?
        Жүйе студенттердің практикаға бөлінуін, практика базаларын, келісімшарттарды,
        жетекшілерді және практика мерзімдерін бір жерден басқаруға арналған.

        ### Қолданылған технологиялар
        - **Backend:** FastAPI және Uvicorn
        - **Дерекқор:** SQLite және SQLModel
        - **Frontend:** Streamlit және requests
        - **Іске қосу:** Docker Compose

        ### Тексерілетін ережелер
        - Келісімшарт таңдалған практика базасына сәйкес болуы керек.
        - Практиканың күндері келісімшарт мерзіміне сыйуы керек.
        - Бір студентке бір уақытта екі практика тағайындалмайды.
        - Практика базасындағы орын саны асып кетпеуі керек.

        Дерекқордың ER схемасы `docs/ER_DIAGRAM.md` файлында берілген.
        """
    )

st.markdown(
    '<div style="margin-top:2rem;padding-top:1rem;border-top:1px solid var(--line);'
    'font-size:.7rem;color:var(--muted);display:flex;justify-content:space-between">'
    '<span>Ақпараттық жүйелердің қолданбалы бағдарламалық жасақтамасы</span><span>2026</span></div>',
    unsafe_allow_html=True,
)
