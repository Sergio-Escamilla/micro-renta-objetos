import json
from datetime import datetime
from pathlib import Path


def send_email(to: str, subject: str, body: str) -> None:
	"""Mock de envío de email.

	En lugar de enviar correos reales, guarda el mensaje en un outbox local.
	Esto permite probar el flujo de verificación por link en desarrollo.
	"""

	to_s = (to or "").strip()
	subject_s = (subject or "").strip()
	body_s = body or ""

	out_dir = Path(__file__).resolve().parents[2] / "tmp"
	out_dir.mkdir(parents=True, exist_ok=True)
	out_file = out_dir / "email_outbox.jsonl"

	payload = {
		"to": to_s,
		"subject": subject_s,
		"body": body_s,
		"created_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
	}

	with out_file.open("a", encoding="utf-8") as f:
		f.write(json.dumps(payload, ensure_ascii=False) + "\n")

	# Log amigable en consola
	print(f"[email_mock] to={to_s} subject={subject_s}")
