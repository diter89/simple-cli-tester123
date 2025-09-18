import os
import json
import argparse
import requests
from pathlib import Path
from rich import print

API_KEY = os.getenv("FIREWORKS_API_KEY", "fw_xxx_gantilah")

EXTRACT_PROMPT = """
Kamu menerima isi log HTTP dari browser (DevTools → Copy as cURL / Copy All as HAR).
Tugasmu adalah mengekstrak hanya HEADER REQUEST HTTP penting dari log tersebut.

Ambil hanya jika tersedia, tanpa menebak:
- authorization
- x-csrf-token
- cookie
- user-agent

Hasilkan dalam format JSON Python valid. Jangan tambahkan komentar, teks tambahan, atau blok kode markdown.
"""

def extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            json.loads(text[start:end + 1]) 
            return text[start:end + 1]
        except json.JSONDecodeError:
            pass
    return "{}"

def clean_cookies(raw_cookie: str) -> str:
    keys_ordered = [
        "auth_token", "ct0", "personalization_id",
        "guest_id_ads", "guest_id_marketing", "guest_id",
        "twid", "lang", "kdt"
    ]
    cookie_dict = {}
    
    for part in raw_cookie.split(";"):
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            if key in keys_ordered:
                cookie_dict[key] = value
    
    if "auth_token" not in cookie_dict or "ct0" not in cookie_dict:
        print("[red]Error: Cookie missing required keys (auth_token or ct0)![/red]")
        return ""

    cleaned = [f"{key}={cookie_dict[key]}" for key in keys_ordered if key in cookie_dict]
    return "; ".join(cleaned)

def extract_important_headers(raw_log: str) -> dict:
    payload = {
        "model": "accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new",
        "max_tokens": 2048,
        "temperature": 0.1,
        "top_p": 1,
        "messages": [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": raw_log}
        ]
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post("https://api.fireworks.ai/inference/v1/chat/completions",
                            headers=headers, data=json.dumps(payload), timeout=40)
        res.raise_for_status()
        raw = res.json()["choices"][0]["message"]["content"]
        print("🧾 [DEBUG] Output LLM:\n", raw)
        result = json.loads(extract_json(raw))
        
        if not result.get("authorization") or not result.get("x-csrf-token") or not result.get("cookie"):
            print("[red]Error: Missing required headers (authorization, x-csrf-token, or cookie)![/red]")
            return {}
        
        return result
    except Exception as e:
        print(f"[red]Gagal parsing: {e}[/red]")
        return {}

def main():
    parser = argparse.ArgumentParser(description="Ekstrak header penting Twitter/X dari file log DevTools.")
    parser.add_argument("--file", "-f", required=True, help="File log input.")
    parser.add_argument("--save", "-s", default="result.json", help="Nama file output.")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[red]❌ File '{args.file}' tidak ditemukan.[/red]")
        return

    raw_log = file_path.read_text(encoding="utf-8")
    print("📦 Mengirim log ke Dobby (Fireworks AI)...\n")
    result = extract_important_headers(raw_log)

    if result:
        if "cookie" in result:
            cleaned_cookie = clean_cookies(result["cookie"])
            if not cleaned_cookie:
                return
            result["cookie"] = cleaned_cookie

        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"[green]✅ Header berhasil disimpan di: {args.save}[/green]")
    else:
        print("[red]⚠️ Tidak ada header yang berhasil diekstrak.[/red]")

if __name__ == "__main__":
    main()
