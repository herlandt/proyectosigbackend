"""
generar_diagrama_mdj.py
-----------------------
Genera DIAGRAMA_BASE_MICROBUSES.mdj para StarUML a partir del esquema
de base_de_datos_microbuses.sql.

Uso:
    python scripts/generar_diagrama_mdj.py
    (crea guias/DIAGRAMA_BASE_MICROBUSES.mdj)
"""

import json, os

# ─── CONFIGURACIÓN DE LAYOUT ───────────────────────────────────────────────
# Cada clase: (left, top, width)
# El alto se calcula automáticamente según la cantidad de atributos.
LAYOUT = {
    "conductores":     (40,   40,  270),
    "lineas":          (390,  40,  290),
    "microbuses":      (180,  380, 270),
    "microbuses_fotos":(540,  380, 250),
    "recorridos":      (40,   700, 290),
    "telemetria":      (420,  700, 270),
}

# ─── DEFINICIÓN DE TABLAS ──────────────────────────────────────────────────
TABLES = [
    {
        "id": "CLS_C001", "name": "conductores",
        "attrs": [
            ("ATR_C001_01", "id",                   "UUID"),
            ("ATR_C001_02", "documento_identidad",  "string"),
            ("ATR_C001_03", "nombre",               "string"),
            ("ATR_C001_04", "fecha_nacimiento",     "date"),
            ("ATR_C001_05", "sexo",                 "sexo_enum"),
            ("ATR_C001_06", "telefono",             "string"),
            ("ATR_C001_07", "email",                "string"),
            ("ATR_C001_08", "categoria_licencia",   "categoria_licencia_enum"),
            ("ATR_C001_09", "foto_url",             "string"),
            ("ATR_C001_10", "password_hash",        "string"),
            ("ATR_C001_11", "activo",               "boolean"),
            ("ATR_C001_12", "created_at",           "datetime"),
            ("ATR_C001_13", "updated_at",           "datetime"),
        ],
        "assocs": [
            ("ASC_C001_C003", "posee",    "CLS_C003", "1", "0..*"),
            ("ASC_C001_C005", "realiza",  "CLS_C005", "1", "0..*"),
        ],
    },
    {
        "id": "CLS_C002", "name": "lineas",
        "attrs": [
            ("ATR_C002_01", "id",                    "UUID"),
            ("ATR_C002_02", "numero",                "string"),
            ("ATR_C002_03", "nombre",                "string"),
            ("ATR_C002_04", "descripcion",           "string"),
            ("ATR_C002_05", "recorrido_ida",         "geometry"),
            ("ATR_C002_06", "recorrido_vuelta",      "geometry"),
            ("ATR_C002_07", "punto_partida_ida",     "geometry"),
            ("ATR_C002_08", "punto_llegada_ida",     "geometry"),
            ("ATR_C002_09", "punto_partida_vuelta",  "geometry"),
            ("ATR_C002_10", "punto_llegada_vuelta",  "geometry"),
            ("ATR_C002_11", "activa",                "boolean"),
            ("ATR_C002_12", "created_at",            "datetime"),
            ("ATR_C002_13", "updated_at",            "datetime"),
        ],
        "assocs": [
            ("ASC_C002_C003", "incluye", "CLS_C003", "1", "0..*"),
            ("ASC_C002_C005", "tiene",   "CLS_C005", "1", "0..*"),
        ],
    },
    {
        "id": "CLS_C003", "name": "microbuses",
        "attrs": [
            ("ATR_C003_01", "id",               "UUID"),
            ("ATR_C003_02", "placa",            "string"),
            ("ATR_C003_03", "modelo",           "string"),
            ("ATR_C003_04", "cantidad_asientos","integer"),
            ("ATR_C003_05", "conductor_id",     "UUID"),
            ("ATR_C003_06", "linea_id",         "UUID"),
            ("ATR_C003_07", "numero_interno",   "string"),
            ("ATR_C003_08", "fecha_asignacion", "date"),
            ("ATR_C003_09", "fecha_baja",       "date"),
            ("ATR_C003_10", "created_at",       "datetime"),
            ("ATR_C003_11", "updated_at",       "datetime"),
        ],
        "assocs": [
            ("ASC_C003_C004", "tiene_fotos", "CLS_C004", "1", "0..*"),
            ("ASC_C003_C005", "genera",      "CLS_C005", "1", "0..*"),
        ],
    },
    {
        "id": "CLS_C004", "name": "microbuses_fotos",
        "attrs": [
            ("ATR_C004_01", "id",          "UUID"),
            ("ATR_C004_02", "microbus_id", "UUID"),
            ("ATR_C004_03", "foto_url",    "string"),
            ("ATR_C004_04", "orden",       "integer"),
            ("ATR_C004_05", "created_at",  "datetime"),
        ],
        "assocs": [],
    },
    {
        "id": "CLS_C005", "name": "recorridos",
        "attrs": [
            ("ATR_C005_01", "id",                "UUID"),
            ("ATR_C005_02", "microbus_id",       "UUID"),
            ("ATR_C005_03", "conductor_id",      "UUID"),
            ("ATR_C005_04", "linea_id",          "UUID"),
            ("ATR_C005_05", "sentido",           "sentido_enum"),
            ("ATR_C005_06", "fecha_inicio",      "datetime"),
            ("ATR_C005_07", "fecha_fin",         "datetime"),
            ("ATR_C005_08", "tipo_finalizacion", "tipo_finalizacion_enum"),
            ("ATR_C005_09", "motivo_salida",     "string"),
            ("ATR_C005_10", "ubicacion_inicio",  "geometry"),
            ("ATR_C005_11", "ubicacion_fin",     "geometry"),
            ("ATR_C005_12", "distancia_total_km","decimal"),
            ("ATR_C005_13", "tiempo_total_seg",  "integer"),
            ("ATR_C005_14", "created_at",        "datetime"),
            ("ATR_C005_15", "updated_at",        "datetime"),
        ],
        "assocs": [
            ("ASC_C005_C006", "registra", "CLS_C006", "1", "0..*"),
        ],
    },
    {
        "id": "CLS_C006", "name": "telemetria",
        "attrs": [
            ("ATR_C006_01", "id",                  "UUID"),
            ("ATR_C006_02", "recorrido_id",        "UUID"),
            ("ATR_C006_03", "ubicacion",           "geometry"),
            ("ATR_C006_04", "fecha",               "date"),
            ("ATR_C006_05", "hora",                "time"),
            ("ATR_C006_06", "timestamp_evento",    "datetime"),
            ("ATR_C006_07", "velocidad",           "decimal"),
            ("ATR_C006_08", "distancia_recorrida", "decimal"),
            ("ATR_C006_09", "tiempo_transcurrido", "integer"),
            ("ATR_C006_10", "created_at",          "datetime"),
        ],
        "assocs": [],
    },
]

