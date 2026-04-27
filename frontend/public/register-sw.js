// Force clear cache on version change
const APP_VERSION = '1.0.3'; // Increment this to force a full refresh

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    // Check if we need to force a refresh due to version change
    const savedVersion = localStorage.getItem('app_version');
    if (savedVersion !== APP_VERSION) {
      navigator.serviceWorker.getRegistrations().then(registrations => {
        for (let registration of registrations) {
          registration.unregister();
        }
        localStorage.setItem('app_version', APP_VERSION);
        // Clear caches too
        if ('caches' in window) {
          caches.keys().then(names => {
            for (let name of names) caches.delete(name);
          });
        }
        console.log('Cache cleared for new version:', APP_VERSION);
        window.location.reload();
      });
    } else {
      navigator.serviceWorker.register('/sw.js').then(reg => {
        // Check for updates periodically
        reg.update();
      });
    }
  });
}
