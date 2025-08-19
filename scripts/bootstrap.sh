#!/usr/bin/env bash
set -euo pipefail

mkdir -p assets posts
[ -f .nojekyll ] || touch .nojekyll
[ -f posts.json ] || echo "[]" > posts.json

if [ ! -f assets/style.css ]; then
  cat > assets/style.css <<'CSS'
:root{--fg:#111;--muted:#666;--link:#0a58ca;--bg:#fff;--card:#f7f7f7}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu}
.wrap{max-width:850px;margin:0 auto;padding:24px}
header.wrap{padding-top:32px}
h1{margin:0 0 6px 0;font-size:28px}
.sub{margin:0;color:var(--muted)}
h2{margin-top:24px}
.posts{list-style:none;padding:0;margin:12px 0}
.posts li{display:flex;justify-content:space-between;align-items:baseline;padding:10px 12px;border-radius:10px;background:var(--card);margin-bottom:8px}
.posts a{text-decoration:none;color:var(--link);font-weight:600}
.posts .date{color:var(--muted);font-size:14px;margin-left:12px;white-space:nowrap}
.muted{color:var(--muted)}
a{color:var(--link)}
article{background:var(--card);padding:18px;border-radius:12px}
.back{display:inline-block;margin:8px 0}
CSS
fi

if [ ! -f assets/app.js ]; then
  cat > assets/app.js <<'JS'
(function(){
  const y = document.getElementById('y');
  if (y) y.textContent = new Date().getFullYear();

  const empty = document.getElementById('empty');
  const ul = document.getElementById('post-list');

  async function loadPosts(){
    try{
      const r = await fetch('posts.json', {cache:'no-store'});
      if(!r.ok) throw new Error('posts.json missing');
      const posts = await r.json();
      if(!posts.length){ if (empty) empty.style.display='block'; return; }
      posts.sort((a,b)=> a.date < b.date ? 1 : -1);
      if (ul) {
        ul.innerHTML = posts.map(p =>
          `<li><a href="posts/${p.slug}.html">${p.title}</a><span class="date">${p.date}</span></li>`
        ).join('');
      }
    }catch(e){
      if (empty) empty.style.display='block';
      console.warn(e);
    }
  }
  loadPosts();
})();
JS
fi

if [ ! -f index.html ]; then
  cat > index.html <<'HTML'
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <title>Carnet des Réponses</title>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <link rel="stylesheet" href="assets/style.css"/>
  <script src="assets/app.js" defer></script>
</head>
<body>
  <header class="wrap">
    <h1>Carnet des Réponses</h1>
    <p class="sub">Des Q/R utiles, publiées simplement.</p>
  </header>
  <main class="wrap">
    <h2>Derniers billets</h2>
    <ul id="post-list" class="posts"></ul>
    <p id="empty" class="muted" style="display:none">Aucun billet pour l’instant.</p>
  </main>
  <footer class="wrap muted"><p>© <span id="y"></span> Carnet des Réponses</p></footer>
</body>
</html>
HTML
fi
