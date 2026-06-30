const C='niosh-cbmsc-d7d30cd7f5';
const ASSETS=['icon-192.png','icon-512.png','manifest.json'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(ASSETS)).catch(()=>{})); self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
function isHTML(r){return r.mode==='navigate' || (r.headers.get('accept')||'').includes('text/html') || /\.html($|\?)/.test(r.url);}
self.addEventListener('fetch',e=>{
  const r=e.request; if(r.method!=='GET' || !r.url.startsWith(self.location.origin)) return;
  if(isHTML(r)){
    // network-first: sempre tenta a versão mais nova; cai pro cache só offline
    e.respondWith(fetch(r).then(resp=>{const cp=resp.clone(); caches.open(C).then(c=>c.put(r,cp)); return resp;})
      .catch(()=>caches.match(r).then(h=>h||caches.match('livro.html')||caches.match('index.html'))));
  } else {
    // estáticos (ícones, pdf): cache-first com atualização em segundo plano
    e.respondWith(caches.match(r).then(hit=>hit || fetch(r).then(resp=>{const cp=resp.clone(); caches.open(C).then(c=>c.put(r,cp)); return resp;})));
  }
});
self.addEventListener('message',e=>{ if(e.data==='skipWaiting') self.skipWaiting(); });
