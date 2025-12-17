from datetime import datetime, timedelta
import io
import json
import re
import secrets
from math import ceil

from flask import current_app

from app.extensions.db import db
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import and_, func, or_
from app.models.articulo import Articulo
from app.models.incidente_renta import IncidenteRenta
from app.models.mensaje_renta import MensajeRenta
from app.models.chat_lectura import ChatLectura
from app.models.punto_entrega import PuntoEntrega
from app.models.renta import Renta
from app.models.usuario import Usuario
from app.services.disponibilidad_service import validar_disponibilidad_articulo
from app.services import notificacion_service
from app.utils.errors import ApiError


PAGO_EXPIRA_MINUTOS_DEFAULT = 15
CHAT_RATE_LIMIT_SECONDS_DEFAULT = 3


def _get_pago_expira_minutos() -> int:
    try:
        v = int(current_app.config.get("PAGO_EXPIRA_MINUTOS", PAGO_EXPIRA_MINUTOS_DEFAULT))
        return max(1, v)
    except Exception:
        return PAGO_EXPIRA_MINUTOS_DEFAULT


def _get_chat_rate_limit_seconds() -> int:
    try:
        v = int(current_app.config.get("CHAT_RATE_LIMIT_SECONDS", CHAT_RATE_LIMIT_SECONDS_DEFAULT))
        return max(0, v)
    except Exception:
        return CHAT_RATE_LIMIT_SECONDS_DEFAULT

# Estados internos que cuentan como "activos" para traslapes/ocupación visible.
ESTADOS_RENTA_ACTIVOS_OCUPACION = [
    "pendiente_pago",
    "pagada",
    "confirmada",
    "en_curso",
]


def _estado_publico(renta: Renta) -> str:
    """Estado público (bonito) sin cambiar los valores internos de BD."""

    estado_interno = renta.estado_renta
    if estado_interno == "en_curso":
        return "devuelta" if renta.devuelto else "en_uso"
    if estado_interno == "completada":
        return "finalizada"
    if estado_interno == "con_incidente":
        return "incidente"
    if estado_interno == "cancelada":
        notas = (renta.notas_devolucion or "")
        return "expirada" if "EXPIRACION_PAGO" in notas else "cancelada"
    return estado_interno


def _append_ts_note(renta: Renta, key: str, dt: datetime | None = None) -> None:
    """Guarda un timestamp de evento en notas_devolucion sin migraciones.

    Formato: TS:<KEY>:<ISO>
    """

    try:
        k = str(key or "").strip().upper()
        if not k:
            return

        stamp = (dt or datetime.utcnow()).replace(microsecond=0).isoformat()
        line = f"TS:{k}:{stamp}"

        prev = renta.notas_devolucion or ""
        if line in prev:
            return

        sep = "\n" if prev else ""
        renta.notas_devolucion = f"{prev}{sep}{line}".strip()
    except Exception:
        return


def _find_ts_note(renta: Renta, key: str) -> str | None:
    try:
        k = str(key or "").strip().upper()
        if not k:
            return None

        notes = str(renta.notas_devolucion or "")
        if not notes:
            return None

        for ln in notes.splitlines():
            ln = ln.strip()
            if not ln.startswith("TS:"):
                continue
            parts = ln.split(":", 2)  # TS:KEY:ISO
            if len(parts) == 3 and parts[1].strip().upper() == k:
                return parts[2].strip() or None
        return None
    except Exception:
        return None


def _pe_extract_from_notes(renta: Renta) -> dict | None:
    """Extrae bloque estructurado PE:{json} desde notas_devolucion (compat sin migraciones)."""
    try:
        notes = str(renta.notas_devolucion or "")
        if not notes:
            return None
        for ln in notes.splitlines():
            ln = ln.strip()
            if not ln.startswith("PE:"):
                continue
            raw = ln[3:].strip()
            if not raw:
                return None
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        return None
    except Exception:
        return None


def _pe_set_in_notes(renta: Renta, pe: dict | None) -> None:
    """Guarda (o elimina) el bloque PE:{json} en notas_devolucion."""
    try:
        prev = str(renta.notas_devolucion or "")
        lines = [ln for ln in prev.splitlines() if ln.strip() and not ln.strip().startswith("PE:")]
        if pe:
            blob = json.dumps(pe, ensure_ascii=False)
            lines.append(f"PE:{blob}")
        renta.notas_devolucion = "\n".join(lines).strip() or None
    except Exception:
        return


def _pe_nombre(pe: dict | None) -> str | None:
    if not pe:
        return None
    n = pe.get("nombre")
    n = str(n).strip() if n is not None else ""
    return n or None


def _timeline_for_inbox(renta: Renta) -> dict:
    """Timeline para Inbox/Historial. Compat: devuelve None si no hay dato confiable."""

    estado_publico = _estado_publico(renta)

    fecha_pago = _find_ts_note(renta, "PAGO")
    fecha_coordinacion_confirmada = _find_ts_note(renta, "COORDINACION_CONFIRMADA")
    fecha_entrega = renta.fecha_entrega.isoformat() if renta.fecha_entrega else _find_ts_note(renta, "ENTREGA_CONFIRMADA")
    fecha_en_uso = _find_ts_note(renta, "EN_USO")
    fecha_devolucion = renta.fecha_devolucion.isoformat() if renta.fecha_devolucion else _find_ts_note(renta, "DEVOLUCION")

    fecha_liberacion_deposito = (
        renta.fecha_liberacion_deposito.isoformat() if renta.fecha_liberacion_deposito else _find_ts_note(renta, "DEPOSITO")
    )

    fecha_finalizacion = fecha_liberacion_deposito if estado_publico == "finalizada" else _find_ts_note(renta, "FINALIZACION")

    fecha_incidente = _find_ts_note(renta, "INCIDENTE")
    try:
        inc = IncidenteRenta.query.filter_by(id_renta=renta.id).first()
        if inc and getattr(inc, "created_at", None):
            fecha_incidente = inc.created_at.isoformat()
    except (OperationalError, ProgrammingError):
        pass

    fecha_cancelacion = _find_ts_note(renta, "CANCELACION")
    fecha_expiracion = _find_ts_note(renta, "EXPIRACION")

    return {
        "fecha_pago": fecha_pago,
        "fecha_coordinacion_confirmada": fecha_coordinacion_confirmada,
        "fecha_entrega": fecha_entrega,
        "fecha_en_uso": fecha_en_uso,
        "fecha_devolucion": fecha_devolucion,
        "fecha_finalizacion": fecha_finalizacion,
        "fecha_incidente": fecha_incidente,
        "fecha_cancelacion": fecha_cancelacion,
        "fecha_expiracion": fecha_expiracion,
        "fecha_liberacion_deposito": fecha_liberacion_deposito,
    }


def _get_articulo_imagen_principal(renta: Renta) -> str | None:
    a = renta.articulo
    if not a:
        return None
    try:
        imgs = list(getattr(a, "imagenes", []) or [])
    except Exception:
        imgs = []
    if not imgs:
        return None
    principal = next((x for x in imgs if getattr(x, "es_principal", False)), None)
    pick = principal or imgs[0]
    return getattr(pick, "url_imagen", None)


def renta_inbox_to_dict(renta: Renta) -> dict:
    unidad_precio = renta.articulo.unidad_precio if renta.articulo else None
    modalidad = (getattr(renta, "modalidad", None) or _modalidad_desde_unidad_precio(unidad_precio))
    estado_publico = _estado_publico(renta)

    subtotal = float(renta.precio_total_renta) if renta.precio_total_renta is not None else 0.0
    deposito = float(renta.monto_deposito) if renta.monto_deposito is not None else 0.0

    arr = getattr(renta, "arrendatario", None)
    prop = getattr(renta, "propietario", None)
    art = getattr(renta, "articulo", None)

    timeline = _timeline_for_inbox(renta)

    pe = _pe_extract_from_notes(renta)
    pe_nombre = _pe_nombre(pe)
    entrega_modo = "punto_entrega" if pe_nombre else "domicilio"

    return {
        "id_renta": renta.id,
        "estado": estado_publico,
        "fechas": {
            "inicio": renta.fecha_inicio.isoformat() if renta.fecha_inicio else None,
            "fin": renta.fecha_fin.isoformat() if renta.fecha_fin else None,
        },
        "modalidad": modalidad,
        "total": subtotal,
        "deposito": deposito,
        "monto_deposito": deposito,
        "deposito_liberado": bool(getattr(renta, "deposito_liberado", False)),
        "reembolso_simulado": bool("REEMBOLSO_SIMULADO:" in (renta.notas_devolucion or "")),
        "timeline": timeline,
        "entrega_modo": entrega_modo,
        "punto_entrega_nombre": pe_nombre,
        # Campos top-level para compat con frontend (mini timeline)
        "fecha_pago": timeline.get("fecha_pago"),
        "fecha_coordinacion_confirmada": timeline.get("fecha_coordinacion_confirmada"),
        "fecha_entrega": timeline.get("fecha_entrega"),
        "fecha_en_uso": timeline.get("fecha_en_uso"),
        "fecha_devolucion": timeline.get("fecha_devolucion"),
        "fecha_finalizacion": timeline.get("fecha_finalizacion"),
        "fecha_incidente": timeline.get("fecha_incidente"),
        "fecha_cancelacion": timeline.get("fecha_cancelacion"),
        "fecha_expiracion": timeline.get("fecha_expiracion"),
        "fecha_liberacion_deposito": timeline.get("fecha_liberacion_deposito"),
        "id_dueno": renta.id_propietario,
        "id_arrendatario": renta.id_arrendatario,
        "dueno": {
            "id_usuario": prop.id_usuario,
            "nombre": prop.nombre,
            "apellidos": prop.apellidos,
        }
        if prop
        else None,
        "arrendatario": {
            "id_usuario": arr.id_usuario,
            "nombre": arr.nombre,
            "apellidos": arr.apellidos,
        }
        if arr
        else None,
        "articulo": {
            "id_articulo": art.id_articulo,
            "titulo": art.titulo,
            "imagen": _get_articulo_imagen_principal(renta),
        }
        if art
        else None,
    }


