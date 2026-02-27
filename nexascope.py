import re
import streamlit as st
from dataclasses import dataclass
from typing import Optional, Dict, Any

# =========================================================
# NexaScope v2.1 - FREE + PRO (Stripe Payment Link redirect)
# PRO se activa con ?pro=1 (success redirect en Stripe)
# =========================================================

PRICE_EUR = 5.99

# 👇 PEGA AQUÍ tu Stripe Payment Link REAL cuando lo tengas
STRIPE_LINK = "https://buy.stripe.com/fZueV5fNU25MboJ9pQ5J601"

# Detectar modo PRO por parámetro en URL (Streamlit Cloud)
is_pro = st.query_params.get("pro") == "1"


# -------------------------
# Modelo de entrada
# -------------------------
@dataclass
class NexaInput:
    days_active: int
    activity_level: str
    sales_90d: int
    visits_30d: int
    conversations_30d: int
    offers_30d: int
    business_type: str
    sale_flow: str
    outbound_level: str


def normalize_days(raw: str) -> Optional[int]:
    s = (raw or "").strip().lower()
    if not s:
        return None
    if re.fullmatch(r"\d+", s):
        return int(s)

    m = re.search(r"(\d+)", s)
    if not m:
        return None
    n = int(m.group(1))

    if "mes" in s:
        return n * 30
    if "año" in s or "ano" in s:
        return n * 365
    if "sem" in s:
        return n * 7
    if "día" in s or "dia" in s:
        return n
    return None


def outbound_to_int(level: str) -> int:
    return {
        "Ninguna": 0,
        "1–5": 3,
        "6–15": 10,
        "Más de 15": 20,
    }.get(level, 0)


def months_from_days(days: int) -> int:
    return max(1, int(round(days / 30)))


