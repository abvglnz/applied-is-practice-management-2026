import os
from datetime import date

import pandas as pd
import requests
import streamlit as st

BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
TIMEOUT = 6

st.set_page_config(page_title="Практиканы басқару", page_icon="🎓", layout="wide")
dark_mode = st.session_state.get("dark_mode", False)
theme = """
:root { --bg:#f3f5fa; --surface:#ffffff; --surface2:#f7f8fc; --ink:#15213b;
  --muted:#78839a; --line:#e4e8f0; --accent:#526af4; --accent-soft:#edf0ff;
  --nav:#aeb9cf; --sidebar:#111d33; --hero:#101d37; --good:#35b99d; }
""" if not dark_mode else """
:root { --bg:#101725; --surface:#182235; --surface2:#202c40; --ink:#edf2fb;
  --muted:#9ba9bf; --line:#2b3a52; --accent:#93a3ff; --accent-soft:#293450;
  --nav:#aeb9cf; --sidebar:#0b1322; --hero:#101d37; --good:#7ce0c9; }
"""
st.markdown(
    f"""<style>
    {theme}
    .stApp {{ background:var(--bg); color:var(--ink); }}
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {{ visibility:hidden; }}
    [data-testid="stAppViewContainer"] {{ background:var(--bg); }}
    [data-testid="stSidebar"] {{ background:var(--sidebar); border-right:1px solid #ffffff12; }}
    [data-testid="stSidebar"] > div:first-child {{ padding:1.4rem 1rem 1rem; }}
    .block-container {{ padding:1.8rem 2.7rem 3rem; max-width:1600px; }}
    h1,h2,h3,p,span,label {{ color:var(--ink); }}
    h1 {{ font-size:1.75rem!important; letter-spacing:-.5px; }}
    h2 {{ font-size:1.15rem!important; }}
    [data-testid="stSidebar"] .stRadio label {{ color:var(--nav); font-size:.88rem; padding:.3rem .45rem;
      border-radius:9px; transition:all .18s ease; }}
    [data-testid="stSidebar"] .stRadio label:hover {{ background:#ffffff12; color:#ffffff; }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ color:#aebbd1; }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{ color:#aebbd1!important; }}
    .brand {{ font-size:1.02rem; font-weight:700; margin:0 0 1.8rem .2rem; color:#f5f7fc; }}
    .brand-mark {{ display:inline-grid; place-items:center; width:34px; height:34px; margin-right:9px;
      background:linear-gradient(145deg,#7c8dff,#526af4); color:white; border-radius:11px; font-size:17px;
      box-shadow:0 7px 18px #526af450; }}
    .side-caption {{ font-size:.63rem; letter-spacing:1.5px; color:#71809a; margin:0 0 .55rem .35rem; }}
    .side-footer {{ border-top:1px solid #ffffff18; margin-top:2rem; padding:1rem .35rem 0;
      color:#aebbd1; font-size:.72rem; line-height:1.7; }}
    .topline {{ display:flex; align-items:center; justify-content:space-between; padding:0 0 1rem;
      margin-bottom:1.4rem; border-bottom:1px solid var(--line); }}
    .topline small {{ color:var(--muted); font-size:.72rem; letter-spacing:.2px; }}
    .topline strong {{ display:block; font-size:.92rem; color:var(--ink); margin-top:2px; }}
    .pill {{ display:inline-block; color:var(--good); background:color-mix(in srgb,var(--good) 12%,transparent);
      padding:6px 11px; border-radius:30px; font-size:.7rem; font-weight:650; }}
    .hero {{ display:flex; justify-content:space-between; align-items:center; gap:1rem; color:#f4f6ff;
      background:radial-gradient(circle at 88% 20%,#526af455 0,transparent 28%),
                 linear-gradient(116deg,#101d37 0%,#1b315b 64%,#294786 100%);
      border-radius:17px; padding:2rem 2.2rem; margin:.4rem 0 1.35rem; position:relative; overflow:hidden;
      box-shadow:0 15px 34px #182b4b20; }}
    .hero:after {{ content:''; position:absolute; width:210px; height:210px; right:8%; top:-130px;
      border:1px solid #ffffff25; border-radius:50%; box-shadow:0 0 0 28px #ffffff08,0 0 0 56px #ffffff06; }}
    .hero * {{ color:#f4f6ff!important; }}
    .hero .eyebrow {{ color:#aebaff!important; font-size:.66rem; letter-spacing:1.6px; font-weight:700; }}
    .hero h2 {{ font-size:1.65rem!important; margin:.55rem 0; letter-spacing:-.5px; }}
    .hero p {{ color:#c0cbe2!important; margin:.35rem 0 0; font-size:.84rem; max-width:590px; }}
    .hero-mark {{ font-size:3.6rem; opacity:.85; padding:0 1rem; color:#b9c6ff; z-index:1; }}
    [data-testid="stMetric"] {{ background:var(--surface); border:1px solid var(--line);
      border-radius:13px; padding:1rem 1.05rem; box-shadow:0 8px 22px #23375b0a;
      transition:transform .16s ease,box-shadow .16s ease; }}
    [data-testid="stMetric"]:hover {{ transform:translateY(-2px); box-shadow:0 12px 25px #23375b14; }}
    [data-testid="stMetricLabel"] {{ color:var(--muted)!important; font-size:.74rem; }}
    [data-testid="stMetricValue"] {{ color:var(--ink)!important; font-size:1.8rem; font-weight:700; }}
    [data-testid="stDataFrame"] {{ border:1px solid var(--line); border-radius:11px; overflow:hidden;
      box-shadow:0 8px 22px #23375b08; }}
    .stButton button {{ border-radius:8px; border:1px solid var(--line); min-height:2.55rem;
      font-weight:600; transition:all .15s ease; }}
    .stButton button:hover {{ border-color:var(--accent); color:var(--accent); transform:translateY(-1px); }}
    .stButton button[kind="primary"] {{ background:linear-gradient(120deg,#526af4,#687df7);
      border-color:var(--accent); color:white; box-shadow:0 6px 14px #526af433; }}
    [data-testid="stForm"] {{ background:var(--surface); border:1px solid var(--line);
      border-radius:13px; padding:1.1rem; box-shadow:0 8px 22px #23375b0a; }}
    input, textarea, [data-baseweb="select"] > div {{ border-radius:8px!important; }}
    [data-testid="stTextInput"] input:focus,[data-testid="stDateInput"] input:focus {{
      border-color:var(--accent)!important; box-shadow:0 0 0 2px #526af425!important; }}
    [data-testid="stSubheader"] {{ margin-top:1.15rem; }}
    hr {{ border-color:var(--line); }}
    div[data-testid="stAlert"] {{ border-radius:6px; }}
    @media(max-width:760px) {{ .block-container {{ padding:.9rem 1rem 2rem; }}
      .hero {{ padding:1.25rem; }} .hero-mark {{ display:none; }} }}
    </style>""",
    unsafe_allow_html=True,
)

st.sidebar.markdown('<div class="brand"><span class="brand-mark">П</span>Практиканы басқару</div>', unsafe_allow_html=True)
st.sidebar.toggle("Қараңғы режим", key="dark_mode")
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
        '<div class="hero"><div><span class="eyebrow">№2 ОҚУ ЖОБАСЫ　·　2026</span>'
        '<h2>Кәсіби практиканы есепке алу</h2>'
        '<p>Студенттерді практикаға бөлу, мерзімдерді бақылау және жетекшілер жұмысын үйлестіру.</p>'
        '</div><div class="hero-mark">✦</div></div>',
        unsafe_allow_html=True,
    )
    total_students = len({row["student_id"] for row in all_placements})
    total_bases = len({row["base_id"] for row in all_placements})
    total_supervisors = len({row["supervisor_id"] for row in all_placements})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🗂 Практика жазбалары", len(all_placements))
    c2.metric("🎓 Қамтылған студенттер", total_students)
    c3.metric("🏢 Практика базалары", total_bases)
    c4.metric("👤 Жетекшілер", total_supervisors)
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