def listar_rentas_mias(
    id_usuario_actual: int,
    rol: str,
    estado: str,
    page: int | str,
    per_page: int | str,
) -> dict:
    r = (rol or "").strip().lower()
    if r not in ("arrendatario", "dueno", "dueño"):
        raise ApiError("Parámetro 'rol' inválido. Usa: arrendatario|dueno", 400)

    est = (estado or "").strip().lower()
    if est not in ("activas", "historial"):
        raise ApiError("Parámetro 'estado' inválido. Usa: activas|historial", 400)

    try:
        page_int = max(int(page), 1)
    except Exception:
        page_int = 1
    try:
        per_page_int = min(max(int(per_page), 1), 50)
    except Exception:
        per_page_int = 10

    query = Renta.query
    if r == "arrendatario":
        query = query.filter(Renta.id_arrendatario == id_usuario_actual)
    else:
        query = query.filter(Renta.id_propietario == id_usuario_actual)

    if est == "activas":
        query = query.filter(Renta.estado_renta.in_(["pendiente_pago", "pagada", "confirmada", "en_curso", "con_incidente"]))
    else:
        query = query.filter(Renta.estado_renta.in_(["completada", "cancelada"]))

    # Compat con MySQL real: evitar .count() sobre subquery que selecciona columnas inexistentes.
    total = int((query.order_by(None).with_entities(func.count(Renta.id)).scalar() or 0))
    items = (
        query.order_by(Renta.fecha_creacion.desc(), Renta.id.desc())
        .offset((page_int - 1) * per_page_int)
        .limit(per_page_int)
        .all()
    )

    # Expiración lazy: si hay pendientes de pago vencidas, marcarlas al consultar.
    for x in items:
        _marcar_expirada_si_corresponde(x)

    return {
        "page": page_int,
        "per_page": per_page_int,
        "total": int(total),
        "items": [renta_inbox_to_dict(x) for x in items],
    }


def _require_participante_renta(renta: Renta, id_usuario_actual: int) -> None:
    if id_usuario_actual not in (renta.id_arrendatario, renta.id_propietario):
        raise ApiError("No autorizado", 403)


def chat_unread_count(id_renta: int, id_usuario_actual: int) -> int:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada", 404)

    _require_participante_renta(renta, id_usuario_actual)

    # Si el chat no está habilitado por estado, no mostramos unread.
    if not _chat_habilitado(renta, id_usuario_actual):
        return 0

    lectura = ChatLectura.query.filter_by(id_renta=renta.id, id_usuario=id_usuario_actual).first()
    last = lectura.last_read_at if lectura else None

    q = MensajeRenta.query.filter(MensajeRenta.id_renta == renta.id, MensajeRenta.id_emisor != id_usuario_actual)
    if last:
        q = q.filter(MensajeRenta.created_at > last)
    return int(q.count())


def chat_marcar_leido(id_renta: int, id_usuario_actual: int) -> None:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada", 404)
    _require_participante_renta(renta, id_usuario_actual)

    now = datetime.utcnow()
    lectura = ChatLectura.query.filter_by(id_renta=renta.id, id_usuario=id_usuario_actual).first()
    if not lectura:
        lectura = ChatLectura(id_renta=renta.id, id_usuario=id_usuario_actual, last_read_at=now)
        db.session.add(lectura)
    else:
        lectura.last_read_at = now
    db.session.commit()


def chat_unread_total(id_usuario_actual: int) -> int:
    """Total de mensajes sin leer en chats de rentas activas del usuario."""

    try:
        min_dt = datetime(1970, 1, 1)
        q = (
            db.session.query(func.count(MensajeRenta.id))
            .join(Renta, MensajeRenta.id_renta == Renta.id)
            .outerjoin(
                ChatLectura,
                and_(ChatLectura.id_renta == Renta.id, ChatLectura.id_usuario == id_usuario_actual),
            )
            .filter(
                or_(Renta.id_arrendatario == id_usuario_actual, Renta.id_propietario == id_usuario_actual),
                # Estados donde el chat puede estar habilitado (pendiente_pago no cuenta)
                Renta.estado_renta.in_(["pagada", "confirmada", "en_curso", "con_incidente"]),
                MensajeRenta.id_emisor != id_usuario_actual,
                MensajeRenta.created_at > func.coalesce(ChatLectura.last_read_at, min_dt),
            )
        )
        total = q.scalar() or 0
        return int(total)
    except (OperationalError, ProgrammingError):
        return 0


def _es_estado_cerrado(estado_publico: str) -> bool:
    return estado_publico in ("cancelada", "expirada", "finalizada")


def _hubo_pago_simulado(renta: Renta) -> bool:
    # Estados que solo se alcanzan post-pago en el flujo actual.
    if renta.estado_renta in ("pagada", "confirmada", "en_curso", "completada", "con_incidente"):
        return True
    notas = (renta.notas_devolucion or "")
    return "REEMBOLSO_SIMULADO:" in notas


def _parse_list_field(raw: str | None) -> list[str]:
    if not raw:
        return []
    s = str(raw).strip()
    if not s:
        return []
    try:
        data = json.loads(s)
        if isinstance(data, list):
            out: list[str] = []
            for it in data:
                v = str(it).strip()
                if v:
                    out.append(v)
            return out
    except Exception:
        pass
    # fallback: líneas
    return [ln.strip() for ln in s.splitlines() if ln.strip()]


def _dump_list_field(items: list[str] | None) -> str | None:
    if not items:
        return None
    clean = [str(x).strip() for x in items if str(x).strip()]
    if not clean:
        return None
    return json.dumps(clean, ensure_ascii=False)


def _validar_mensaje_chat(mensaje: str | None) -> str:
    m = (mensaje or "").strip()
    if not m:
        raise ApiError("Mensaje vacío.", status_code=400)
    if len(m) > 240:
        raise ApiError("El mensaje no puede exceder 240 caracteres.", status_code=400)
    if re.search(r"https?://|www\.", m, flags=re.IGNORECASE):
        raise ApiError("No se permiten links en el chat.", status_code=400)
    # Bloqueo simple de emails
    if re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", m, flags=re.IGNORECASE):
        raise ApiError("No se permiten correos electrónicos en el chat.", status_code=400)
    # Bloqueo de strings típicas de mensajería externa
    if re.search(r"\b(wa\.me|whatsapp|telegram|t\.me)\b", m, flags=re.IGNORECASE):
        raise ApiError("No se permite compartir medios de contacto en el chat.", status_code=400)
    # Bloqueo simple de teléfonos (7+ dígitos, con separadores comunes)
    if re.search(r"\b\d[\d\s\-]{6,}\d\b", m):
        raise ApiError("No se permiten números de teléfono en el chat.", status_code=400)
    return m


def _gen_otp_6() -> str:
    return str(secrets.randbelow(1_000_000)).zfill(6)


def _chat_habilitado(renta: Renta, id_usuario_actual: int | None) -> bool:
    if id_usuario_actual is None:
        return False
    estado_publico = _estado_publico(renta)
    if _es_estado_cerrado(estado_publico):
        return False
    if estado_publico == "pendiente_pago":
        return False
    return id_usuario_actual in (renta.id_arrendatario, renta.id_propietario)


def _es_expirable(renta: Renta) -> bool:
    if renta.estado_renta != "pendiente_pago":
        return False
    if not renta.fecha_creacion:
        return False
    return datetime.utcnow() - renta.fecha_creacion > timedelta(minutes=_get_pago_expira_minutos())


def _marcar_expirada_si_corresponde(renta: Renta) -> bool:
    """Marca como cancelada por expiración de pago. Devuelve True si modificó."""
    if not _es_expirable(renta):
        return False
    if renta.estado_renta == "cancelada" and "EXPIRACION_PAGO" in (renta.notas_devolucion or ""):
        return False

    renta.estado_renta = "cancelada"
    previo = renta.notas_devolucion or ""
    sep = "\n" if previo else ""
    renta.notas_devolucion = f"{previo}{sep}EXPIRACION_PAGO: Reserva expirada por falta de pago.".strip()
    _append_ts_note(renta, "EXPIRACION")
    db.session.commit()

    # Notificar a ambos
    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "EXPIRACION",
        "La reserva expiró por falta de pago.",
        meta={"id_renta": renta.id},
        event_key=f"EXPIRACION:{renta.id}:{renta.id_arrendatario}",
    )
    notificacion_service.crear_notificacion(
        renta.id_propietario,
        "EXPIRACION",
        "Una reserva expiró por falta de pago.",
        meta={"id_renta": renta.id},
        event_key=f"EXPIRACION:{renta.id}:{renta.id_propietario}",
    )
    return True


