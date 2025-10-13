document.addEventListener('DOMContentLoaded', function() {
    const sections = Array.from(document.querySelectorAll('.doc-section')).filter(s => s.id);
    const navLinks = document.querySelectorAll('.doc-nav-link');

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            const id = entry.target.getAttribute('id');
            if (!id) return;
            const navLink = document.querySelector(`.doc-nav-link[href="#${id}"]`);
            if (navLink && entry.isIntersecting) {
                navLinks.forEach(link => link.classList.remove('active'));
                navLink.classList.add('active');
            }
        });
    }, { rootMargin: "-20% 0px -80% 0px", threshold: 0 });

    sections.forEach(section => observer.observe(section));

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (!targetId) return;
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                navLinks.forEach(l => l.classList.remove('active'));
                this.classList.add('active');
                targetElement.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    window.addEventListener('beforeunload', () => {
        observer.disconnect();
    });
});