# ─── CONSTRUCCIÓN DEL MDJ ─────────────────────────────────────────────────

def cls_height(n_attrs):
    # 25 (name) + n*15+4 (attrs) + 10 (op) + 10 (recep) = 49 + n*15
    return 49 + n_attrs * 15

def make_class(t, model_id):
    cls_id = t["id"]
    attrs_json = []
    for aid, aname, atype in t["attrs"]:
        attrs_json.append({
            "_type": "UMLAttribute",
            "_id": aid,
            "_parent": {"$ref": cls_id},
            "name": aname,
            "type": atype,
        })

    assocs_json = []
    for asc_id, asc_name, target_id, mult1, mult2 in t["assocs"]:
        assocs_json.append({
            "_type": "UMLAssociation",
            "_id": asc_id,
            "_parent": {"$ref": cls_id},
            "name": asc_name,
            "end1": {
                "_type": "UMLAssociationEnd",
                "_id": f"AE1_{asc_id}",
                "_parent": {"$ref": asc_id},
                "reference": {"$ref": cls_id},
                "name": mult1,
            },
            "end2": {
                "_type": "UMLAssociationEnd",
                "_id": f"AE2_{asc_id}",
                "_parent": {"$ref": asc_id},
                "reference": {"$ref": target_id},
                "name": mult2,
            },
        })

    return {
        "_type": "UMLClass",
        "_id": cls_id,
        "_parent": {"$ref": model_id},
        "name": t["name"],
        "attributes": attrs_json,
        "ownedElements": assocs_json,
    }