def _calcular_unidades(unidad_precio: str, fecha_inicio: datetime, fecha_fin: datetime) -> int:
    """
    Calcula cuántas unidades se cobrarán según la unidad_precio:
    - por_hora
    - por_dia
    - por_semana (por si en un futuro la usas)
    Siempre redondea hacia arriba (ceil).
    """
    segundos = (fecha_fin - fecha_inicio).total_seconds()
    if unidad_precio == "por_hora":
        horas = segundos / 3600
        return max(1, ceil(horas))
    elif unidad_precio == "por_dia":
        dias = segundos / 86400
        return max(1, ceil(dias))
    elif unidad_precio == "por_semana":
        semanas = segundos / (86400 * 7)
        return max(1, ceil(semanas))
    else:
        # fallback defensivo
        dias = segundos / 86400
        return max(1, ceil(dias))


def _unidad_precio_desde_modalidad(modalidad: str | None) -> str | None:
    if not modalidad:
        return None
    m = str(modalidad).lower().strip()
    if m == "horas":
        return "por_hora"
    if m == "dias":
        return "por_dia"
    return None


def _modalidad_desde_unidad_precio(unidad_precio: str | None) -> str:
    if unidad_precio == "por_hora":
        return "horas"
    return "dias"


def _renta_to_dict(renta: Renta, id_usuario_actual: int | None = None, roles: list[str] | None = None) -> dict:
    """
    Serialización sencilla de Renta para respuestas JSON.
    """
    unidad_precio = renta.articulo.unidad_precio if renta.articulo else None
    modalidad = (getattr(renta, "modalidad", None) or _modalidad_desde_unidad_precio(unidad_precio))

    # Estado público (sin tocar enum/valores internos de BD)
    estado_publico = _estado_publico(renta)

    # Unidades calculadas (por horas cuando aplique)
    cantidad_unidades = None
    if renta.fecha_inicio and renta.fecha_fin:
        if estado_publico in ("en_uso", "devuelta") and modalidad == "horas":
            segundos = (renta.fecha_fin - renta.fecha_inicio).total_seconds()
            cantidad_unidades = max(1, int(segundos // 3600))
        else:
            unidad_calc = "por_hora" if modalidad == "horas" else "por_dia"
            cantidad_unidades = _calcular_unidades(unidad_calc, renta.fecha_inicio, renta.fecha_fin)

    subtotal_renta = float(renta.precio_total_renta) if renta.precio_total_renta is not None else 0.0
    deposito = float(renta.monto_deposito) if renta.monto_deposito is not None else 0.0
    total_a_pagar = subtotal_renta + deposito

    # Reembolso simulado (solo informativo; no hay pagos reales)
    reembolso_simulado = False
    monto_reembolso = 0.0
    if estado_publico in ("cancelada", "expirada"):
        # Reglas simples:
        # - expirada/pendiente_pago: no hubo pago => 0
        # - cancelada después de pago/confirmación: el servicio de cancelación calcula y lo deja en notas
        notas = (renta.notas_devolucion or "")
        if "REEMBOLSO_SIMULADO:" in notas:
            reembolso_simulado = True
            try:
                # formato: REEMBOLSO_SIMULADO: <monto>
                frag = notas.split("REEMBOLSO_SIMULADO:", 1)[1].strip().split()[0]
                monto_reembolso = float(frag)
            except Exception:
                monto_reembolso = 0.0

    incidente_obj = None
    try:
        incidente = IncidenteRenta.query.filter_by(id_renta=renta.id).first()
        if incidente:
            incidente_obj = {
                "id": incidente.id,
                "descripcion": incidente.descripcion,
                "decision": incidente.decision,
                "monto_retenido": float(incidente.monto_retenido) if incidente.monto_retenido is not None else None,
                "nota": incidente.nota,
                "created_at": incidente.created_at.isoformat() if incidente.created_at else None,
                "resolved_at": incidente.resolved_at.isoformat() if incidente.resolved_at else None,
            }
    except (OperationalError, ProgrammingError):
        # Tabla nueva aún no existe (sin migraciones): no romper el flujo existente
        incidente_obj = None

    es_participante = id_usuario_actual in (renta.id_arrendatario, renta.id_propietario) if id_usuario_actual else False
    es_admin = False
    if roles:
        es_admin = any(str(r).upper() in ("ADMIN", "ADMINISTRADOR") for r in roles)

    hubo_pago = _hubo_pago_simulado(renta)
    direccion_entrega_visible = bool(hubo_pago and (es_participante or es_admin) and renta.direccion_entrega)

    pe = _pe_extract_from_notes(renta)
    pe_nombre = _pe_nombre(pe)

    # OTP solo visible al arrendatario y solo cuando la renta sigue activa
    codigos_visibles = bool(
        id_usuario_actual == renta.id_arrendatario
        and not _es_estado_cerrado(estado_publico)
        and estado_publico != "pendiente_pago"
    )

    return {
        "id": renta.id,
        "id_renta": renta.id,
        "id_articulo": renta.id_articulo,
        "id_arrendatario": renta.id_arrendatario,
        "id_propietario": renta.id_propietario,
        "fecha_inicio": renta.fecha_inicio.isoformat() if renta.fecha_inicio else None,
        "fecha_fin": renta.fecha_fin.isoformat() if renta.fecha_fin else None,
        "modalidad": modalidad,
        "cantidad_unidades": cantidad_unidades,
        "precio_total_renta": subtotal_renta,
        "monto_deposito": deposito,
        "subtotal_renta": subtotal_renta,
        "total_a_pagar": total_a_pagar,
        "estado_renta": estado_publico,
        "entregado": renta.entregado,
        "devuelto": renta.devuelto,
        "deposito_liberado": renta.deposito_liberado,
        "fecha_entrega": renta.fecha_entrega.isoformat() if renta.fecha_entrega else None,
        "fecha_devolucion": renta.fecha_devolucion.isoformat() if renta.fecha_devolucion else None,
        "fecha_liberacion_deposito": (
            renta.fecha_liberacion_deposito.isoformat() if renta.fecha_liberacion_deposito else None
        ),
        "notas_entrega": renta.notas_entrega,
        "notas_devolucion": renta.notas_devolucion,
        # Coordinación / privacidad
        "modo_entrega": renta.modo_entrega or "arrendador",
        "zona_publica": renta.zona_publica,
        "entrega_modo": "punto_entrega" if pe_nombre else "domicilio",
        "punto_entrega": pe if pe_nombre else None,
        "direccion_entrega_visible": bool(hubo_pago and (es_participante or es_admin)),
        "direccion_entrega": renta.direccion_entrega if direccion_entrega_visible else None,
        "ventanas_entrega_propuestas": _parse_list_field(renta.ventanas_entrega_propuestas),
        "ventana_entrega_elegida": renta.ventana_entrega_elegida,
        "ventanas_devolucion_propuestas": _parse_list_field(renta.ventanas_devolucion_propuestas),
        "ventana_devolucion_elegida": renta.ventana_devolucion_elegida,
        "coordinacion_confirmada": bool(renta.coordinacion_confirmada),
        # OTP
        "codigo_entrega": renta.codigo_entrega if codigos_visibles else None,
        "codigo_devolucion": renta.codigo_devolucion if codigos_visibles else None,
        "checklist_entrega": renta.checklist_entrega if (es_participante or es_admin) else None,
        "checklist_devolucion": renta.checklist_devolucion if (es_participante or es_admin) else None,
        # Chat
        "chat_habilitado": _chat_habilitado(renta, id_usuario_actual),
        "reembolso_simulado": reembolso_simulado,
        "monto_reembolso": monto_reembolso,
        "incidente": incidente_obj,
        "fecha_creacion": renta.fecha_creacion.isoformat() if renta.fecha_creacion else None,
        "articulo": {
            "id": renta.articulo.id_articulo,
            "id_articulo": renta.articulo.id_articulo,
            "titulo": renta.articulo.titulo,
            "precio_base": float(renta.articulo.precio_base),
            "precio_renta_dia": (
                float(renta.articulo.precio_base) if renta.articulo.unidad_precio == "por_dia" else None
            ),
            "precio_renta_hora": (
                float(renta.articulo.precio_base) if renta.articulo.unidad_precio == "por_hora" else None
            ),
            "unidad_precio": renta.articulo.unidad_precio,
            "monto_deposito": float(renta.articulo.monto_deposito) if renta.articulo.monto_deposito is not None else 0.0,
            "deposito_garantia": float(renta.articulo.monto_deposito) if renta.articulo.monto_deposito is not None else 0.0,
            "ubicacion_texto": renta.articulo.ubicacion_texto,
        }
        if renta.articulo
        else None,
    }


def _validar_no_traslape_rentas(id_articulo: int, fecha_inicio: datetime, fecha_fin: datetime) -> None:
    """Evita traslapes con otras rentas activas del mismo artículo."""

    estados_activos = list(ESTADOS_RENTA_ACTIVOS_OCUPACION)

    q = (
        Renta.query.filter(Renta.id_articulo == id_articulo)
        .filter(Renta.estado_renta.in_(estados_activos))
        .filter(Renta.fecha_inicio < fecha_fin)
        .filter(Renta.fecha_fin > fecha_inicio)
    )

    if q.first() is not None:
        raise ApiError("El artículo no está disponible en esas fechas/horas.", status_code=400)


def listar_ocupacion_articulo(id_articulo: int, desde: datetime, hasta: datetime) -> list[dict]:
    """Lista rangos ocupados (inicio/fin) para un artículo en ventana dada."""

    if not isinstance(desde, datetime) or not isinstance(hasta, datetime) or hasta <= desde:
        raise ApiError("Rango de fechas inválido.", status_code=400)

    q = (
        Renta.query.filter(Renta.id_articulo == id_articulo)
        .filter(Renta.estado_renta.in_(ESTADOS_RENTA_ACTIVOS_OCUPACION))
        .filter(Renta.fecha_inicio < hasta)
        .filter(Renta.fecha_fin > desde)
        .order_by(Renta.fecha_inicio.asc())
    )

    items = []
    for r in q.all():
        items.append(
            {
                "inicio": r.fecha_inicio.isoformat() if r.fecha_inicio else None,
                "fin": r.fecha_fin.isoformat() if r.fecha_fin else None,
            }
        )
    return items


def crear_renta(data: dict, id_usuario_actual: int) -> dict:
    """
    Crea una nueva renta en estado 'pendiente_pago'.

    Pasos:
    - Verificar que el artículo exista y esté activo/publicado.
    - Verificar que el usuario actual exista.
    - Validar disponibilidad (sin solapamientos).
    - Calcular precio_total_renta + depósito.
    - Crear registro en 'rentas'.
    """

    id_articulo = data["id_articulo"]
    fecha_inicio: datetime = data["fecha_inicio"]
    fecha_fin: datetime = data["fecha_fin"]
    modalidad = data.get("modalidad")

    articulo: Articulo | None = Articulo.query.get(id_articulo)
    if not articulo:
        raise ApiError("El artículo especificado no existe.", status_code=404)

    # En tu DDL tienes estado_publicacion; aquí asumimos que 'eliminado'
    # o 'pausado' no deben permitir nuevas rentas.
    if articulo.estado_publicacion not in ("publicado", "borrador"):
        raise ApiError(
            "El artículo no está disponible para renta.",
            status_code=400,
        )

    arrendatario: Usuario | None = Usuario.query.get(id_usuario_actual)
    if not arrendatario:
        raise ApiError("El usuario autenticado no existe.", status_code=404)

    # validar que no se rente su propio artículo (opcional, pero lógico)
    if articulo.id_propietario == id_usuario_actual:
        raise ApiError("No puedes rentar tu propio artículo.", status_code=403)

    # Validar disponibilidad (rentas + bloqueos)
    validar_disponibilidad_articulo(id_articulo, fecha_inicio, fecha_fin)

    # Validar disponibilidad por traslapes contra rentas activas
    _validar_no_traslape_rentas(id_articulo, fecha_inicio, fecha_fin)

    # BD real: 1 modalidad por artículo (unidad_precio).
    unidad_articulo = getattr(articulo, "unidad_precio", None)
    permite_horas = unidad_articulo == "por_hora"
    permite_dias = unidad_articulo == "por_dia"

    unidad_precio_calc = _unidad_precio_desde_modalidad(modalidad)
    if unidad_precio_calc is None:
        # default: inferir de la unidad del artículo
        if permite_horas:
            unidad_precio_calc = "por_hora"
            modalidad = "horas"
        elif permite_dias:
            unidad_precio_calc = "por_dia"
            modalidad = "dias"
        else:
            raise ApiError(
                "Este artículo no se renta por horas ni por días.",
                status_code=400,
            )
    else:
        if unidad_precio_calc == "por_hora" and not permite_horas:
            raise ApiError("Este artículo se renta por día, no por horas.", status_code=400)
        if unidad_precio_calc == "por_dia" and not permite_dias:
            raise ApiError("Este artículo se renta por hora, no por días.", status_code=400)

    # Validación extra para modalidad horas: solo horas exactas (sin minutos)
    if unidad_precio_calc == "por_hora":
        if (
            fecha_inicio.minute != 0
            or fecha_fin.minute != 0
            or fecha_inicio.second != 0
            or fecha_fin.second != 0
            or fecha_inicio.microsecond != 0
            or fecha_fin.microsecond != 0
        ):
            raise ApiError("Solo se permiten horas exactas (sin minutos).", status_code=400)

        segundos = (fecha_fin - fecha_inicio).total_seconds()
        if segundos < 3600:
            raise ApiError("La renta por horas debe ser de al menos 1 hora.", status_code=400)
        if int(segundos) % 3600 != 0:
            raise ApiError("Solo se permiten horas exactas (sin minutos).", status_code=400)

        unidades = int(segundos // 3600)
    else:
        # Calcular unidades y precio según modalidad días
        unidades = _calcular_unidades(unidad_precio_calc, fecha_inicio, fecha_fin)

    # Precio por unidad (BD real: siempre precio_base)
    precio_unit = float(articulo.precio_base)

    precio_total_renta = precio_unit * unidades
    monto_deposito = articulo.monto_deposito if articulo.monto_deposito is not None else 0

    renta = Renta(
        id_articulo=articulo.id_articulo,
        id_arrendatario=arrendatario.id_usuario,
        id_propietario=articulo.id_propietario,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        precio_total_renta=precio_total_renta,
        monto_deposito=monto_deposito,
        estado_renta="pendiente_pago",
        entregado=False,
        devuelto=False,
        deposito_liberado=False,
    )

    db.session.add(renta)
    db.session.commit()

    # Notificar a ambos (best-effort, dedupe por event_key)
    try:
        notificacion_service.crear_notificacion(
            renta.id_propietario,
            "RENTA_CREADA",
            "Nueva solicitud de renta.",
            meta={"id_renta": renta.id},
            event_key=f"RENTA_CREADA:{renta.id}",
        )
        notificacion_service.crear_notificacion(
            renta.id_arrendatario,
            "RENTA_CREADA",
            "Solicitud de renta creada.",
            meta={"id_renta": renta.id},
            event_key=f"RENTA_CREADA_ACK:{renta.id}:{renta.id_arrendatario}",
        )
    except Exception:
        pass

    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def obtener_renta(id_renta: int, id_usuario_actual: int) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    if renta.id_arrendatario != id_usuario_actual and renta.id_propietario != id_usuario_actual:
        raise ApiError("No tienes permisos para ver esta renta.", status_code=403)

    _marcar_expirada_si_corresponde(renta)

    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def generar_recibo_pdf(id_renta: int, id_usuario_actual: int) -> bytes:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    if renta.id_arrendatario != id_usuario_actual and renta.id_propietario != id_usuario_actual:
        raise ApiError("No tienes permisos para ver esta renta.", status_code=403)

    _marcar_expirada_si_corresponde(renta)

    estado_publico = _estado_publico(renta)
    estados_ok = {"pagada", "confirmada", "en_uso", "devuelta", "finalizada", "incidente"}
    if estado_publico not in estados_ok:
        raise ApiError("Aún no hay recibo disponible para esta renta.", status_code=400)

    titulo = (getattr(getattr(renta, "articulo", None), "titulo", None) or "Artículo")

    subtotal = float(renta.precio_total_renta) if renta.precio_total_renta is not None else 0.0
    deposito = float(renta.monto_deposito) if renta.monto_deposito is not None else 0.0
    total = subtotal + deposito

    def _fmt_dt(dt: datetime | None) -> str:
        return dt.isoformat() if dt else "-"

    lines = [
        "Recibo de renta",
        f"Renta ID: {renta.id}",
        f"Estado: {estado_publico}",
        f"Artículo: {titulo}",
        f"Arrendatario ID: {renta.id_arrendatario}",
        f"Propietario ID: {renta.id_propietario}",
        f"Inicio: {_fmt_dt(renta.fecha_inicio)}",
        f"Fin: {_fmt_dt(renta.fecha_fin)}",
        f"Subtotal: ${subtotal:.2f}",
        f"Depósito: ${deposito:.2f}",
        f"Total: ${total:.2f}",
        "",
        f"Generado: {datetime.utcnow().replace(microsecond=0).isoformat()} UTC",
    ]

    return _simple_pdf_bytes(lines)


def _simple_pdf_bytes(lines: list[str]) -> bytes:
    """Genera un PDF mínimo (1 página) sin dependencias externas."""

    def _sanitize(s: str) -> str:
        if s is None:
            s = ""
        # Evitar problemas con caracteres fuera de ASCII (PDF Type1 básico)
        s = s.encode("ascii", "replace").decode("ascii")
        s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return s

    safe_lines = [_sanitize(x) for x in (lines or [])]

    # Content stream (texto simple)
    y = 760
    content_parts = [
        b"BT\n/F1 12 Tf\n72 %d Td\n" % y,
    ]
    first = True
    for raw in safe_lines:
        if not first:
            content_parts.append(b"0 -16 Td\n")
        first = False
        content_parts.append(("(" + raw + ") Tj\n").encode("ascii"))
    content_parts.append(b"ET\n")
    content = b"".join(content_parts)

    def _obj(num: int, body: bytes) -> bytes:
        return f"{num} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    obj1 = _obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    obj2 = _obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    obj3 = _obj(
        3,
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    )
    obj4 = _obj(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    obj5_body = b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream"
    obj5 = _obj(5, obj5_body)

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    pdf = io.BytesIO()
    pdf.write(header)

    objects = [obj1, obj2, obj3, obj4, obj5]
    offsets: list[int] = [0]
    for o in objects:
        offsets.append(pdf.tell())
        pdf.write(o)

    xref_start = pdf.tell()
    pdf.write(b"xref\n0 6\n")
    pdf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.write(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.write(b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n")
    pdf.write(str(xref_start).encode("ascii"))
    pdf.write(b"\n%%EOF\n")

    return pdf.getvalue()


def pagar_renta(id_renta: int, id_usuario_actual: int) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    if renta.id_arrendatario != id_usuario_actual:
        raise ApiError("Solo el arrendatario puede pagar esta renta.", status_code=403)

    if _estado_publico(renta) == "expirada":
        raise ApiError("La reserva expiró.", status_code=409)

    if _es_expirable(renta):
        _marcar_expirada_si_corresponde(renta)
        raise ApiError("La reserva expiró.", status_code=409)

    if renta.estado_renta != "pendiente_pago":
        # Idempotencia: si ya pagó o avanzó, no repetir ni spamear.
        if renta.estado_renta in ("pagada", "confirmada", "en_curso", "completada", "con_incidente"):
            return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)
        raise ApiError("La renta no está pendiente de pago.", status_code=400)

    renta.estado_renta = "pagada"
    _append_ts_note(renta, "PAGO")

    # Generar OTP al pagar (solo si aún no existe)
    if not renta.codigo_entrega:
        renta.codigo_entrega = _gen_otp_6()
    if not renta.codigo_devolucion:
        renta.codigo_devolucion = _gen_otp_6()

    db.session.commit()

    # Notificar a ambos (best-effort)
    notificacion_service.crear_notificacion(
        renta.id_propietario,
        "PAGO",
        "La renta fue pagada. Ya puedes coordinar entrega y devolución.",
        meta={"id_renta": renta.id},
        event_key=f"PAGO:{renta.id}:{renta.id_propietario}",
    )

    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "PAGO",
        "Pago registrado.",
        meta={"id_renta": renta.id},
        event_key=f"PAGO:{renta.id}:{renta.id_arrendatario}",
    )

    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def cancelar_renta(id_renta: int, id_usuario_actual: int, roles: list[str] | None, motivo: str | None) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    # Expira automáticamente si aplica
    _marcar_expirada_si_corresponde(renta)

    estado = renta.estado_renta
    if estado in ("completada", "en_curso", "con_incidente"):
        raise ApiError("La renta no se puede cancelar en el estado actual.", status_code=400)
    if estado == "cancelada":
        return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual, roles=roles)

    m = (motivo or "").strip()

    es_arrendatario = renta.id_arrendatario == id_usuario_actual
    es_dueno = renta.id_propietario == id_usuario_actual
    roles = roles or []
    es_admin = any(str(r).upper() in ("ADMIN", "ADMINISTRADOR") for r in roles)

    if not (es_arrendatario or es_dueno or es_admin):
        raise ApiError("No tienes permisos para cancelar esta renta.", status_code=403)

    # Permisos y estados permitidos
    if es_arrendatario and not es_dueno and not es_admin:
        if estado not in ("pendiente_pago", "pagada", "confirmada"):
            raise ApiError("No puedes cancelar en el estado actual.", status_code=400)
    elif es_dueno and not es_admin:
        if estado not in ("pagada", "confirmada"):
            raise ApiError("No puedes cancelar en el estado actual.", status_code=400)
        if not m:
            raise ApiError("El motivo es obligatorio para el dueño.", status_code=400)

    # Reembolso simulado
    subtotal = float(renta.precio_total_renta or 0)
    deposito = float(renta.monto_deposito or 0)
    monto_reembolso = 0.0

    if estado == "pendiente_pago":
        monto_reembolso = 0.0
    elif estado == "pagada":
        # Si ya pagó, se reembolsa todo (simulado)
        monto_reembolso = subtotal + deposito
    elif estado == "confirmada":
        # Regla simple: si ya estaba confirmada, reembolso solo del depósito (simulado)
        monto_reembolso = deposito

    renta.estado_renta = "cancelada"

    previo = renta.notas_devolucion or ""
    sep = "\n" if previo else ""
    quien = "admin" if es_admin and not (es_arrendatario or es_dueno) else ("dueño" if es_dueno else "arrendatario")
    motivo_txt = m or "(sin motivo)"
    renta.notas_devolucion = (
        f"{previo}{sep}CANCELACION: por={quien}; motivo={motivo_txt}\n"
        f"REEMBOLSO_SIMULADO: {monto_reembolso:.2f}"
    ).strip()

    _append_ts_note(renta, "CANCELACION")

    db.session.commit()

    # Notificar contraparte
    otro = renta.id_propietario if es_arrendatario else renta.id_arrendatario
    notificacion_service.crear_notificacion(
        otro,
        "CANCELACION",
        "La renta fue cancelada.",
        meta={"id_renta": renta.id, "motivo": motivo_txt, "monto_reembolso": monto_reembolso},
        event_key=f"CANCELACION:{renta.id}:{otro}",
    )

    notificacion_service.crear_notificacion(
        id_usuario_actual,
        "CANCELACION",
        "Cancelación registrada.",
        meta={"id_renta": renta.id, "motivo": motivo_txt, "monto_reembolso": monto_reembolso},
        event_key=f"CANCELACION:{renta.id}:{id_usuario_actual}",
    )
    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual, roles=roles)


def confirmar_entrega(id_renta: int, id_usuario_actual: int) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    if renta.id_propietario != id_usuario_actual:
        raise ApiError("Solo el dueño puede confirmar la entrega.", status_code=403)

    if renta.estado_renta != "pagada":
        # Idempotencia: ya confirmada o en curso
        if renta.estado_renta in ("confirmada", "en_curso", "completada", "con_incidente"):
            return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)
        raise ApiError("La renta debe estar pagada para confirmar entrega.", status_code=400)

    renta.estado_renta = "confirmada"
    renta.entregado = True
    renta.fecha_entrega = datetime.utcnow()
    _append_ts_note(renta, "ENTREGA_CONFIRMADA", renta.fecha_entrega)
    db.session.commit()

    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "ENTREGA_CONFIRMADA",
        "Entrega confirmada.",
        meta={"id_renta": renta.id},
        event_key=f"ENTREGA_CONFIRMADA:{renta.id}:{renta.id_arrendatario}",
    )

    notificacion_service.crear_notificacion(
        renta.id_propietario,
        "ENTREGA_CONFIRMADA",
        "Entrega confirmada.",
        meta={"id_renta": renta.id},
        event_key=f"ENTREGA_CONFIRMADA:{renta.id}:{renta.id_propietario}",
    )

    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def marcar_en_uso(id_renta: int, id_usuario_actual: int) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    if renta.id_arrendatario != id_usuario_actual:
        raise ApiError("Solo el arrendatario puede marcar en uso.", status_code=403)

    if renta.estado_renta != "confirmada":
        if renta.estado_renta in ("en_curso", "completada", "con_incidente"):
            return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)
        raise ApiError("La renta debe estar confirmada para iniciar el uso.", status_code=400)

    renta.estado_renta = "en_curso"
    _append_ts_note(renta, "EN_USO")
    db.session.commit()

    notificacion_service.crear_notificacion(
        renta.id_propietario,
        "EN_USO",
        "La renta fue marcada en uso.",
        meta={"id_renta": renta.id},
        event_key=f"EN_USO:{renta.id}:{renta.id_propietario}",
    )
    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "EN_USO",
        "Renta en uso.",
        meta={"id_renta": renta.id},
        event_key=f"EN_USO:{renta.id}:{renta.id_arrendatario}",
    )

    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def devolver(id_renta: int, id_usuario_actual: int) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    if renta.id_arrendatario != id_usuario_actual:
        raise ApiError("Solo el arrendatario puede devolver el artículo.", status_code=403)

    if renta.estado_renta != "en_curso":
        raise ApiError("La renta debe estar en uso para poder devolverse.", status_code=400)

    if renta.devuelto:
        return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)

    renta.devuelto = True
    renta.fecha_devolucion = datetime.utcnow()
    _append_ts_note(renta, "DEVOLUCION", renta.fecha_devolucion)
    db.session.commit()

    notificacion_service.crear_notificacion(
        renta.id_propietario,
        "DEVOLUCION",
        "El arrendatario marcó el objeto como devuelto.",
        meta={"id_renta": renta.id},
        event_key=f"DEVOLUCION:{renta.id}:{renta.id_propietario}",
    )
    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "DEVOLUCION",
        "Devolución registrada.",
        meta={"id_renta": renta.id},
        event_key=f"DEVOLUCION:{renta.id}:{renta.id_arrendatario}",
    )

    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def finalizar(id_renta: int, id_usuario_actual: int) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    if renta.id_propietario != id_usuario_actual:
        raise ApiError("Solo el dueño puede finalizar la renta.", status_code=403)

    if renta.estado_renta != "en_curso" or not renta.devuelto:
        # Idempotencia
        if renta.estado_renta == "completada" and renta.deposito_liberado:
            return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)
        raise ApiError("La renta debe estar devuelta para finalizarse.", status_code=400)

    renta.estado_renta = "completada"
    renta.deposito_liberado = True
    renta.fecha_liberacion_deposito = datetime.utcnow()
    _append_ts_note(renta, "FINALIZACION", renta.fecha_liberacion_deposito)
    _append_ts_note(renta, "DEPOSITO", renta.fecha_liberacion_deposito)
    db.session.commit()

    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "RENTA_FINALIZADA",
        "Renta finalizada.",
        meta={"id_renta": renta.id},
        event_key=f"RENTA_FINALIZADA:{renta.id}:{renta.id_arrendatario}",
    )
    notificacion_service.crear_notificacion(
        renta.id_propietario,
        "RENTA_FINALIZADA",
        "Renta finalizada.",
        meta={"id_renta": renta.id},
        event_key=f"RENTA_FINALIZADA:{renta.id}:{renta.id_propietario}",
    )

    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "DEPOSITO_LIBERADO",
        f"Depósito liberado: ${float(renta.monto_deposito or 0):.2f}",
        meta={"id_renta": renta.id, "monto_deposito": float(renta.monto_deposito or 0), "deposito_liberado": True},
        event_key=f"DEPOSITO_LIBERADO:{renta.id}:{renta.id_arrendatario}",
    )

    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def reportar_incidente(id_renta: int, id_usuario_actual: int, descripcion: str | None) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    if renta.id_arrendatario != id_usuario_actual and renta.id_propietario != id_usuario_actual:
        raise ApiError("No tienes permisos para reportar incidente.", status_code=403)

    # No permitir incidente si ya está finalizada
    if renta.estado_renta == "completada":
        raise ApiError("No se puede reportar incidente en una renta finalizada.", status_code=400)

    renta.estado_renta = "con_incidente"
    _append_ts_note(renta, "INCIDENTE")

    desc = (descripcion or "").strip()
    if desc:
        # Reutiliza campos existentes sin migración
        previo = renta.notas_devolucion or ""
        sep = "\n" if previo else ""
        renta.notas_devolucion = f"{previo}{sep}INCIDENTE: {desc}".strip()

    # Persistir/actualizar incidente de renta (1 por renta)
    desc_db = desc or "Incidente reportado"
    try:
        incidente = IncidenteRenta.query.filter_by(id_renta=renta.id).first()
        if not incidente:
            incidente = IncidenteRenta(id_renta=renta.id, descripcion=desc_db)
            db.session.add(incidente)
        else:
            incidente.descripcion = desc_db
    except (OperationalError, ProgrammingError):
        # Sin migraciones: se mantiene el incidente en notas/estado
        pass

    db.session.commit()

    otro = renta.id_propietario if renta.id_arrendatario == id_usuario_actual else renta.id_arrendatario
    notificacion_service.crear_notificacion(
        otro,
        "INCIDENTE_CREADO",
        "Se reportó un incidente en la renta.",
        meta={"id_renta": renta.id},
        event_key=f"INCIDENTE_CREADO:{renta.id}:{otro}",
    )

    notificacion_service.crear_notificacion(
        id_usuario_actual,
        "INCIDENTE_CREADO",
        "Incidente reportado.",
        meta={"id_renta": renta.id},
        event_key=f"INCIDENTE_CREADO:{renta.id}:{id_usuario_actual}",
    )
    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def resolver_incidente(
    id_renta: int,
    id_usuario_actual: int,
    decision: str,
    monto_retenido: float | None,
    nota: str | None,
    es_admin: bool = False,
) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    # Permisos: dueño o admin
    if renta.id_propietario != id_usuario_actual and not es_admin:
        raise ApiError("Solo el dueño o un admin puede resolver el incidente.", status_code=403)

    # Idempotencia: si ya se resolvió antes, responder 200 sin efectos colaterales.
    if renta.estado_renta != "con_incidente":
        try:
            inc_prev = IncidenteRenta.query.filter_by(id_renta=renta.id).first()
            if inc_prev and (getattr(inc_prev, "resolved_at", None) is not None or getattr(inc_prev, "decision", None) is not None):
                return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)
        except (OperationalError, ProgrammingError):
            pass
        raise ApiError("Solo se puede resolver un incidente si el estado actual es 'incidente'.", status_code=400)

    d = (decision or "").strip()
    if d not in ("liberar", "retener_parcial", "retener_total"):
        raise ApiError("Decisión inválida.", status_code=400)

    retenido = None
    deposito = float(renta.monto_deposito or 0)

    if d == "liberar":
        retenido = 0.0
    elif d == "retener_total":
        retenido = deposito
    elif d == "retener_parcial":
        if monto_retenido is None:
            raise ApiError("Debes indicar monto_retenido para retención parcial.", status_code=400)
        try:
            retenido = float(monto_retenido)
        except (TypeError, ValueError):
            raise ApiError("monto_retenido inválido.", status_code=400)
        # Regla: 0 < retenido < depósito
        if retenido <= 0 or retenido >= deposito:
            raise ApiError("monto_retenido debe ser mayor a 0 y menor al monto del depósito.", status_code=400)

    nota_norm = (nota or "").strip() or None
    if nota_norm is not None and len(nota_norm) > 300:
        raise ApiError("La nota no puede exceder 300 caracteres.", status_code=400)

    if d in ("retener_parcial", "retener_total") and not nota_norm:
        raise ApiError("La nota es obligatoria cuando se retiene el depósito.", status_code=400)

    now = datetime.utcnow()

    try:
        incidente = IncidenteRenta.query.filter_by(id_renta=renta.id).first()
        if not incidente:
            incidente = IncidenteRenta(id_renta=renta.id, descripcion="Incidente")
            db.session.add(incidente)

        # Idempotencia fuerte: si ya está resuelto, no mutar ni notificar.
        if getattr(incidente, "resolved_at", None) is not None or getattr(incidente, "decision", None) is not None:
            return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)

        incidente.decision = d
        incidente.monto_retenido = retenido
        incidente.nota = nota_norm
        incidente.resolved_at = now
    except (OperationalError, ProgrammingError):
        # Sin migraciones: igual finalizamos la renta para no romper el flujo
        pass

    # Resolver => finalizada
    renta.estado_renta = "completada"
    renta.deposito_liberado = bool(d == "liberar")
    # Guardamos el timestamp de resolución para la UX/timeline (aunque haya retención).
    renta.fecha_liberacion_deposito = now

    _append_ts_note(renta, "INCIDENTE_RESUELTO", renta.fecha_liberacion_deposito)
    _append_ts_note(renta, "DEPOSITO", renta.fecha_liberacion_deposito)

    db.session.commit()

    # Notificar arrendatario sobre resolución y depósito
    quien = "administrador" if es_admin else "dueño"
    if float(retenido or 0) > 0:
        msg_arr = f"Incidente resuelto: depósito retenido ${float(retenido):.2f}."
    else:
        msg_arr = f"Incidente resuelto: depósito liberado ${float(renta.monto_deposito or 0):.2f}."

    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "INCIDENTE_RESUELTO",
        msg_arr,
        meta={
            "id_renta": renta.id,
            "decision": d,
            "monto_retenido": float(retenido or 0),
            "monto_deposito": float(renta.monto_deposito or 0),
            "nota": nota_norm,
            "resuelto_por": quien,
        },
        event_key=f"INCIDENTE_RESUELTO:{renta.id}:{renta.id_arrendatario}",
    )
    if retenido and float(retenido) > 0:
        notificacion_service.crear_notificacion(
            renta.id_arrendatario,
            "DEPOSITO_RETENIDO",
            f"Depósito retenido: ${float(retenido):.2f}",
            meta={
                "id_renta": renta.id,
                "monto_retenido": float(retenido),
                "monto_deposito": float(renta.monto_deposito or 0),
                "nota": nota_norm,
                "resuelto_por": quien,
            },
            event_key=f"DEPOSITO_RETENIDO:{renta.id}:{renta.id_arrendatario}",
        )
    else:
        notificacion_service.crear_notificacion(
            renta.id_arrendatario,
            "DEPOSITO_LIBERADO",
            f"Depósito liberado: ${float(renta.monto_deposito or 0):.2f}",
            meta={"id_renta": renta.id, "monto_deposito": float(renta.monto_deposito or 0), "nota": nota_norm, "resuelto_por": quien},
            event_key=f"DEPOSITO_LIBERADO:{renta.id}:{renta.id_arrendatario}",
        )

    # Notificar dueño (o admin actuando) para visibilidad
    try:
        notificacion_service.crear_notificacion(
            renta.id_propietario,
            "INCIDENTE_RESUELTO",
            "Resolución de incidente aplicada." + (" (por administrador)." if es_admin else "."),
            meta={
                "id_renta": renta.id,
                "decision": d,
                "monto_retenido": float(retenido or 0),
                "monto_deposito": float(renta.monto_deposito or 0),
                "nota": nota_norm,
                "resuelto_por": quien,
            },
            event_key=f"INCIDENTE_RESUELTO:{renta.id}:{renta.id_propietario}",
        )
    except Exception:
        pass
    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def listar_rentas_usuario(id_usuario: int, como: str = "arrendatario") -> list[dict]:
    """
    Lista rentas de un usuario, según el rol en la renta:
    - como="arrendatario": rentas donde él rentó artículos.
    - como="propietario": rentas donde él es dueño del artículo.
    """

    if como not in ("arrendatario", "propietario"):
        raise ApiError("El parámetro 'como' debe ser 'arrendatario' o 'propietario'.", status_code=400)

    if como == "arrendatario":
        query = Renta.query.filter_by(id_arrendatario=id_usuario)
    else:
        query = Renta.query.filter_by(id_propietario=id_usuario)

    rentas = query.order_by(Renta.fecha_creacion.desc()).all()
    return [_renta_to_dict(r, id_usuario_actual=id_usuario) for r in rentas]


