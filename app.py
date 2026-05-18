# ═══════════════════════════════════════════════════════════════════════════════
#  EPE Chile SpA — Sistema de Reclutamiento Piloto B2C
#  Formulario web con control de cuotas en tiempo real
#  Backend: Google Sheets  |  Deploy: Streamlit Cloud
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date
import json

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="EPE Chile | Reclutamiento Piloto",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Constantes del diseño muestral (20-79 años, n=500) ──────────────────────
RANGOS = [
    "20-24","25-29","30-34","35-39","40-44","45-49",
    "50-54","55-59","60-64","65-69","70-74","75-79",
]
CUOTA_M = dict(zip(RANGOS, [23,27,30,26,24,23,21,20,18,16,12,8]))
CUOTA_H = dict(zip(RANGOS, [23,27,29,26,24,23,21,21,19,16,13,10]))

GRUPOS = {
    "20-24": "Adultos jóvenes",
    "25-29": "Adultos jóvenes activos",
    "30-34": "Adultos en formación",
    "35-39": "Adultos en plenitud",
    "40-44": "Adultos en plenitud laboral",
    "45-49": "Adultos maduros",
    "50-54": "Adultos maduros activos",
    "55-59": "Próximos a la jubilación",
    "60-64": "Jubilados recientes",
    "65-69": "Adultos mayores activos",
    "70-74": "Adultos mayores",
    "75-79": "Adultos mayores plenos",
}

REGIONES = [
    "Arica y Parinacota","Tarapacá","Antofagasta","Atacama","Coquimbo",
    "Valparaíso","Metropolitana","O'Higgins","Maule","Ñuble","Biobío",
    "La Araucanía","Los Ríos","Los Lagos","Aysén","Magallanes",
]
CANALES = [
    "Universidad / CFT","Instagram / TikTok","LinkedIn","Empresa B2B",
    "Caja de Compensación","Mutual","Municipalidad","Referido","Otro",
]
NIVEL_ED = [
    "Educación media","Técnico profesional","Universitaria incompleta",
    "Universitaria completa","Postgrado",
]

HEADERS = [
    "ID","Fecha registro","Nombre completo","RUT","Email","Teléfono",
    "Reclutador","Canal captación","Fecha nacimiento","Edad","Rango etario",
    "Sexo","Región","Comuna","Ocupación","Nivel educacional",
    "Empresa / Universidad","Grupo objetivo","Smartphone con internet",
    "Disposición 60 días","Consentimiento firmado","En otro piloto similar",
    "Diagnóstico severo activo","Uso autónomo smartphone",
    "Elegible","Motivo no elegible","Estado",
]

# ── Helpers ──────────────────────────────────────────────────────────────────
def get_rango(edad: int) -> str:
    for r in RANGOS:
        lo, hi = map(int, r.split("-"))
        if lo <= edad <= hi:
            return r
    return "Fuera de rango"

def get_edad(fecha_nac: date) -> int:
    hoy = date.today()
    return hoy.year - fecha_nac.year - (
        (hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day)
    )

# ── Conexión Google Sheets ───────────────────────────────────────────────────
@st.cache_resource
def get_worksheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["spreadsheet_id"])
    ws = sh.sheet1
    # Inicializar cabeceras si la hoja está vacía
    if ws.row_count == 0 or not ws.row_values(1):
        ws.append_row(HEADERS)
    return ws

@st.cache_data(ttl=25)
def cargar_conteos() -> dict:
    """Retorna {rango: {'F': int, 'M': int}} con participantes elegibles."""
    ws = get_worksheet()
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    conteos = {r: {"F": 0, "M": 0} for r in RANGOS}
    if df.empty or "Rango etario" not in df.columns:
        return conteos
    elegibles = df[df.get("Elegible", pd.Series(dtype=str)) == "Sí"]
    for _, row in elegibles.iterrows():
        rng  = row.get("Rango etario", "")
        sexo = row.get("Sexo", "")
        if rng in conteos:
            if sexo == "Femenino":
                conteos[rng]["F"] += 1
            elif sexo == "Masculino":
                conteos[rng]["M"] += 1
    return conteos

