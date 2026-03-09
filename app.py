import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, jsonify, flash
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "usher-logistics-dev-secret")

# ── Firebase init ─────────────────────────────────────────────────────────────

def _init_firebase():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")

        if cred_json:
            cred_dict = json.loads(cred_json)
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate("key.json")

        firebase_admin.initialize_app(cred)

    return firestore.client()

_db = _init_firebase()

def get_db():
    return _db


def _fetch(collection, order_by=None, direction=None, limit=None, where=None):
    """Helper: run a Firestore collection query and return list of dicts."""
    db  = get_db()
    ref = db.collection(collection)
    if where:
        ref = ref.where(where[0], where[1], where[2])
    if order_by:
        ref = ref.order_by(order_by,
                           direction=direction or firestore.Query.ASCENDING)
    if limit:
        ref = ref.limit(limit)
    return [{"id": d.id, **d.to_dict()} for d in ref.get()]


def parallel(*fns):
    """Run callables in parallel threads, return results in same order."""
    if len(fns) == 1:
        return [fns[0]()]
    with ThreadPoolExecutor(max_workers=len(fns)) as ex:
        futures = {ex.submit(fn): i for i, fn in enumerate(fns)}
        results = [None] * len(fns)
        for f in as_completed(futures):
            results[futures[f]] = f.result()
    return results


def _norm_zona(z):
    """Normalize Firestore zona dict: map nombre_descriptivo -> nombre."""
    if not z.get("nombre"):
        z["nombre"] = z.get("nombre_descriptivo") or z.get("id_zona") or z.get("id", "")
    return z


# ── Context processor ─────────────────────────────────────────────────────────
@app.context_processor
def inject_now():
    return {"now": datetime.now()}


