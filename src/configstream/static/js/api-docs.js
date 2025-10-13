(function () {
  'use strict';

  const FLAG = 'apiDocsNavInitialized';
  if (document.documentElement.dataset[FLAG]) {
    return;
  }
  document.documentElement.dataset[FLAG] = 'true';

  const ready = (fn) => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn, { once: true });
    } else {
      fn();
    }
  };

  ready(() => {
    const sections = Array.from(document.querySelectorAll('.doc-section[id]'));
    const navLinks = Array.from(document.querySelectorAll('.doc-nav-link[href^="#"]'));
    if (!sections.length || !navLinks.length) {
      return;
    }

    const cleanupTasks = [];
    let activeId = null;

    const setActive = (id) => {
      if (!id || id === activeId) {
        return;
      }
      activeId = id;
      navLinks.forEach((link) => {
        const match = link.hash.slice(1) === id;
        link.classList.toggle('active', match);
        link.setAttribute('aria-current', match ? 'true' : 'false');
      });
    };

    const prefersReducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const handleClick = (event) => {
      const href = event.currentTarget.getAttribute('href');
      if (!href || !href.startsWith('#')) {
        return;
      }
      const id = href.slice(1);
      if (!id) {
        return;
      }
      event.preventDefault();
      const target = document.getElementById(id);
      if (!target) {
        return;
      }
      target.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' });
      history.replaceState(null, '', `#${id}`);
      setActive(id);
    };

    navLinks.forEach((link) => link.addEventListener('click', handleClick, { passive: false }));
    cleanupTasks.push(() => navLinks.forEach((link) => link.removeEventListener('click', handleClick)));

    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          const id = entry.target.getAttribute('id');
          if (id) {
            setActive(id);
          }
        });
      }, { rootMargin: '-35% 0px -55% 0px', threshold: [0, 0.25, 0.5, 0.75, 1] });
      sections.forEach((section) => observer.observe(section));
      cleanupTasks.push(() => observer.disconnect());
    } else if (sections[0]) {
      setActive(sections[0].id);
    }

    const handleHashChange = () => {
      const id = window.location.hash.slice(1);
      if (id) {
        setActive(id);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    cleanupTasks.push(() => window.removeEventListener('hashchange', handleHashChange));

    const cleanup = () => {
      while (cleanupTasks.length) {
        const fn = cleanupTasks.pop();
        if (typeof fn === 'function') {
          fn();
        }
      }
    };

    window.addEventListener('beforeunload', cleanup, { once: true });
    window.addEventListener('pagehide', cleanup, { once: true });

    const initial = window.location.hash.slice(1);
    if (initial) {
      setActive(initial);
    } else if (sections[0]) {
      setActive(sections[0].id);
    }
  });
})();
