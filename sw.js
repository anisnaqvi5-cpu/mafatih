/* مفاتیح PWA — service worker
   کیش کا نام ورژن کے ساتھ بدلیں تاکہ update صارف تک پہنچے */
const CACHE = 'mafatih-v10';

const SHELL = [
  './',
  './index.html',
  './manifest.json',
  './data/index.json',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

// install: shell کو کیش میں ڈالو
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

// activate: پرانے کیش صاف کرو
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// fetch: پہلے کیش، پھر network (اور جو نیا ملے اسے کیش کر لو)
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(hit => {
      if (hit) return hit;
      return fetch(e.request).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
        return res;
      }).catch(() => caches.match('./index.html'));
    })
  );
});

// audio download: صفحے سے پیغام آنے پر مخصوص فائل کیش کرو
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'CACHE_AUDIO' && e.data.url) {
    caches.open(CACHE).then(c => c.add(e.data.url)).catch(() => {});
  }
});
