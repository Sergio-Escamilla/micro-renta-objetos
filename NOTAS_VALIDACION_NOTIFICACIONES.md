# Validación manual – Notificaciones (MVP)

Pantalla a revisar: **Perfil** (sección “Notificaciones”, contador y lista).

## Checklist (5 pasos)

1) **Pago genera notificación**
- Acción: crea una renta como arrendatario y pulsa “Pagar”.
- Esperado: en Perfil del dueño aparece una notificación tipo **PAGO**; el contador sube (+1).

2) **Cancelar / Expirar genera notificación**
- Acción A: cancela una renta (según reglas) desde el resumen.
- Esperado: la contraparte ve una notificación tipo **CANCELACION**.
- Acción B (expirar): crea una renta y espera >15 min sin pagar; entra a la renta/intentá pagar para disparar expiración.
- Esperado: arrendatario y dueño reciben notificación tipo **EXPIRACION**.

3) **Coordinar / Aceptar genera notificación**
- Acción: dueño propone ventanas (coordinar) y arrendatario acepta.
- Esperado: arrendatario ve **COORDINACION_PROPUESTA** (o **COORDINACION_CONFIRMADA** si el dueño confirma), y dueño ve **COORDINACION_ACEPTADA**.

4) **OTP entrega / devolución genera notificación**
- Acción: dueño confirma entrega por OTP y luego devolución por OTP.
- Esperado: arrendatario ve **ENTREGA_CONFIRMADA_OTP** y **DEVOLUCION_CONFIRMADA_OTP**.

5) **Marcar leída funciona y baja contador**
- Acción: en Perfil pulsa “Marcar leída” en una notificación.
- Esperado: cambia a “Leída” y el contador de “nuevas” disminuye.

## Debug mínimo (solo si algo no aparece)

Hay logs puntuales desactivados por defecto. Para activarlos temporalmente:
- En `backend/.env` agrega `NOTIFICACIONES_DEBUG=1` y reinicia `flask run`.
- Esperado en consola: logs al crear notificación y al hacer GET `/api/notificaciones`.

Nota: dejar `NOTIFICACIONES_DEBUG` en `0` o sin definir para no generar ruido.
