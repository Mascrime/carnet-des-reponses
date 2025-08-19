#!/usr/bin/env python3
import os, re, json, sys, hashlib, requests
from pathlib import Path
from datetime import datetime, timezone
from markdown import markdown

ISSUE_TITLE = os.getenv("ISSUE_TITLE","").strip()
ISSUE_BODY  = os.getenv("ISSUE_BODY","").strip()
HINT_TAGS   = os.getenv("HINT_TAGS","").strip()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL   = "gemini-2.5-flash"
URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

SYSTEM_PROMPT = """Tu es un éditeur. Tâches:
1) Détecte si le contenu est trop personnel (noms privés, coordonnées, infos médicales/financières).
2) Si personnel -> {"publishable": false} uniquement.
3) Sinon, renvoie STRICTEMENT ce JSON:
{
 "publishable": true,
 "title": "≤70 car",
 "excerpt": "≤160 car",
 "tags": ["3-6 tags"],
 "body_md": "150–300 mots en Markdown (sans front matter)",
 "tweet": "≤260 car (sans # ni emoji)"
}
"""

def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s).strip('-')
    return s or hashlib.sha1(s.encode()).hexdigest()[:8]

def call_gemini(issue_title, issue_body, hint_tags):
    payload = {
      "contents": [
        {"role": "user", "parts": [
          {"text": SYSTEM_PROMPT +
            "\n\nTitre Issue: " + issue_title +
            "\n\nContenu:\n" + issue_body +
            "\n\nTags suggérés: " + hint_tags}
        ]}
      ]
    }
    r = requests.post(URL, json=payload, timeout=60)
    r.raise_for_status()
    out = r.json()
    text = out["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = text.strip('`').strip()
    if text.lower().startswith('json'):
        text = text[4:].strip()
    return json.loads(text)

def ensure_files():
    Path("posts").mkdir(exist_ok=True)
    # .nojekyll pour désactiver Jekyll
    Path(".nojekyll").touch()
    if not Path("posts.json").exists():
        Path("posts.json").write_text("[]\n", encoding="utf-8")

def write_post(meta):
    slug = slugify(meta["title"])
    date_iso = datetime.now(timezone.utc).date().isoformat()
    # Convertir markdown -> HTML
    body_html = markdown(meta["body_md"], extensions=["extra","sane_lists","tables"])
    html = f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>{meta['title']} — Carnet des Réponses</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <link rel="stylesheet" href="../assets/style.css" />
  <meta name="description" content="{meta['excerpt']}"/>
</head>
<body>
  <main class="wrap">
    <a class="back" href="../index.html">← Retour</a>
    <h1>{meta['title']}</h1>
    <p class="muted">Publié le {date_iso}</p>
    <article>
      {body_html}
    </article>
  </main>
</body>
</html>
"""
    Path("posts").mkdir(exist_ok=True)
    Path(f"posts/{slug}.html").write_text(html, encoding="utf-8")
    # update posts.json
    idx_path = Path("posts.json")
    posts = []
    try:
        posts = json.loads(idx_path.read_text(encoding="utf-8") or "[]")
    except Exception:
        posts = []
    # remove same slug if exists
    posts = [p for p in posts if p.get("slug") != slug]
    posts.append({"title": meta["title"], "date": date_iso, "slug": slug})
    posts.sort(key=lambda p: p["date"], reverse=True)
    idx_path.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return slug

def main():
    ensure_files()
    meta = call_gemini(ISSUE_TITLE, ISSUE_BODY, HINT_TAGS)
    if not meta.get("publishable", False):
        # Rien à générer (on ne fail pas le job)
        print("NON_PUBLISHABLE")
        return
    slug = write_post(meta)
    # imprime UNIQUEMENT le slug pour le step GitHub
    print(slug)

if __name__ == "__main__":
    main()
