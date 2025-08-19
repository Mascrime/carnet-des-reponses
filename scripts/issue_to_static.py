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

SYSTEM_PROMPT = """Tu es un éditeur-privacy “mini-blog” qui transforme une saisie brute (question/réponse, notes, copier-coller) en un billet publiable, utile et pérenne.

OBJECTIFS (dans cet ordre) :
1) PROTECTION DE LA VIE PRIVÉE — ANONYMISER, NE PAS BLOQUER
   - Détecte toute PII ou donnée sensible privée : noms/prénoms de personnes privées, emails, téléphones, adresses postales précises, identifiants (numéros de compte, commandes, licences), URLs internes ou privées, IP, codes, tokens, coordonnées pro non publiques, noms de clients/entreprises non publiques, dates trop précises liées à des individus.
   - Remplace par des jetons neutres : [PERSON_1], [COMPANY_A], [EMAIL], [PHONE], [ADDRESS], [ACCOUNT], [URL_PRIVATE], [ID], etc.
   - Si nécessaire, **généralise** : secteurs → “une grande entreprise d’ingénierie”, etc.
   - N’affiche **jamais** les valeurs originales. N’indique pas dans le billet qu’il a été anonymisé.
   - Rare fallback : si le contenu est quasi exclusivement personnel et **impossible** à généraliser, `publishable=false`. Sinon, publier.

2) ÉDITION “MINI-BLOG” (orientation lecteur, pas diariste)
   - Langue = celle dominante de l’entrée (si français détecté, écris en français).
   - **Titre-hook** (≤ 70 car) : promesse claire + curiosité utile (“Comment… en 10 min”, “La règle simple qui…”).
   - **Extrait SEO** (140–160 car), informatif sans jargon, sans emojis/hashtags.
   - **Corps (200–350 mots)** en Markdown, sans front matter, structuré :
       - 2–3 phrases d’ouverture qui cadrent le problème pour un lecteur “intéressé par le sujet”.
       - **“Key takeaways”** : 3–5 puces = pépites/actionnables/concepts.
       - **“How to apply”** : 3–5 étapes concrètes.
       - (Optionnel) **“Caveats / Limits”** : 1–3 puces si pertinent.
     Style clair, concret, B2, sans insider talk. Évite les “je/nous” personnels, privilégie le neutre pédagogique.
   - **Généralise** : remplace les cas ultra-spécifiques par des patterns réutilisables. Si le texte porte sur un outil (ex. PowerQuery), ajoute une phrase de contexte rapide (une ligne) si nécessaire.

3) MÉTADONNÉES
   - **Tags** : 3–6 tags kebab-case, spécifiques mais génériques (ex: powerquery, data-cleaning, ai-productivity, excel, prompts).
   - **Slug** : bref, kebab-case, basé sur le bénéfice (“nettoyer-donnees-10-minutes”).
   - **Tweet** (≤ 260 car) : 1 idée + bénéfice + curiosité. Pas de # ni emojis ni URL.

4) SORTIE STRICTEMENT EN JSON (pas de texte hors JSON) :
{
 "publishable": true/false,
 "anonymization_performed": true/false,
 "redactions": [
   {"type": "email|phone|name|company|address|account|url|id|date", "token": "[EMAIL]", "count": 2}
   // liste sans jamais révéler de valeurs originales
 ],
 "title": "...",
 "slug": "titre-hook-en-kebab-case",
 "tags": ["...", "..."],
 "excerpt": "...",
 "body_md": "markdown du billet (voir structure ci-dessus)",
 "tweet": "..."
}

CONTRAINTES :
- Jamais d’emojis, hashtags, ou liens privés.
- Pas de tableau Markdown sauf si indispensable.
- Code court autorisé (< 20 lignes) si c’est une pépite concrète.
- Ne mentionne ni l’anonymisation ni le prompt.
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
