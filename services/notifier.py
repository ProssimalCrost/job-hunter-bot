"""
Envio de notificação por WhatsApp via CallMeBot — gratuito, sem Twilio.

Como funciona: CallMeBot expõe um número de WhatsApp que, depois de você
autorizar uma vez (mandando uma mensagem pra ele), passa a aceitar
mensagens via uma simples requisição HTTP GET.

Limitações a respeitar (é um serviço gratuito e pessoal, não comercial):
- ~1 mensagem por minuto por número.
- Não use para volume alto ou fins comerciais.
"""

import os
import time
import requests
from urllib.parse import quote

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"
MAX_MESSAGE_CHARS = 1800  # margem de segurança abaixo do limite do serviço


def _send_single(text: str, phone: str, apikey: str) -> bool:
    params = {
        "phone": phone,
        "text": text,
        "apikey": apikey,
    }
    url = f"{CALLMEBOT_URL}?phone={quote(phone)}&text={quote(text)}&apikey={quote(apikey)}"
    try:
        resp = requests.get(url, timeout=15)
        ok = resp.status_code == 200
        if not ok:
            print(f"[notifier] CallMeBot respondeu {resp.status_code}: {resp.text[:200]}")
        return ok
    except requests.RequestException as e:
        print(f"[notifier] erro de rede ao enviar WhatsApp: {e}")
        return False


def send_whatsapp_digest(jobs: list[dict]) -> None:
    """Manda um resumo das vagas novas. Quebra em vários envios se precisar."""
    phone = os.getenv("CALLMEBOT_PHONE")
    apikey = os.getenv("CALLMEBOT_APIKEY")

    if not phone or not apikey:
        print("[notifier] CALLMEBOT_PHONE/CALLMEBOT_APIKEY não configurados no .env")
        return

    if not jobs:
        return

    header = f"🔎 {len(jobs)} vaga(s) nova(s) nas últimas 24h:\n\n"
    chunk = header
    chunks = []

    # agrupa por área (TI / Elétrica) pra mensagem não virar lista misturada
    by_area = {}
    for job in jobs:
        by_area.setdefault(job.get("area", "Vagas"), []).append(job)

    for area, area_jobs in by_area.items():
        section = f"— {area} ({len(area_jobs)}) —\n"
        if len(chunk) + len(section) > MAX_MESSAGE_CHARS:
            chunks.append(chunk)
            chunk = ""
        chunk += section

        for job in area_jobs:
            line = (
                f"• {job['title']} — {job['company']}\n"
                f"  📍 {job['location']}\n"
                f"  {job['link']}\n\n"
            )
            if len(chunk) + len(line) > MAX_MESSAGE_CHARS:
                chunks.append(chunk)
                chunk = ""
            chunk += line

    if chunk:
        chunks.append(chunk)

    for i, part in enumerate(chunks):
        _send_single(part.strip(), phone, apikey)
        if i < len(chunks) - 1:
            time.sleep(65)  # respeita o limite de ~1 msg/min do CallMeBot