def diagnose(inp: NexaInput) -> Dict[str, Any]:
    months = months_from_days(inp.days_active)

    # -------------------------
    # Diagnóstico principal (estado)
    # -------------------------
    if inp.activity_level == "He estado prácticamente en pausa":
        code = "PAUSA"
        main = "Tu negocio no está siendo probado ahora mismo."
        meaning = (
            f"Aunque tu negocio lleva creado aprox. {months} meses, en los últimos 3 meses "
            "ha estado en pausa o con muy poco movimiento. Sin actividad reciente, no hay base justa "
            "para decir “funciona” o “no funciona”."
        )

    elif inp.sales_90d >= 2:
        code = "SENALES"
        main = "Hay señales reales de que esto sí puede funcionar."
        meaning = (
            f"Has tenido {inp.sales_90d} ventas en los últimos 90 días. "
            "Eso es una señal real: el mercado sí paga, al menos a veces."
        )

    elif inp.sales_90d == 0 and inp.conversations_30d >= 10 and inp.offers_30d >= 10:
        code = "INTERES_SIN_PAGO"
        main = "Hay interés, pero algo está frenando el pago."
        meaning = (
            f"En el último mes tuviste {inp.conversations_30d} conversaciones y {inp.offers_30d} ofertas, "
            "pero 0 ventas. Eso suele significar: la gente se interesa, pero no se decide a pagar."
        )

    else:
        code = "SIN_PRUEBA"
        main = "No hay suficiente prueba clara todavía."
        meaning = (
            f"Tu negocio lleva creado aprox. {months} meses, pero en el último mes no hay suficiente actividad "
            "medible para concluir si el modelo funciona o no."
        )

    # -------------------------
    # Ajuste por tiempo
    # -------------------------
    long_time = inp.days_active >= 18 * 30  # 18 meses+
    was_active = inp.activity_level != "He estado prácticamente en pausa"

    if long_time and was_active and inp.sales_90d == 0 and inp.offers_30d >= 10 and inp.conversations_30d >= 10:
        code = "REPLANTEAR_FUERTE"
        main = "Ya hubo intento real: no conviene seguir igual."
        meaning = (
            f"Llevas aprox. {months} meses con el negocio y en el último mes hubo movimiento real "
            f"({inp.conversations_30d} conversaciones, {inp.offers_30d} ofertas), pero 0 ventas. "
            "Con esa combinación, insistir sin cambiar nada suele ser perder tiempo."
        )

    if long_time and was_active and inp.sales_90d == 0 and inp.offers_30d < 5:
        code = "LARGO_TIEMPO_POCA_PRESION"
        main = "El negocio lleva tiempo, pero no ha tenido presión reciente suficiente."
        meaning = (
            f"Llevas aprox. {months} meses con el negocio, pero en el último mes casi no hubo ofertas claras. "
            "En ese caso, el problema no es “si funciona o no”, sino que no hay una prueba reciente y medible."
        )

    # -------------------------
    # Plan 14 días (por tipo)
    # -------------------------
    if inp.business_type == "Producto físico":
        plan = [
            "Elige UN producto principal y enfoca todo hacia ese producto (no 20 productos a la vez).",
            "Lleva tráfico constante a ese producto (contenido diario o anuncios pequeños).",
            "Mantén el mismo precio y la misma oferta 14 días para medir sin confusión.",
            "La meta es simple: ver si con visitas reales aparece compra."
        ]
    elif inp.business_type == "Servicio":
        plan = [
            "Genera conversaciones reales con personas que encajen con tu cliente ideal.",
            "Haz ofertas claras (precio + qué incluye + cómo se paga).",
            "Si hay interés pero no pagan: ajusta UNA cosa (precio, paquete o tipo de cliente) y vuelve a ofrecer."
        ]
    elif inp.business_type == "Producto digital":
        plan = [
            "Enfoca todo en UNA oferta con promesa clara (qué logra la persona).",
            "Dirige tráfico a esa oferta (contenido o ads).",
            "Mide interés real: clics con intención, registros o compras (no likes)."
        ]
    else:  # SaaS
        plan = [
            "Consigue usuarios reales que prueben el producto (aunque sea gratis al inicio).",
            "Mide si lo usan más de una vez (eso dice más que ‘visitas’).",
            "No agregues funciones todavía: primero valida uso constante."
        ]

    dont = [
        "No cambies 5 cosas a la vez (si cambias todo, nunca sabrás qué funcionó).",
        "No tomes una decisión definitiva sin una prueba reciente clara.",
    ]

    secondary = None
    needs_convo = (inp.business_type == "Servicio") or (inp.sale_flow == "Hablo antes de cerrar")
    outbound = outbound_to_int(inp.outbound_level)
    if needs_convo and outbound == 0:
        secondary = (
            "Tu modelo normalmente necesita conversación directa para cerrar ventas, "
            "pero hoy no estás iniciando conversaciones. Eso, por sí solo, puede explicar el estancamiento."
        )

    if code == "SENALES":
        decision = "✅ Continuar"
        decision_text = (
            "Hay señales reales de pago. No es momento de cerrar. "
            "La prioridad ahora es repetir lo que ya funcionó y hacerlo consistente."
        )
    elif code == "INTERES_SIN_PAGO":
        decision = "🟡 Replantear"
        decision_text = (
            "No conviene cerrar todavía, pero tampoco seguir igual. "
            "Ajusta UNA cosa (oferta, mensaje o precio) y vuelve a probar con el mismo volumen."
        )
    elif code == "REPLANTEAR_FUERTE":
        decision = "🟠 Replantear fuerte (cambio estructural)"
        decision_text = (
            "Con el tiempo y el intento realizado, seguir igual es poco probable que funcione. "
            "Necesitas un cambio de oferta/cliente/precio (elige uno) o un enfoque distinto."
        )
    elif code == "PAUSA":
        decision = "⏸ Pausar o reactivar con intención"
        decision_text = (
            "No hay base reciente para decidir. O lo reactivas con una prueba real de 14 días, "
            "o lo pausas de forma consciente."
        )
    elif code == "LARGO_TIEMPO_POCA_PRESION":
        decision = "🟡 Aún no decidir (primero prueba en serio)"
        decision_text = (
            "Lleva tiempo creado, pero no hay presión reciente suficiente. "
            "Primero haz una prueba real de 14 días antes de cerrar o cambiar todo."
        )
    else:
        decision = "🟡 Aún no decidir"
        decision_text = (
            "Aún no hay una prueba reciente clara para cerrar o continuar con certeza. "
            "Primero necesitas actividad medible durante 14 días."
        )

    preview_map = {
        "PAUSA": "Parece que el negocio ha estado en pausa (y eso cambia la lectura).",
        "SENALES": "Hay una señal positiva: ya existe pago real.",
        "INTERES_SIN_PAGO": "Hay interés, pero no se está convirtiendo en pago.",
        "SIN_PRUEBA": "Falta una prueba reciente clara para concluir.",
        "REPLANTEAR_FUERTE": "Hay una señal fuerte: con este intento, seguir igual no conviene.",
        "LARGO_TIEMPO_POCA_PRESION": "Lleva tiempo creado, pero falta presión reciente para evaluarlo bien.",
    }

    title_pre = "🔎 Resultado inicial"
    hint_pre = (
        f"{preview_map.get(code, 'Hay algo importante que vale la pena revisar.')}\n\n"
        "En el análisis completo te explicamos qué está pasando, qué cambiar primero y qué NO tocar todavía."
    )

    full = {
        "code": code,
        "diagnostico": main,
        "que_significa": meaning,
        "plan_14_dias": plan,
        "no_hagas": dont,
        "observacion_adicional": secondary,
        "decision_final": decision,
        "explicacion_decision": decision_text,
        "months": months,
    }

    return {"title_pre": title_pre, "hint_pre": hint_pre, "full": full}


