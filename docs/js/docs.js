// Active link highlighting in sidebar
const currentUrl = window.location.href.split('#')[0];
const sidebarLinks = document.querySelectorAll('.docs-sidebar a');

sidebarLinks.forEach(link => {
    if (link.href.split('#')[0] === currentUrl) {
        // Find the anchor target and highlight based on scroll position
        const anchorId = link.getAttribute('href').split('#')[1];
        if (anchorId) {
            const targetElement = document.getElementById(anchorId);
            if (targetElement) {
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            sidebarLinks.forEach(l => l.classList.remove('active'));
                            link.classList.add('active');
                        }
                    });
                }, { threshold: 0.5 });
                observer.observe(targetElement);
            }
        }
    }
});

// Auto-scrolling sidebar to active link
const activeLink = document.querySelector('.docs-sidebar a.active');
if (activeLink) {
    activeLink.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
    });
}

// Mobile sidebar toggle
const mobileSidebarToggle = document.createElement('button');
mobileSidebarToggle.innerHTML = '<i class="fas fa-bars"></i>';
mobileSidebarToggle.className = 'mobile-sidebar-toggle';
document.body.appendChild(mobileSidebarToggle);

const docsSidebar = document.querySelector('.docs-sidebar');
mobileSidebarToggle.addEventListener('click', () => {
    docsSidebar.classList.toggle('open');
});

// Add styles for mobile sidebar
const mobileSidebarStyles = `
    .mobile-sidebar-toggle {
        display: none;
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 50px;
        height: 50px;
        background: var(--primary-color);
        color: white;
        border: none;
        border-radius: 50%;
        font-size: 1.2rem;
        cursor: pointer;
        z-index: 1001;
        box-shadow: var(--shadow-lg);
    }

    @media (max-width: 1024px) {
        .mobile-sidebar-toggle {
            display: block;
        }

        .docs-sidebar {
            position: fixed;
            top: 0;
            left: -300px;
            width: 300px;
            height: 100vh;
            background: var(--dark-surface);
            z-index: 1000;
            transition: left 0.3s ease-in-out;
            padding: 2rem;
            border-right: 1px solid var(--dark-border);
        }

        .docs-sidebar.open {
            left: 0;
        }
    }
`;

const styleSheet = document.createElement("style");
styleSheet.innerText = mobileSidebarStyles;
document.head.appendChild(styleSheet);