def coordinar_renta(id_renta: int, id_usuario_actual: int, payload: dict) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    _marcar_expirada_si_corresponde(renta)

    if renta.id_propietario != id_usuario_actual:
        raise ApiError("Solo el dueño puede coordinar.", status_code=403)

    estado_publico = _estado_publico(renta)
    if _es_estado_cerrado(estado_publico):
        raise ApiError("La renta no permite coordinación en el estado actual.", status_code=400)
    if renta.estado_renta not in ("pendiente_pago", "pagada", "confirmada"):
        raise ApiError("La renta no permite coordinación en el estado actual.", status_code=400)

    modo = payload.get("modo_entrega")
    if modo is not None:
        modo = str(modo).strip().lower()
        if modo not in ("arrendador", "neutral"):
            raise ApiError("modo_entrega inválido.", status_code=400)
        renta.modo_entrega = modo

    zp = payload.get("zona_publica")
    if zp is not None:
        zp = str(zp).strip()
        if len(zp) > 120:
            raise ApiError("zona_publica no puede exceder 120 caracteres.", status_code=400)
        renta.zona_publica = zp or None

    de = payload.get("direccion_entrega")
    if de is not None:
        de = str(de).strip()
        if len(de) > 300:
            raise ApiError("direccion_entrega no puede exceder 300 caracteres.", status_code=400)
        renta.direccion_entrega = de or None

    # Selección de punto de entrega seguro (compat: guardado en notas_devolucion como PE:{json})
    entrega_modo = payload.get("entrega_modo")
    if entrega_modo is not None:
        entrega_modo = str(entrega_modo).strip().lower()
        if entrega_modo not in ("domicilio", "punto_entrega"):
            raise ApiError("entrega_modo inválido.", status_code=400)

        if entrega_modo == "domicilio":
            _pe_set_in_notes(renta, None)
        else:
            id_punto = payload.get("id_punto_entrega")
            try:
                id_punto_int = int(id_punto)
            except Exception:
                raise ApiError("id_punto_entrega inválido.", status_code=400)

            try:
                p: PuntoEntrega | None = PuntoEntrega.query.get(id_punto_int)
                if not p or not getattr(p, "activo", False):
                    raise ApiError("Punto de entrega no disponible.", status_code=400)
                pe = {
                    "id": p.id,
                    "nombre": p.nombre,
                    "direccion": p.direccion,
                    "ciudad": None,
                    "estado": None,
                    "horario": None,
                    "notas": None,
                }
            except (OperationalError, ProgrammingError):
                # Compat: si faltan migraciones, no rompemos, pero tampoco permitimos selección.
                raise ApiError("Puntos de entrega no disponibles.", status_code=501)

            _pe_set_in_notes(renta, pe)
            # Para UX: mostrar el nombre del punto como zona pública y evitar dirección privada
            renta.zona_publica = p.nombre
            renta.direccion_entrega = None

    ventanas_entrega = payload.get("ventanas_entrega_propuestas")
    if ventanas_entrega is not None:
        if not isinstance(ventanas_entrega, list):
            raise ApiError("ventanas_entrega_propuestas debe ser una lista.", status_code=400)
        ve = [str(x).strip() for x in ventanas_entrega if str(x).strip()]
        if not (2 <= len(ve) <= 3):
            raise ApiError("Debes proponer 2–3 ventanas de entrega.", status_code=400)
        if any(len(x) > 120 for x in ve):
            raise ApiError("Cada ventana no puede exceder 120 caracteres.", status_code=400)
        renta.ventanas_entrega_propuestas = _dump_list_field(ve)
        # Al reproponer, limpiar selección y confirmación
        renta.ventana_entrega_elegida = None
        renta.coordinacion_confirmada = False

    ventanas_devolucion = payload.get("ventanas_devolucion_propuestas")
    if ventanas_devolucion is not None:
        if not isinstance(ventanas_devolucion, list):
            raise ApiError("ventanas_devolucion_propuestas debe ser una lista.", status_code=400)
        vd = [str(x).strip() for x in ventanas_devolucion if str(x).strip()]
        if not (2 <= len(vd) <= 3):
            raise ApiError("Debes proponer 2–3 ventanas de devolución.", status_code=400)
        if any(len(x) > 120 for x in vd):
            raise ApiError("Cada ventana no puede exceder 120 caracteres.", status_code=400)
        renta.ventanas_devolucion_propuestas = _dump_list_field(vd)
        renta.ventana_devolucion_elegida = None
        renta.coordinacion_confirmada = False

    confirmar = bool(payload.get("confirmar"))
    if confirmar:
        if not renta.ventana_entrega_elegida or not renta.ventana_devolucion_elegida:
            raise ApiError("El arrendatario debe elegir ventanas antes de confirmar.", status_code=400)
        renta.coordinacion_confirmada = True
        _append_ts_note(renta, "COORDINACION_CONFIRMADA")

    db.session.commit()

    pe_after = _pe_extract_from_notes(renta)
    pe_nombre_after = _pe_nombre(pe_after)

    if payload.get("confirmar"):
        notificacion_service.crear_notificacion(
            renta.id_arrendatario,
            "COORDINACION_CONFIRMADA",
            (
                f"La coordinación fue confirmada. Punto de entrega: {pe_nombre_after}."
                if pe_nombre_after
                else "La coordinación de entrega/devolución fue confirmada."
            ),
            meta={"id_renta": renta.id, "punto_entrega": pe_nombre_after},
            event_key=f"COORDINACION_CONFIRMADA:{renta.id}:{renta.id_arrendatario}",
        )
        notificacion_service.crear_notificacion(
            renta.id_propietario,
            "COORDINACION_CONFIRMADA",
            (
                f"Coordinación confirmada. Punto de entrega: {pe_nombre_after}."
                if pe_nombre_after
                else "Coordinación confirmada."
            ),
            meta={"id_renta": renta.id, "punto_entrega": pe_nombre_after},
            event_key=f"COORDINACION_CONFIRMADA:{renta.id}:{renta.id_propietario}",
        )
    else:
        notificacion_service.crear_notificacion(
            renta.id_arrendatario,
            "COORDINACION_PROPUESTA",
            (
                f"Se propuso punto de entrega: {pe_nombre_after}."
                if pe_nombre_after
                else "El dueño propuso ventanas de entrega/devolución."
            ),
            meta={"id_renta": renta.id, "punto_entrega": pe_nombre_after},
            event_key=f"COORDINACION_PROPUESTA:{renta.id}:{renta.id_arrendatario}",
        )
        notificacion_service.crear_notificacion(
            renta.id_propietario,
            "COORDINACION_PROPUESTA",
            "Propuesta de coordinación enviada.",
            meta={"id_renta": renta.id, "punto_entrega": pe_nombre_after},
            event_key=f"COORDINACION_PROPUESTA:{renta.id}:{renta.id_propietario}",
        )
    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def aceptar_coordinacion(id_renta: int, id_usuario_actual: int, payload: dict) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    _marcar_expirada_si_corresponde(renta)

    if renta.id_arrendatario != id_usuario_actual:
        raise ApiError("Solo el arrendatario puede aceptar la coordinación.", status_code=403)

    estado_publico = _estado_publico(renta)
    if _es_estado_cerrado(estado_publico):
        raise ApiError("La renta no permite coordinación en el estado actual.", status_code=400)
    if estado_publico == "pendiente_pago":
        raise ApiError("Debes pagar antes de aceptar la coordinación.", status_code=400)
    if renta.estado_renta not in ("pagada", "confirmada"):
        raise ApiError("La renta no permite aceptar coordinación en el estado actual.", status_code=400)

    ve = str(payload.get("ventana_entrega") or "").strip()
    vd = str(payload.get("ventana_devolucion") or "").strip()
    if not ve or not vd:
        raise ApiError("Debes elegir ventana de entrega y devolución.", status_code=400)

    propuestas_entrega = _parse_list_field(renta.ventanas_entrega_propuestas)
    propuestas_devolucion = _parse_list_field(renta.ventanas_devolucion_propuestas)
    if ve not in propuestas_entrega:
        raise ApiError("ventana_entrega inválida.", status_code=400)
    if vd not in propuestas_devolucion:
        raise ApiError("ventana_devolucion inválida.", status_code=400)

    renta.ventana_entrega_elegida = ve
    renta.ventana_devolucion_elegida = vd
    renta.coordinacion_confirmada = False

    _append_ts_note(renta, "COORDINACION_ACEPTADA")

    db.session.commit()

    pe_after = _pe_extract_from_notes(renta)
    pe_nombre_after = _pe_nombre(pe_after)

    notificacion_service.crear_notificacion(
        renta.id_propietario,
        "COORDINACION_ACEPTADA",
        (
            f"Se aceptó el punto de entrega: {pe_nombre_after}."
            if pe_nombre_after
            else "El arrendatario eligió ventanas de entrega/devolución."
        ),
        meta={"id_renta": renta.id, "punto_entrega": pe_nombre_after},
        event_key=f"COORDINACION_ACEPTADA:{renta.id}:{renta.id_propietario}",
    )
    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "COORDINACION_ACEPTADA",
        (
            f"Aceptaste el punto de entrega: {pe_nombre_after}."
            if pe_nombre_after
            else "Selección de ventanas enviada."
        ),
        meta={"id_renta": renta.id, "punto_entrega": pe_nombre_after},
        event_key=f"COORDINACION_ACEPTADA:{renta.id}:{renta.id_arrendatario}",
    )
    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def confirmar_entrega_otp(id_renta: int, id_usuario_actual: int, payload: dict) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    _marcar_expirada_si_corresponde(renta)

    if renta.id_propietario != id_usuario_actual:
        raise ApiError("Solo el dueño puede confirmar la entrega por OTP.", status_code=403)

    estado_publico = _estado_publico(renta)
    if _es_estado_cerrado(estado_publico):
        raise ApiError("La renta no permite confirmar entrega en el estado actual.", status_code=400)

    if renta.estado_renta not in ("pagada", "confirmada"):
        raise ApiError("La renta debe estar pagada para confirmar entrega.", status_code=400)

    codigo = str(payload.get("codigo") or "").strip()
    if not codigo or len(codigo) != 6 or not codigo.isdigit():
        raise ApiError("Código OTP inválido.", status_code=400)
    if not renta.codigo_entrega or codigo != renta.codigo_entrega:
        raise ApiError("Código OTP incorrecto.", status_code=400)

    checklist = payload.get("checklist")
    if checklist is not None:
        checklist = str(checklist).strip()
        if len(checklist) > 800:
            raise ApiError("checklist_entrega no puede exceder 800 caracteres.", status_code=400)
        renta.checklist_entrega = checklist or None

    renta.entregado = True
    renta.fecha_entrega = datetime.utcnow()
    renta.estado_renta = "en_curso"

    _append_ts_note(renta, "ENTREGA_CONFIRMADA", renta.fecha_entrega)
    _append_ts_note(renta, "EN_USO", renta.fecha_entrega)

    db.session.commit()

    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "ENTREGA_CONFIRMADA_OTP",
        "La entrega fue confirmada por OTP.",
        meta={"id_renta": renta.id},
        event_key=f"ENTREGA_CONFIRMADA_OTP:{renta.id}:{renta.id_arrendatario}",
    )
    notificacion_service.crear_notificacion(
        renta.id_propietario,
        "ENTREGA_CONFIRMADA_OTP",
        "Entrega confirmada por OTP.",
        meta={"id_renta": renta.id},
        event_key=f"ENTREGA_CONFIRMADA_OTP:{renta.id}:{renta.id_propietario}",
    )
    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def confirmar_devolucion_otp(id_renta: int, id_usuario_actual: int, payload: dict) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    _marcar_expirada_si_corresponde(renta)

    if renta.id_propietario != id_usuario_actual:
        raise ApiError("Solo el dueño puede confirmar la devolución por OTP.", status_code=403)

    estado_publico = _estado_publico(renta)
    if _es_estado_cerrado(estado_publico):
        raise ApiError("La renta no permite confirmar devolución en el estado actual.", status_code=400)

    if renta.estado_renta != "en_curso" or renta.devuelto:
        raise ApiError("La renta debe estar en uso para confirmar devolución.", status_code=400)

    codigo = str(payload.get("codigo") or "").strip()
    if not codigo or len(codigo) != 6 or not codigo.isdigit():
        raise ApiError("Código OTP inválido.", status_code=400)
    if not renta.codigo_devolucion or codigo != renta.codigo_devolucion:
        raise ApiError("Código OTP incorrecto.", status_code=400)

    checklist = payload.get("checklist")
    if checklist is not None:
        checklist = str(checklist).strip()
        if len(checklist) > 800:
            raise ApiError("checklist_devolucion no puede exceder 800 caracteres.", status_code=400)
        renta.checklist_devolucion = checklist or None

    renta.devuelto = True
    renta.fecha_devolucion = datetime.utcnow()

    _append_ts_note(renta, "DEVOLUCION", renta.fecha_devolucion)

    db.session.commit()

    notificacion_service.crear_notificacion(
        renta.id_arrendatario,
        "DEVOLUCION_CONFIRMADA_OTP",
        "La devolución fue confirmada por OTP.",
        meta={"id_renta": renta.id},
        event_key=f"DEVOLUCION_CONFIRMADA_OTP:{renta.id}:{renta.id_arrendatario}",
    )
    notificacion_service.crear_notificacion(
        renta.id_propietario,
        "DEVOLUCION_CONFIRMADA_OTP",
        "Devolución confirmada por OTP.",
        meta={"id_renta": renta.id},
        event_key=f"DEVOLUCION_CONFIRMADA_OTP:{renta.id}:{renta.id_propietario}",
    )
    return _renta_to_dict(renta, id_usuario_actual=id_usuario_actual)