# ── Bloques predefinidos ──────────────────────────────────────────────────────
BLOQUES = [
    {"label": "Jornada Completa  (7:30 – 12:30)", "inicio": "07:30", "fin": "12:30"},
    {"label": "Bloque Mañana     (7:30 – 10:00)", "inicio": "07:30", "fin": "10:00"},
    {"label": "Bloque Tarde      (10:00 – 12:30)", "inicio": "10:00", "fin": "12:30"},
    {"label": "Turno A  (7:30 – 8:45)",  "inicio": "07:30", "fin": "08:45"},
    {"label": "Turno B  (8:45 – 10:00)", "inicio": "08:45", "fin": "10:00"},
    {"label": "Turno C  (10:00 – 11:15)","inicio": "10:00", "fin": "11:15"},
    {"label": "Turno D  (11:15 – 12:30)","inicio": "11:15", "fin": "12:30"},
]


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def dashboard():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        congs, vols, zonas, asigs = parallel(
            lambda: _fetch("congregaciones"),
            lambda: _fetch("voluntarios"),
            lambda: _fetch("zonas"),
            lambda: _fetch("asignaciones"),
        )

        congregaciones_count = len(congs)
        voluntarios_count    = len(vols)
        zonas_count          = len(zonas)
        asignaciones_count   = len(asigs)
        capitanes_count      = sum(1 for v in vols if v.get("capitan"))

        vol_map  = {v["id"]: v["nombre"] for v in vols}
        zonas    = [_norm_zona(z) for z in zonas]
        zona_map = {z["id"]: z["nombre"] for z in zonas}

        # Top 5 zones by assignment count
        zone_counts = {}
        for a in asigs:
            znombre = zona_map.get(a.get("zona_id", ""), "Sin zona")
            zone_counts[znombre] = zone_counts.get(znombre, 0) + 1
        top_zonas = sorted(zone_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Most recent 8 assignments
        recent = sorted(asigs, key=lambda a: a.get("fecha", ""), reverse=True)[:8]
        for a in recent:
            a["voluntario_nombre"] = vol_map.get(a.get("voluntario_id", ""), "—")
            a["zona_nombre"]       = zona_map.get(a.get("zona_id",      ""), "—")

        # Monthly counts (last 6 months)
        month_counts = {}
        for a in asigs:
            m = (a.get("fecha") or "")[:7]
            if m:
                month_counts[m] = month_counts.get(m, 0) + 1
        months_sorted = sorted(month_counts.items())[-6:]

    except Exception as exc:
        flash(f"Error de conexión con Firebase: {exc}", "error")
        congregaciones_count = voluntarios_count = zonas_count = asignaciones_count = capitanes_count = 0
        top_zonas = []
        recent = []
        months_sorted = []

    return render_template(
        "index.html",
        congregaciones_count=congregaciones_count,
        voluntarios_count=voluntarios_count,
        zonas_count=zonas_count,
        asignaciones_count=asignaciones_count,
        capitanes_count=capitanes_count,
        top_zonas=top_zonas,
        recent_asignaciones=recent,
        months_data=months_sorted,
        today=today,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  CONGREGACIONES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/congregaciones")
def congregaciones():
    db = get_db()
    docs = db.collection("congregaciones").order_by("nombre").get()
    data = [{"id": doc.id, **doc.to_dict()} for doc in docs]
    return render_template("congregaciones.html", congregaciones=data)


@app.route("/api/congregaciones", methods=["GET"])
def api_list_congregaciones():
    db = get_db()
    docs = db.collection("congregaciones").order_by("nombre").get()
    return jsonify([{"id": doc.id, **doc.to_dict()} for doc in docs])


@app.route("/api/congregaciones", methods=["POST"])
def api_add_congregacion():
    db = get_db()
    body   = request.get_json(silent=True) or {}
    nombre = (body.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre es requerido"}), 400
    doc_id = nombre.upper().replace(" ", "_")
    db.collection("congregaciones").document(doc_id).set({"nombre": nombre})
    return jsonify({"id": doc_id, "nombre": nombre}), 201


@app.route("/api/congregaciones/<doc_id>", methods=["PUT"])
def api_update_congregacion(doc_id):
    db = get_db()
    body   = request.get_json(silent=True) or {}
    nombre = (body.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre es requerido"}), 400
    db.collection("congregaciones").document(doc_id).update({"nombre": nombre})
    return jsonify({"success": True})


@app.route("/api/congregaciones/<doc_id>", methods=["DELETE"])
def api_delete_congregacion(doc_id):
    db = get_db()
    db.collection("congregaciones").document(doc_id).delete()
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════════════════════════════════
#  VOLUNTARIOS
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/voluntarios")
def voluntarios():
    vols_raw, congs_raw = parallel(
        lambda: _fetch("voluntarios",    order_by="nombre"),
        lambda: _fetch("congregaciones", order_by="nombre"),
    )
    cong_map  = {c["id"]: c["nombre"] for c in congs_raw}
    cong_list = [{"id": c["id"], "nombre": c["nombre"]} for c in congs_raw]

    vols = []
    for v in vols_raw:
        v["congregacion_nombre"] = cong_map.get(v.get("congregacion_id", ""), "—")
        vols.append(v)

    return render_template("voluntarios.html", voluntarios=vols, congregaciones=cong_list)


@app.route("/api/voluntarios", methods=["POST"])
def api_add_voluntario():
    db     = get_db()
    body   = request.get_json(silent=True) or {}
    nombre = (body.get("nombre") or "").strip()
    cong   = (body.get("congregacion_id") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio"}), 400
    if not cong:
        return jsonify({"error": "La congregación es obligatoria"}), 400
    raw_cap = body.get("capitan", False)
    capitan = raw_cap.lower() in ("true", "1") if isinstance(raw_cap, str) else bool(raw_cap)
    new_data = {
        "nombre":          nombre,
        "celular":         (body.get("celular") or "").strip(),
        "congregacion_id": cong,
        "capitan":         capitan,
    }
    _, ref = db.collection("voluntarios").add(new_data)
    return jsonify({"id": ref.id, **new_data}), 201


@app.route("/api/voluntarios/<doc_id>", methods=["PUT"])
def api_update_voluntario(doc_id):
    db      = get_db()
    body    = request.get_json(silent=True) or {}
    raw_cap = body.get("capitan", False)
    capitan = raw_cap.lower() in ("true", "1") if isinstance(raw_cap, str) else bool(raw_cap)
    db.collection("voluntarios").document(doc_id).update({
        "nombre":          (body.get("nombre") or "").strip(),
        "celular":         (body.get("celular") or "").strip(),
        "congregacion_id": (body.get("congregacion_id") or "").strip(),
        "capitan":         capitan,
    })
    return jsonify({"success": True})


@app.route("/api/voluntarios/<doc_id>", methods=["DELETE"])
def api_delete_voluntario(doc_id):
    db = get_db()
    db.collection("voluntarios").document(doc_id).delete()
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════════════════════════════════
#  ZONAS
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/zonas")
def zonas():
    db   = get_db()
    docs = db.collection("zonas").order_by("id_zona").get()
    data = [_norm_zona({"id": doc.id, **doc.to_dict()}) for doc in docs]
    return render_template("zonas.html", zonas=data)


@app.route("/api/zonas", methods=["POST"])
def api_add_zona():
    db      = get_db()
    body    = request.get_json(silent=True) or {}
    id_zona = (body.get("id_zona") or "").strip().upper()
    nombre  = (body.get("nombre")  or "").strip()
    if not id_zona or not nombre:
        return jsonify({"error": "ID y nombre son requeridos"}), 400
    raw = body.get("sub_sectores", "")
    sub_sectores = (
        [s.strip() for s in raw.split(",") if s.strip()]
        if isinstance(raw, str) else list(raw)
    )
    new_data = {"id_zona": id_zona, "nombre_descriptivo": nombre, "sub_sectores": sub_sectores}
    db.collection("zonas").document(id_zona).set(new_data)
    return jsonify({"id": id_zona, **new_data}), 201


@app.route("/api/zonas/<doc_id>", methods=["PUT"])
def api_update_zona(doc_id):
    db   = get_db()
    body = request.get_json(silent=True) or {}
    raw  = body.get("sub_sectores", "")
    sub_sectores = (
        [s.strip() for s in raw.split(",") if s.strip()]
        if isinstance(raw, str) else list(raw)
    )
    db.collection("zonas").document(doc_id).update({
        "nombre_descriptivo": (body.get("nombre") or "").strip(),
        "sub_sectores":       sub_sectores,
    })
    return jsonify({"success": True})


@app.route("/api/zonas/<doc_id>", methods=["DELETE"])
def api_delete_zona(doc_id):
    db = get_db()
    db.collection("zonas").document(doc_id).delete()
    return jsonify({"success": True})


@app.route("/api/zonas/<zona_id>/sub_sectores")
def api_sub_sectores(zona_id):
    db  = get_db()
    doc = db.collection("zonas").document(zona_id).get()
    return jsonify(doc.to_dict().get("sub_sectores", []) if doc.exists else [])


# ═══════════════════════════════════════════════════════════════════════════════
#  ASIGNACIONES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/asignaciones")
def asignaciones():
    congs_raw, vols_raw, zonas_raw, asig_raw = parallel(
        lambda: _fetch("congregaciones", order_by="nombre"),
        lambda: _fetch("voluntarios",    order_by="nombre"),
        lambda: _fetch("zonas",          order_by="id_zona"),
        lambda: _fetch("asignaciones",   order_by="fecha",
                       direction=firestore.Query.DESCENDING, limit=300),
    )

    voluntarios = vols_raw
    capitanes   = [v for v in voluntarios if v.get("capitan")]
    zonas       = [_norm_zona(z) for z in zonas_raw]
    vol_map     = {v["id"]: v["nombre"] for v in voluntarios}
    zona_map    = {z["id"]: z for z in zonas}
    cong_map    = {c["id"]: c.get("nombre", "—") for c in congs_raw}
    vol_cong    = {v["id"]: cong_map.get(v.get("congregacion_id", ""), "—") for v in voluntarios}

    asig_list = []
    for a in asig_raw:
        vid = a.get("voluntario_id", "")
        a["voluntario_nombre"]      = vol_map.get(vid, "—")
        a["congregacion_nombre"]    = vol_cong.get(vid, "—")
        a["capitan_nombre"]         = vol_map.get(a.get("capitan_id", ""), "—")
        zona                        = zona_map.get(a.get("zona_id", ""), {})
        a["zona_nombre"]            = zona.get("nombre", "—") if zona else "—"
        a["zona_id_zona"]           = zona.get("id_zona", a.get("zona_id", "—")) if zona else a.get("zona_id", "—")
        a["zona_nombre_descriptivo"]= zona.get("nombre_descriptivo", zona.get("nombre", "—")) if zona else "—"
        asig_list.append(a)

    return render_template(
        "asignaciones.html",
        voluntarios=voluntarios,
        capitanes=capitanes,
        zonas=zonas,
        asignaciones=asig_list,
        bloques=BLOQUES,
    )


@app.route("/api/asignaciones", methods=["POST"])
def api_add_asignacion():
    db   = get_db()
    body = request.get_json(silent=True) or {}
    new_data = {
        "voluntario_id":  body.get("voluntario_id",  ""),
        "capitan_id":     body.get("capitan_id",     ""),
        "zona_id":        body.get("zona_id",        ""),
        "sub_sector":     body.get("sub_sector",     ""),
        "bloque_maestro": body.get("bloque_maestro", ""),
        "horario": {
            "inicio": body.get("horario_inicio", ""),
            "fin":    body.get("horario_fin",    ""),
        },
        "fecha": body.get("fecha", datetime.now().strftime("%Y-%m-%d")),
    }
    _, ref = db.collection("asignaciones").add(new_data)
    return jsonify({"id": ref.id}), 201


@app.route("/api/asignaciones/<doc_id>", methods=["PUT"])
def api_update_asignacion(doc_id):
    db   = get_db()
    body = request.get_json(silent=True) or {}
    db.collection("asignaciones").document(doc_id).update({
        "voluntario_id":  body.get("voluntario_id",  ""),
        "capitan_id":     body.get("capitan_id",     ""),
        "zona_id":        body.get("zona_id",        ""),
        "sub_sector":     body.get("sub_sector",     ""),
        "bloque_maestro": body.get("bloque_maestro", ""),
        "horario": {
            "inicio": body.get("horario_inicio", ""),
            "fin":    body.get("horario_fin",    ""),
        },
        "fecha": body.get("fecha", ""),
    })
    return jsonify({"success": True})


@app.route("/api/asignaciones/<doc_id>", methods=["DELETE"])
def api_delete_asignacion(doc_id):
    db = get_db()
    db.collection("asignaciones").document(doc_id).delete()
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=True, port=5000)