def make_class_view(t, diag_id):
    cls_id  = t["id"]
    name    = t["name"]
    n_attrs = len(t["attrs"])
    left, top, width = LAYOUT[name]
    height = cls_height(n_attrs)

    ncv_id  = f"NCV_{cls_id}"
    acv_id  = f"ACV_{cls_id}"
    ocv_id  = f"OCV_{cls_id}"
    rcv_id  = f"RCV_{cls_id}"
    tcv_id  = f"TCV_{cls_id}"
    cv_id   = f"CV_{cls_id}"

    nl1 = f"NL_{cls_id}_1"
    nl2 = f"NL_{cls_id}_2"
    nl3 = f"NL_{cls_id}_3"
    nl4 = f"NL_{cls_id}_4"

    ncv_height = 25
    acv_top    = top + ncv_height
    acv_height = n_attrs * 15 + 4

    name_compartment = {
        "_type": "UMLNameCompartmentView",
        "_id": ncv_id,
        "_parent": {"$ref": cv_id},
        "model": {"$ref": cls_id},
        "subViews": [
            {"_type": "LabelView", "_id": nl1, "_parent": {"$ref": ncv_id},
             "font": "Arial;13;0", "parentStyle": True,
             "left": left, "top": top, "width": 100, "height": 13, "visible": False},
            {"_type": "LabelView", "_id": nl2, "_parent": {"$ref": ncv_id},
             "font": "Arial;13;1", "parentStyle": True,
             "left": left + 5, "top": top + 6, "width": width - 10, "height": 13,
             "text": name},
            {"_type": "LabelView", "_id": nl3, "_parent": {"$ref": ncv_id},
             "font": "Arial;13;0", "parentStyle": True,
             "left": left, "top": top, "width": 100, "height": 13, "visible": False},
            {"_type": "LabelView", "_id": nl4, "_parent": {"$ref": ncv_id},
             "font": "Arial;13;0", "parentStyle": True,
             "left": left, "top": top, "width": 100, "height": 13, "visible": False},
        ],
        "font": "Arial;13;0", "parentStyle": True,
        "left": left, "top": top, "width": width, "height": ncv_height,
        "stereotypeLabel":  {"$ref": nl1},
        "nameLabel":        {"$ref": nl2},
        "namespaceLabel":   {"$ref": nl3},
        "propertyLabel":    {"$ref": nl4},
    }

    attr_views = []
    for i, (aid, aname, atype) in enumerate(t["attrs"]):
        avw_id = f"AVW_{cls_id}_{i:02d}"
        attr_views.append({
            "_type": "UMLAttributeView",
            "_id": avw_id,
            "_parent": {"$ref": acv_id},
            "model": {"$ref": aid},
            "font": "Arial;13;0", "parentStyle": True,
            "left": left + 5,
            "top":  acv_top + 4 + i * 15,
            "width": width - 10, "height": 13,
            "text": f"+{aname} : {atype}",
            "horizontalAlignment": 0,
        })

    attr_compartment = {
        "_type": "UMLAttributeCompartmentView",
        "_id": acv_id,
        "_parent": {"$ref": cv_id},
        "model": {"$ref": cls_id},
        "subViews": attr_views,
        "font": "Arial;13;0", "parentStyle": True,
        "left": left, "top": acv_top, "width": width, "height": acv_height,
    }

    op_top = acv_top + acv_height
    op_compartment = {
        "_type": "UMLOperationCompartmentView",
        "_id": ocv_id,
        "_parent": {"$ref": cv_id},
        "model": {"$ref": cls_id},
        "subViews": [],
        "font": "Arial;13;0", "parentStyle": True,
        "left": left, "top": op_top, "width": width, "height": 10,
    }

    rec_compartment = {
        "_type": "UMLReceptionCompartmentView",
        "_id": rcv_id,
        "_parent": {"$ref": cv_id},
        "model": {"$ref": cls_id},
        "subViews": [],
        "font": "Arial;13;0", "parentStyle": True,
        "left": left, "top": op_top + 10, "width": width, "height": 10,
    }

    tpl_compartment = {
        "_type": "UMLTemplateParameterCompartmentView",
        "_id": tcv_id,
        "_parent": {"$ref": cv_id},
        "model": {"$ref": cls_id},
        "subViews": [],
        "font": "Arial;13;0", "parentStyle": True,
        "left": left, "top": top, "width": 10, "height": 0,
    }

    return {
        "_type": "UMLClassView",
        "_id": cv_id,
        "_parent": {"$ref": diag_id},
        "model": {"$ref": cls_id},
        "subViews": [
            name_compartment,
            attr_compartment,
            op_compartment,
            rec_compartment,
            tpl_compartment,
        ],
        "font": "Arial;13;0", "parentStyle": True,
        "containerChangeable": True,
        "left": left, "top": top, "width": width, "height": height,
        "nameCompartment":           {"$ref": ncv_id},
        "attributeCompartment":      {"$ref": acv_id},
        "operationCompartment":      {"$ref": ocv_id},
        "receptionCompartment":      {"$ref": rcv_id},
        "templateParameterCompartment": {"$ref": tcv_id},
    }


def center(cls_name):
    l, t, w = LAYOUT[cls_name]
    n = next(len(x["attrs"]) for x in TABLES if x["name"] == cls_name)
    h = cls_height(n)
    return l + w // 2, t + h // 2