def obtener_chat(id_renta: int, id_usuario_actual: int) -> list[dict]:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    _marcar_expirada_si_corresponde(renta)
    if id_usuario_actual not in (renta.id_arrendatario, renta.id_propietario):
        raise ApiError("No tienes permisos para ver el chat.", status_code=403)
    if not _chat_habilitado(renta, id_usuario_actual):
        raise ApiError("El chat no está habilitado para esta renta.", status_code=400)

    try:
        msgs = (
            MensajeRenta.query.filter_by(id_renta=renta.id)
            .order_by(MensajeRenta.created_at.asc(), MensajeRenta.id.asc())
            .limit(120)
            .all()
        )
    except (OperationalError, ProgrammingError):
        raise ApiError("Chat no disponible (faltan migraciones).", status_code=501)

    return [
        {
            "id": m.id,
            "id_renta": m.id_renta,
            "id_emisor": m.id_emisor,
            "mensaje": m.mensaje,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]


def enviar_chat(id_renta: int, id_usuario_actual: int, payload: dict) -> dict:
    renta: Renta | None = Renta.query.get(id_renta)
    if not renta:
        raise ApiError("Renta no encontrada.", status_code=404)

    _marcar_expirada_si_corresponde(renta)
    if id_usuario_actual not in (renta.id_arrendatario, renta.id_propietario):
        raise ApiError("No tienes permisos para enviar mensajes.", status_code=403)
    if not _chat_habilitado(renta, id_usuario_actual):
        raise ApiError("El chat no está habilitado para esta renta.", status_code=400)

    mensaje = _validar_mensaje_chat(payload.get("mensaje"))

    try:
        # Rate limit simple: 1 mensaje cada N segundos por usuario/renta
        limit_s = _get_chat_rate_limit_seconds()
        if limit_s > 0:
            last = (
                MensajeRenta.query.filter_by(id_renta=renta.id, id_emisor=id_usuario_actual)
                .order_by(MensajeRenta.created_at.desc(), MensajeRenta.id.desc())
                .first()
            )
            if last and last.created_at:
                delta = (datetime.utcnow() - last.created_at).total_seconds()
                if delta < limit_s:
                    raise ApiError(
                        "Estás enviando muy rápido. Intenta de nuevo en unos segundos.",
                        status_code=429,
                    )

        msg = MensajeRenta(id_renta=renta.id, id_emisor=id_usuario_actual, mensaje=mensaje)
        db.session.add(msg)
        db.session.commit()
    except (OperationalError, ProgrammingError):
        raise ApiError("Chat no disponible (faltan migraciones).", status_code=501)

    # Notificar a la contraparte (best-effort)
    try:
        otro = renta.id_propietario if id_usuario_actual == renta.id_arrendatario else renta.id_arrendatario
        notificacion_service.crear_notificacion(
            otro,
            "CHAT",
            "Nuevo mensaje en una renta.",
            meta={"id_renta": renta.id, "chat": True},
        )
    except Exception:
        pass

    return {
        "id": msg.id,
        "id_renta": msg.id_renta,
        "id_emisor": msg.id_emisor,
        "mensaje": msg.mensaje,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
