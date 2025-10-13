(function () {
  'use strict';

  const FLAG = 'docsNavInitialized';
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

    const setActiveLink = (id) => {
      if (!id || id === activeId) {
        return;
      }
      activeId = id;
      navLinks.forEach((link) => {
        const matches = link.hash.slice(1) === id;
        link.classList.toggle('active', matches);
        link.setAttribute('aria-current', matches ? 'true' : 'false');
      });
    };

    const scrollToSection = (targetId) => {
      const target = document.getElementById(targetId);
      if (!target) {
        return;
      }
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      target.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
      setActiveLink(targetId);
    };

    const handleClick = (event) => {
      const href = event.currentTarget.getAttribute('href');
      if (!href || !href.startsWith('#')) {
        return;
      }
      event.preventDefault();
      const targetId = href.slice(1);
      if (targetId) {
        scrollToSection(targetId);
        history.replaceState(null, '', `#${targetId}`);
      }
    };

    navLinks.forEach((link) => {
      link.addEventListener('click', handleClick, { passive: false });
    });
    cleanupTasks.push(() => navLinks.forEach((link) => link.removeEventListener('click', handleClick)));

    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          const id = entry.target.getAttribute('id');
          if (id) {
            setActiveLink(id);
          }
        });
      }, { rootMargin: '-40% 0px -55% 0px', threshold: [0, 0.25, 0.5, 0.75, 1] });
      sections.forEach((section) => observer.observe(section));
      cleanupTasks.push(() => observer.disconnect());
    } else {
      setActiveLink(sections[0].id);
    }

    const handleHashChange = () => {
      const id = window.location.hash.slice(1);
      if (id) {
        setActiveLink(id);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    cleanupTasks.push(() => window.removeEventListener('hashchange', handleHashChange));

    const cleanup = () => {
      while (cleanupTasks.length) {
        try {
          const task = cleanupTasks.pop();
          if (task) {
            task();
          }
        } catch (err) {
          console.error('docs cleanup failed', err);
        }
      }
    };

    window.addEventListener('beforeunload', cleanup, { once: true });
    window.addEventListener('pagehide', cleanup, { once: true });

    const initialId = window.location.hash.slice(1);
    if (initialId) {
      setActiveLink(initialId);
    } else {
      const first = sections[0];
      if (first) {
        setActiveLink(first.id);
      }
    }
  });
})();