# =========================================================
# UI
# =========================================================

st.set_page_config(page_title="NexaScope", page_icon="🧠")
st.title("🧠 NexaScope")
st.caption("Diagnóstico claro, sin tecnicismos, adaptado al tipo de negocio.")
st.markdown("---")

time_raw = st.text_input("¿Cuánto tiempo lleva creado el negocio? (ej: 6 meses, 2 años)", "12 meses")
days_active = normalize_days(time_raw)

activity_level = st.selectbox(
    "En los últimos 3 meses, ¿qué tan activo has estado realmente?",
    [
        "He estado activo casi todas las semanas",
        "He estado activo a ratos",
        "He estado prácticamente en pausa"
    ]
)

col1, col2 = st.columns(2)
with col1:
    sales_90d = st.number_input("Ventas en los últimos 3 meses", min_value=0, value=0)
    visits_30d = st.number_input("Visitas en los últimos 30 días (aprox)", min_value=0, value=0)

with col2:
    conversations_30d = st.number_input("Conversaciones reales en 30 días", min_value=0, value=0)
    offers_30d = st.number_input("Ofertas claras hechas en 30 días", min_value=0, value=0)

business_type = st.selectbox("Tipo de negocio", ["Producto físico", "Servicio", "Producto digital", "SaaS"])
sale_flow = st.selectbox("¿Cómo ocurre normalmente la venta?", ["Compra directa en la web", "Hablo antes de cerrar", "Depende"])
outbound_level = st.selectbox("¿Cuántas conversaciones inicias tú activamente al mes?", ["Ninguna", "1–5", "6–15", "Más de 15"])

st.markdown("---")

if "result" not in st.session_state:
    st.session_state.result = None

if st.button("Analizar", type="primary", use_container_width=True):
    if not days_active:
        st.warning("Escribe un tiempo válido (ej: 6 meses, 2 años).")
    else:
        inp = NexaInput(
            days_active=days_active,
            activity_level=activity_level,
            sales_90d=int(sales_90d),
            visits_30d=int(visits_30d),
            conversations_30d=int(conversations_30d),
            offers_30d=int(offers_30d),
            business_type=business_type,
            sale_flow=sale_flow,
            outbound_level=outbound_level
        )
        st.session_state.result = diagnose(inp)

res = st.session_state.result
if res:
    st.subheader(res["title_pre"])
    st.write(res["hint_pre"])

    # ========== BLOQUEO (FREE) ==========
    if not is_pro:
        st.markdown("---")
        st.subheader("🔒 Desbloquea el análisis completo (PRO)")
        st.write("Incluye: plan detallado, errores estratégicos, observación adicional y decisión final clara.")
        st.markdown(f"**Precio: €{PRICE_EUR:.2f}**")

        if "PEGA_AQUI" in STRIPE_LINK:
            st.warning("Pega tu Stripe Payment Link en STRIPE_LINK.")
        else:
            st.link_button("💳 Pagar y ver análisis completo", STRIPE_LINK, use_container_width=True)

        st.info("Después de pagar, Stripe debe redirigirte a esta web con ?pro=1.")

    # ========== PRO ==========
    if is_pro:
        full = res["full"]
        st.markdown("---")
        st.subheader("✅ Análisis completo (PRO)")

        st.write(f"**Diagnóstico:** {full['diagnostico']}")

        st.markdown("#### Qué está pasando")
        st.write(full["que_significa"])

        st.markdown("#### Qué hacer en los próximos 14 días")
        for step in full["plan_14_dias"]:
            st.write(f"- {step}")

        st.markdown("#### Qué no hacer todavía")
        for step in full["no_hagas"]:
            st.write(f"- {step}")

        if full.get("observacion_adicional"):
            st.markdown("#### Observación adicional")
            st.write(full["observacion_adicional"])

        st.markdown("#### Decisión recomendada")
        st.write(f"**{full['decision_final']}**")
        st.write(full["explicacion_decision"])