def registrar_participante(data: dict):
    ws = get_worksheet()
    records = ws.get_all_records()
    next_id = len(records) + 1
    fila = [
        next_id,
        date.today().strftime("%d/%m/%Y"),
        data["nombre"],
        data["rut"],
        data["email"],
        data["telefono"],
        data["reclutador"],
        data["canal"],
        data["fecha_nac"].strftime("%d/%m/%Y"),
        data["edad"],
        data["rango"],
        data["sexo"],
        data["region"],
        data["comuna"],
        data["ocupacion"],
        data["nivel_ed"],
        data["empresa"],
        data["grupo"],
        data["smartphone"],
        data["disposicion"],
        data["consentimiento"],
        data["otro_piloto"],
        data["diagnostico"],
        data["uso_autonomo"],
        data["elegible"],
        data["motivo"],
        "Postulante",
    ]
    ws.append_row(fila, value_input_option="USER_ENTERED")
    cargar_conteos.clear()

# ── Estilos CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Fondo general */
[data-testid="stAppViewContainer"] { background: #F0F4FA; }
[data-testid="stHeader"] { background: transparent; }

/* Header principal */
.epe-header {
    background: linear-gradient(135deg, #1F4E79 0%, #2E75B6 100%);
    color: white; padding: 28px 36px; border-radius: 14px;
    margin-bottom: 28px; box-shadow: 0 4px 16px rgba(31,78,121,0.18);
}
.epe-header h1 { margin: 0; font-size: 1.75rem; letter-spacing: -0.3px; }
.epe-header p  { margin: 6px 0 0; opacity: 0.88; font-size: 0.95rem; }

/* Tarjetas de cupo */
.quota-card {
    border-radius: 10px; padding: 10px 8px; text-align: center;
    font-size: 0.82rem; font-weight: 700; margin: 2px 0;
    border: 1.5px solid transparent; line-height: 1.4;
}
.card-green  { background:#D5F5E3; color:#1A5E34; border-color:#52BE80; }
.card-yellow { background:#FEF9E7; color:#7D6608; border-color:#F4D03F; }
.card-red    { background:#FDEDEC; color:#922B21; border-color:#E74C3C; }

/* Secciones */
.section-title {
    font-size: 1.05rem; font-weight: 700; color: #1F4E79;
    border-left: 4px solid #2E75B6; padding-left: 10px;
    margin: 24px 0 14px;
}

/* Alertas de cupo */
.alerta {
    padding: 13px 18px; border-radius: 10px; margin: 12px 0;
    font-weight: 600; font-size: 0.97rem; line-height: 1.5;
}
.alerta-ok     { background:#D5F5E3; color:#1A5E34; border:1.5px solid #52BE80; }
.alerta-warn   { background:#FEF9E7; color:#7D6608; border:1.5px solid #F4D03F; }
.alerta-full   { background:#FDEDEC; color:#922B21; border:1.5px solid #E74C3C; }
.alerta-info   { background:#EAF2FB; color:#1A5276; border:1.5px solid #5DADE2; }

/* Métricas resumen */
.resumen-box {
    background: white; border-radius: 12px; padding: 16px 20px;
    text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border-top: 4px solid #2E75B6;
}
.resumen-box .num { font-size: 2rem; font-weight: 800; color: #1F4E79; }
.resumen-box .lbl { font-size: 0.8rem; color: #6B7280; margin-top: 2px; }

/* Formulario */
.form-section {
    background: white; border-radius: 14px; padding: 24px 28px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06); margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="epe-header">
    <h1>🧬 EPE Chile — Reclutamiento Piloto B2C</h1>
    <p>Portal de ingreso de participantes · Control de cuotas en tiempo real · Meta: 500 personas (20–79 años)</p>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD DE CUOTAS
# ════════════════════════════════════════════════════════════════════════════
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.markdown('<div class="section-title">📊 Estado de Cuotas en Tiempo Real</div>',
                unsafe_allow_html=True)
with col_refresh:
    st.write("")
    if st.button("🔄 Actualizar", use_container_width=True):
        cargar_conteos.clear()
        st.rerun()

conteos = cargar_conteos()

total_recl = sum(v["F"] + v["M"] for v in conteos.values())
total_m    = sum(v["F"] for v in conteos.values())
total_h    = sum(v["M"] for v in conteos.values())
restantes  = 500 - total_recl
pct        = int(total_recl / 500 * 100)

# Métricas resumen
m1, m2, m3, m4, m5 = st.columns(5)
for col, num, lbl, color in [
    (m1, f"{total_recl} / 500", "Total reclutados",   "#2E75B6"),
    (m2, f"{pct}%",             "Avance piloto",       "#2E75B6"),
    (m3, f"{total_m} / 248",    "Mujeres elegibles",   "#C0392B"),
    (m4, f"{total_h} / 252",    "Hombres elegibles",   "#1A5276"),
    (m5, str(restantes),        "Cupos restantes",     "#1A5E34"),
]:
    col.markdown(f"""
    <div class="resumen-box" style="border-top-color:{color}">
        <div class="num" style="color:{color}">{num}</div>
        <div class="lbl">{lbl}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Grid de cuotas por rango
h0, h1, h2, h3, h4, h5, h6 = st.columns([2.8, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
for col, txt in zip(
    [h0, h1, h2, h3, h4, h5, h6],
    ["**Rango · Grupo**", "**Recl. M**", "**Cuota M**", "**Resta M**",
     "**Recl. H**", "**Cuota H**", "**Resta H**"]
):
    col.markdown(txt)

st.markdown("<hr style='margin:6px 0'>", unsafe_allow_html=True)

for rng in RANGOS:
    cm = CUOTA_M[rng]; ch = CUOTA_H[rng]
    rm = conteos[rng]["F"]; rh = conteos[rng]["M"]
    rest_m = max(0, cm - rm); rest_h = max(0, ch - rh)

    def cls(recl, cuota):
        if recl >= cuota:          return "card-red"
        elif recl / cuota >= 0.8:  return "card-yellow"
        else:                       return "card-green"

    def etiqueta(recl, cuota):
        if recl >= cuota:          return f"{recl}/{cuota} 🔴"
        elif recl / cuota >= 0.8:  return f"{recl}/{cuota} ⚠️"
        else:                       return f"{recl}/{cuota} ✅"

    c0, c1, c2, c3, c4, c5, c6 = st.columns([2.8, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2])
    c0.markdown(f"**{rng}** &nbsp; <span style='color:#6B7280;font-size:0.82rem'>{GRUPOS[rng]}</span>",
                unsafe_allow_html=True)
    c1.markdown(f'<div class="quota-card {cls(rm,cm)}">{etiqueta(rm,cm)}</div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="quota-card card-green" style="background:#EAF2FB;color:#1A5276;border-color:#5DADE2">{cm}</div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="quota-card {"card-red" if rest_m==0 else "card-green"}">{rest_m}</div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="quota-card {cls(rh,ch)}">{etiqueta(rh,ch)}</div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="quota-card card-green" style="background:#EAF2FB;color:#1A5276;border-color:#5DADE2">{ch}</div>', unsafe_allow_html=True)
    c6.markdown(f'<div class="quota-card {"card-red" if rest_h==0 else "card-green"}">{rest_h}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN PREVIA DE CUPO
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">🔍 Paso 1 — Verifica el cupo antes de registrar</div>',
            unsafe_allow_html=True)

st.markdown("""
<div class="alerta alerta-info">
    ⚠️ <b>Regla de oro:</b> Antes de ingresar los datos completos del candidato,
    verifica aquí si su rango etario + sexo tiene cupo disponible.
    Si la celda está <b>ROJA (LLENO)</b>, no se acepta a este participante.
</div>
""", unsafe_allow_html=True)

v1, v2 = st.columns(2)
with v1:
    pre_fecha = st.date_input(
        "📅 Fecha de nacimiento del candidato",
        value=None,
        min_value=date(1945, 1, 1),
        max_value=date(2006, 12, 31),
        help="Debe tener entre 20 y 79 años",
        format="DD/MM/YYYY",
    )
with v2:
    pre_sexo = st.selectbox(
        "⚥ Sexo",
        ["— seleccionar —", "Femenino", "Masculino"],
    )

show_form = False

if pre_fecha and pre_sexo != "— seleccionar —":
    edad_pre  = get_edad(pre_fecha)
    rango_pre = get_rango(edad_pre)
    sexo_key  = "F" if pre_sexo == "Femenino" else "M"

    if rango_pre == "Fuera de rango":
        st.markdown(f"""
        <div class="alerta alerta-full">
            ⛔ <b>PARTICIPANTE NO ELEGIBLE</b><br>
            Edad calculada: {edad_pre} años — fuera del rango objetivo (20-79 años).<br>
            <b>No registres a esta persona.</b>
        </div>""", unsafe_allow_html=True)

    else:
        cuota   = CUOTA_M[rango_pre] if sexo_key == "F" else CUOTA_H[rango_pre]
        recl    = conteos.get(rango_pre, {}).get(sexo_key, 0)
        restante = max(0, cuota - recl)
        grupo   = GRUPOS[rango_pre]
        pct_r   = recl / cuota if cuota else 0

        if restante == 0:
            st.markdown(f"""
            <div class="alerta alerta-full">
                🔴 <b>CUOTA LLENA — No aceptar</b><br>
                Rango <b>{rango_pre}</b> ({grupo}) · {pre_sexo}<br>
                Cupos: {recl}/{cuota} — completados al 100%.<br>
                <b>No registres a esta persona en este segmento.</b>
            </div>""", unsafe_allow_html=True)

        elif pct_r >= 0.8:
            st.markdown(f"""
            <div class="alerta alerta-warn">
                ⚠️ <b>CUPO CASI LLENO — Procede con cuidado</b><br>
                Rango <b>{rango_pre}</b> ({grupo}) · {pre_sexo} · Edad: {edad_pre} años<br>
                Quedan <b>{restante} cupo(s)</b> de {cuota} — {int(pct_r*100)}% completado.<br>
                Puedes registrar, pero revisa que sea la persona correcta.
            </div>""", unsafe_allow_html=True)
            show_form = True

        else:
            st.markdown(f"""
            <div class="alerta alerta-ok">
                ✅ <b>CUPO DISPONIBLE — Puedes registrar</b><br>
                Rango <b>{rango_pre}</b> ({grupo}) · {pre_sexo} · Edad: {edad_pre} años<br>
                Quedan <b>{restante} cupo(s)</b> de {cuota} disponibles ({int(pct_r*100)}% completado).
            </div>""", unsafe_allow_html=True)
            show_form = True

elif pre_fecha or pre_sexo != "— seleccionar —":
    st.markdown("""
    <div class="alerta alerta-info">
        Completa <b>fecha de nacimiento</b> y <b>sexo</b> para verificar el cupo disponible.
    </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# FORMULARIO DE REGISTRO
# ════════════════════════════════════════════════════════════════════════════
if show_form:
    edad_calc  = get_edad(pre_fecha)
    rango_calc = get_rango(edad_calc)
    grupo_calc = GRUPOS.get(rango_calc, "")

    st.markdown('<div class="section-title">📝 Paso 2 — Completa los datos del participante</div>',
                unsafe_allow_html=True)

    st.info(
        f"👤 **Edad calculada:** {edad_calc} años  ·  "
        f"**Rango:** {rango_calc}  ·  "
        f"**Grupo:** {grupo_calc}  ·  "
        f"**Sexo:** {pre_sexo}"
    )

    with st.form("registro", clear_on_submit=True):

        # ── Identificación ──────────────────────────────────────────────────
        st.markdown("#### 🪪 Identificación")
        a1, a2, a3 = st.columns(3)
        nombre = a1.text_input("Nombre completo *")
        rut    = a2.text_input("RUT *", placeholder="12.345.678-9")
        email  = a3.text_input("Email *", placeholder="nombre@correo.cl")

        b1, b2, b3 = st.columns(3)
        telefono   = b1.text_input("Teléfono", placeholder="+56 9 1234 5678")
        reclutador = b2.text_input("Nombre del reclutador *")
        canal      = b3.selectbox("Canal de captación *", CANALES)

        # ── Ubicación ───────────────────────────────────────────────────────
        st.markdown("#### 📍 Ubicación")
        c1, c2 = st.columns(2)
        region = c1.selectbox("Región *", REGIONES)
        comuna = c2.text_input("Comuna *")

        # ── Perfil ──────────────────────────────────────────────────────────
        st.markdown("#### 👔 Perfil")
        d1, d2, d3 = st.columns(3)
        ocupacion = d1.text_input("Ocupación")
        nivel_ed  = d2.selectbox("Nivel educacional", NIVEL_ED)
        empresa   = d3.text_input("Empresa / Universidad")

        # ── Criterios de elegibilidad ────────────────────────────────────────
        st.markdown("#### ✅ Criterios de elegibilidad")
        st.caption("Todos los campos marcados con * son obligatorios para determinar elegibilidad.")

        e1, e2, e3 = st.columns(3)
        smartphone     = e1.radio("¿Smartphone con internet? *",
                                  ["Sí", "No"], horizontal=True)
        disposicion    = e2.radio("¿Disponibilidad 60 días? *",
                                  ["Sí", "No"], horizontal=True)
        consentimiento = e3.radio("¿Consentimiento firmado? *",
                                  ["Sí", "No"], horizontal=True)

        f1, f2, f3 = st.columns(3)
        otro_piloto  = f1.radio("¿En otro piloto similar? *",
                                ["No", "Sí"], horizontal=True)
        diagnostico  = f2.radio("¿Diagnóstico severo activo? *",
                                ["No", "Sí"], horizontal=True)
        uso_autonomo = f3.radio("¿Uso autónomo del smartphone? *",
                                ["Sí", "No"], horizontal=True)

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            "✅ Registrar participante",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            # Validación de campos requeridos
            faltantes = []
            if not nombre:     faltantes.append("Nombre completo")
            if not rut:        faltantes.append("RUT")
            if not email:      faltantes.append("Email")
            if not reclutador: faltantes.append("Nombre del reclutador")
            if not comuna:     faltantes.append("Comuna")

            if faltantes:
                st.error(f"⚠️ Completa los campos obligatorios: **{', '.join(faltantes)}**")
            else:
                # Calcular elegibilidad
                elegible = (
                    rango_calc != "Fuera de rango"
                    and smartphone    == "Sí"
                    and disposicion   == "Sí"
                    and consentimiento == "Sí"
                    and otro_piloto   == "No"
                    and diagnostico   == "No"
                    and uso_autonomo  == "Sí"
                )
                motivos = []
                if rango_calc == "Fuera de rango": motivos.append("Edad fuera 20-79")
                if smartphone    == "No":  motivos.append("Sin smartphone")
                if disposicion   == "No":  motivos.append("No dispone 60 días")
                if consentimiento == "No": motivos.append("Sin consentimiento")
                if otro_piloto   == "Sí":  motivos.append("En otro piloto")
                if diagnostico   == "Sí":  motivos.append("Diagnóstico severo activo")
                if uso_autonomo  == "No":  motivos.append("No uso autónomo smartphone")

                data = dict(
                    nombre=nombre, rut=rut, email=email, telefono=telefono,
                    reclutador=reclutador, canal=canal,
                    fecha_nac=pre_fecha, edad=edad_calc, rango=rango_calc,
                    sexo=pre_sexo, region=region, comuna=comuna,
                    ocupacion=ocupacion, nivel_ed=nivel_ed, empresa=empresa,
                    grupo=grupo_calc, smartphone=smartphone,
                    disposicion=disposicion, consentimiento=consentimiento,
                    otro_piloto=otro_piloto, diagnostico=diagnostico,
                    uso_autonomo=uso_autonomo,
                    elegible="Sí" if elegible else "No",
                    motivo="; ".join(motivos) if motivos else "",
                )

                try:
                    registrar_participante(data)
                    if elegible:
                        st.success(
                            f"🎉 **Participante registrado exitosamente.**\n\n"
                            f"**{nombre}** es **ELEGIBLE** para el piloto · "
                            f"Rango {rango_calc} · {pre_sexo}"
                        )
                        st.balloons()
                    else:
                        st.warning(
                            f"⚠️ **{nombre}** fue registrado pero **NO es elegible**.\n\n"
                            f"Motivo(s): {'; '.join(motivos)}"
                        )
                except Exception as err:
                    st.error(f"❌ Error al guardar en Google Sheets: {err}")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"🔬 EPE Chile SpA · Piloto B2C · "
    f"Fuente demográfica: Proyecciones INE 2023 (base Censo 2017) · "
    f"{date.today().strftime('%Y')}"
)
