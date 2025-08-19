// assets/app.js
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