def make_assoc_view(asc_id, asc_name, src_name, dst_name, mult1, mult2, diag_id):
    asv_id = f"ASV_{asc_id}"
    cv_src = f"CV_CLS_{src_name.upper()}" if False else f"CV_{next(t['id'] for t in TABLES if t['name']==src_name)}"
    cv_dst = f"CV_{next(t['id'] for t in TABLES if t['name']==dst_name)}"

    cx1, cy1 = center(src_name)
    cx2, cy2 = center(dst_name)
    pts = f"{cx1}:{cy1};{cx2}:{cy2}"

    def elbl(i, text=None):
        eid = f"EL_{asc_id}_{i}"
        obj = {
            "_type": "EdgeLabelView",
            "_id": eid,
            "_parent": {"$ref": asv_id},
            "font": "Arial;13;0", "parentStyle": True,
            "edgePosition": 1, "alpha": 0, "distance": 20,
            "hostEdge": {"$ref": asv_id},
        }
        if text is not None:
            obj["text"] = text
        else:
            obj["visible"] = False
        return obj

    sub = [
        elbl(1, asc_name),   # nameLabel
        elbl(2),             # stereotypeLabel
        elbl(3),             # propertyLabel
        elbl(4),             # tailRoleNameLabel
        elbl(5),             # tailPropertyLabel
        elbl(6, mult1),      # tailMultiplicityLabel
        elbl(7),             # headRoleNameLabel
        elbl(8),             # headPropertyLabel
        elbl(9, mult2),      # headMultiplicityLabel
        {"_type": "UMLQualifierCompartmentView", "_id": f"TQ_{asc_id}",
         "_parent": {"$ref": asv_id}, "subViews": [], "visible": False,
         "font": "Arial;13;0", "parentStyle": True},
        {"_type": "UMLQualifierCompartmentView", "_id": f"HQ_{asc_id}",
         "_parent": {"$ref": asv_id}, "subViews": [], "visible": False,
         "font": "Arial;13;0", "parentStyle": True},
    ]

    return {
        "_type": "UMLAssociationView",
        "_id": asv_id,
        "_parent": {"$ref": diag_id},
        "model": {"$ref": asc_id},
        "subViews": sub,
        "font": "Arial;13;0", "parentStyle": False,
        "tail": {"$ref": cv_src},
        "head": {"$ref": cv_dst},
        "lineStyle": 1,
        "points": pts,
        "showVisibility": True,
        "showEndOrder": "hide",
        "nameLabel":             {"$ref": f"EL_{asc_id}_1"},
        "stereotypeLabel":       {"$ref": f"EL_{asc_id}_2"},
        "propertyLabel":         {"$ref": f"EL_{asc_id}_3"},
        "tailRoleNameLabel":     {"$ref": f"EL_{asc_id}_4"},
        "tailPropertyLabel":     {"$ref": f"EL_{asc_id}_5"},
        "tailMultiplicityLabel": {"$ref": f"EL_{asc_id}_6"},
        "headRoleNameLabel":     {"$ref": f"EL_{asc_id}_7"},
        "headPropertyLabel":     {"$ref": f"EL_{asc_id}_8"},
        "headMultiplicityLabel": {"$ref": f"EL_{asc_id}_9"},
        "tailQualifiersCompartment": {"$ref": f"TQ_{asc_id}"},
        "headQualifiersCompartment": {"$ref": f"HQ_{asc_id}"},
    }


def build_mdj():
    proj_id  = "PROJ_MICRO_SIG"
    model_id = "MDL_MAIN"
    diag_id  = "DGM_MAIN"

    # Build model elements (classes)
    model_elements = [make_class(t, model_id) for t in TABLES]

    # Build diagram views
    class_views = [make_class_view(t, diag_id) for t in TABLES]

    assoc_views = []
    for t in TABLES:
        src_name = t["name"]
        for asc_id, asc_name, target_cls_id, mult1, mult2 in t["assocs"]:
            dst_name = next(x["name"] for x in TABLES if x["id"] == target_cls_id)
            assoc_views.append(
                make_assoc_view(asc_id, asc_name, src_name, dst_name, mult1, mult2, diag_id)
            )

    diagram = {
        "_type": "UMLClassDiagram",
        "_id": diag_id,
        "_parent": {"$ref": model_id},
        "name": "Main",
        "defaultDiagram": True,
        "ownedViews": class_views + assoc_views,
    }

    model_elements.append(diagram)

    project = {
        "_type": "Project",
        "_id": proj_id,
        "name": "MicrobusesSIG",
        "ownedElements": [
            {
                "_type": "UMLModel",
                "_id": model_id,
                "_parent": {"$ref": proj_id},
                "name": "Model",
                "ownedElements": model_elements,
            }
        ],
    }

    return project


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path   = os.path.join(script_dir, "..", "guias", "DIAGRAMA_BASE_MICROBUSES.mdj")
    out_path   = os.path.normpath(out_path)

    mdj = build_mdj()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mdj, f, indent="\t", ensure_ascii=False)

    print(f"Generado: {out_path}")
