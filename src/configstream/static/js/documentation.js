document.addEventListener('DOMContentLoaded', function() {
    const sections = document.querySelectorAll('.doc-section');
    const navLinks = document.querySelectorAll('.doc-nav-link');

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            const id = entry.target.getAttribute('id');
            const navLink = document.querySelector(`.doc-nav-link[href="#${id}"]`);
            if (navLink) {
                if (entry.isIntersecting) {
                    navLinks.forEach(link => link.classList.remove('active'));
                    navLink.classList.add('active');
                }
            }
        });
    }, { rootMargin: "-20% 0px -80% 0px", threshold: 0 });

    sections.forEach(section => observer.observe(section));

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
});