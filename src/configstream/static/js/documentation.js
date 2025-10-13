document.addEventListener('DOMContentLoaded', function() {
    // Prevent double-initialization if both scripts are included
    if (!window.__docsNavInitialized__) {
        window.__docsNavInitialized__ = true;

        const sections = document.querySelectorAll('.doc-section');
        const navLinks = document.querySelectorAll('.doc-nav-link');

        let observer = null;
        const activateLink = (id) => {
            navLinks.forEach(link => link.classList.remove('active'));
            const navLink = document.querySelector(`.doc-nav-link[href="#${id}"]`);
            if (navLink) navLink.classList.add('active');
        };

        if ('IntersectionObserver' in window) {
            observer = new IntersectionObserver(entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const id = entry.target.getAttribute('id');
                        if (id) activateLink(id);
                    }
                });
            }, { rootMargin: "-20% 0px -80% 0px", threshold: 0 });

            sections.forEach(section => observer.observe(section));
            window.addEventListener('pagehide', () => observer && observer.disconnect(), { once: true });
            window.addEventListener('beforeunload', () => observer && observer.disconnect(), { once: true });
        } else {
            const first = sections[0]?.getAttribute('id');
            if (first) activateLink(first);
        }

        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    targetElement.scrollIntoView({ behavior: 'smooth' });
                    const id = targetElement.getAttribute('id');
                    if (id) activateLink(id);
                }
            }, { passive: false });
        });
    }
});