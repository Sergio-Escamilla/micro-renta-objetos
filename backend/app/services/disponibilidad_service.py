from datetime import datetime

from sqlalchemy import and_

from app.extensions.db import db
from app.models.disponibilidad_articulo import DisponibilidadArticulo
from app.models.renta import Renta
from app.utils.errors import ApiError


# Estados de renta que bloquean el calendario del artículo
ESTADOS_RENTA_BLOQUEO = (
    "pendiente_pago",
    "pagada",
    "confirmada",
    "en_curso",
)


def _rangos_solapan(inicio1: datetime, fin1: datetime, inicio2: datetime, fin2: datetime) -> bool:
    """
    Devuelve True si los rangos [inicio1, fin1) y [inicio2, fin2) se solapan.
    Fórmula estándar: A.inicio < B.fin AND A.fin > B.inicio
    """
    return inicio1 < fin2 and fin1 > inicio2


def validar_disponibilidad_articulo(id_articulo: int, fecha_inicio: datetime, fecha_fin: datetime) -> None:
    """
    Lanza ApiError si el artículo NO está disponible en ese rango.
    Valida:
    - Bloqueos manuales en disponibilidad_articulo (disponible = 0).
    - Rentas existentes en estados que bloquean el calendario.
    """

    # 1) Bloqueos en disponibilidad_articulo
    bloqueos = DisponibilidadArticulo.query.filter(
        DisponibilidadArticulo.id_articulo == id_articulo,
        DisponibilidadArticulo.disponible == False,  # noqa: E712
        DisponibilidadArticulo.fecha_inicio < fecha_fin,
        DisponibilidadArticulo.fecha_fin > fecha_inicio,
    ).all()

    if bloqueos:
        raise ApiError(
            "El artículo no está disponible en las fechas seleccionadas (bloqueo de disponibilidad).",
            status_code=409,
        )

    # 2) Rentas que se solapan
    renta_conflictiva = (
        Renta.query.filter(
            Renta.id_articulo == id_articulo,
            Renta.estado_renta.in_(ESTADOS_RENTA_BLOQUEO),
            Renta.fecha_inicio < fecha_fin,
            Renta.fecha_fin > fecha_inicio,
        )
        .with_for_update(read=True)
        .first()
    )

    if renta_conflictiva:
        raise ApiError(
            "El artículo ya está reservado en las fechas seleccionadas.",
            status_code=409,
            payload={"id_renta_conflictiva": renta_conflictiva.id},
        )
