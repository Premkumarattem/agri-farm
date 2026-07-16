document.addEventListener('click', (e) => {
  const nav = document.querySelector('.main-nav');
  const toggle = document.querySelector('.nav-toggle');
  if (!nav || !toggle) return;
  if (nav.classList.contains('open') && !nav.contains(e.target) && !toggle.contains(e.target)) {
    nav.classList.remove('open');
  }
});
