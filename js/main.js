/* ==========================================================================
   TzakGPT — Main JavaScript
   Smooth scrolling, nav highlight, mobile menu, animated reveals.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ---- DOM refs ------------------------------------------------------- */
    var nav = document.querySelector('.nav');
    var navToggle = document.querySelector('.nav-toggle');
    var navLinksAll = document.querySelectorAll('.nav-links a');

    /* ---- Mobile menu toggle --------------------------------------------- */
    function openNav() {
        nav.classList.add('open');
        navToggle.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
    }

    function closeNav() {
        nav.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    }

    navToggle.addEventListener('click', function () {
        if (nav.classList.contains('open')) {
            closeNav();
        } else {
            openNav();
        }
    });

    /* Close mobile menu when a nav link is clicked */
    navLinksAll.forEach(function (link) {
        link.addEventListener('click', function () {
            closeNav();
        });
    });

    /* Close mobile menu when tapping the backdrop (dimmed area) */
    document.addEventListener('click', function (e) {
        if (!nav.classList.contains('open')) return;
        // If click is on the nav-links panel itself but NOT on a link/button,
        // and also not on the toggle, treat as backdrop tap
        var clickedInsidePanel = nav.querySelector('.nav-links').contains(e.target);
        var clickedToggle = navToggle.contains(e.target);
        if (!clickedInsidePanel && !clickedToggle) {
            closeNav();
        }
    });

    /* ---- Smooth scroll for anchor links --------------------------------- */
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                var navHeight = nav.offsetHeight;
                var targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight - 16;
                window.scrollTo({ top: targetPosition, behavior: 'smooth' });
                history.pushState(null, null, this.getAttribute('href'));
            }
        });
    });

    /* ---- Scroll-aware navigation highlight + shadow --------------------- */
    var sections = document.querySelectorAll('.section[id]');
    var navSectionLinks = document.querySelectorAll('.nav-links a[href^="#"]');

    function updateNavHighlight() {
        var scrollY = window.pageYOffset || document.documentElement.scrollTop;

        /* Nav shadow when scrolled */
        if (scrollY > 10) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }

        var current = '';
        sections.forEach(function (section) {
            var sectionTop = section.offsetTop - 140;
            if (scrollY >= sectionTop) {
                current = section.getAttribute('id');
            }
        });

        navSectionLinks.forEach(function (link) {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#' + current) {
                link.classList.add('active');
            }
        });
    }

    window.addEventListener('scroll', updateNavHighlight, { passive: true });
    updateNavHighlight();

    /* ---- Table scroll shadow — add class when table overflows ----------- */
    var tableWrappers = document.querySelectorAll('.table-wrapper');

    function updateTableShadows() {
        tableWrappers.forEach(function (wrapper) {
            var hasOverflow = wrapper.scrollWidth > wrapper.clientWidth + 2;
            var isScrolledToEnd = wrapper.scrollLeft + wrapper.clientWidth >= wrapper.scrollWidth - 2;
            if (hasOverflow && !isScrolledToEnd) {
                wrapper.classList.add('has-scroll-right');
            } else {
                wrapper.classList.remove('has-scroll-right');
            }
            if (hasOverflow && wrapper.scrollLeft > 2) {
                wrapper.classList.add('has-scroll-left');
            } else {
                wrapper.classList.remove('has-scroll-left');
            }
        });
    }

    tableWrappers.forEach(function (wrapper) {
        wrapper.addEventListener('scroll', updateTableShadows, { passive: true });
    });

    window.addEventListener('resize', updateTableShadows, { passive: true });
    updateTableShadows();

    /* ---- Animated stat counters ----------------------------------------- */
    function animateCounters() {
        var counters = document.querySelectorAll('.stat-value');
        counters.forEach(function (counter) {
            if (counter.dataset.animated) return;
            counter.dataset.animated = 'true';

            var target = parseInt(counter.textContent, 10);
            if (isNaN(target)) return;

            var start = 0;
            var duration = 1400;  // ms
            var startTime = null;

            function step(timestamp) {
                if (!startTime) startTime = timestamp;
                var elapsed = timestamp - startTime;
                var progress = Math.min(elapsed / duration, 1.0);
                /* Ease-out cubic */
                var eased = 1 - Math.pow(1 - progress, 3);
                var current = Math.round(start + (target - start) * eased);
                counter.textContent = current;
                if (progress < 1) {
                    requestAnimationFrame(step);
                } else {
                    counter.textContent = target;
                }
            }

            requestAnimationFrame(step);
        });
    }

    /* ---- Intersection Observer for reveals + counters ------------------- */
    var observerOptions = { threshold: 0.12, rootMargin: '0px 0px -30px 0px' };

    var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry, index) {
            if (entry.isIntersecting) {
                /* Stagger: delay each card within the same batch */
                var delay = Array.from(entry.target.parentNode.children)
                    .indexOf(entry.target) * 60;
                entry.target.style.transitionDelay = delay + 'ms';
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                revealObserver.unobserve(entry.target);

                /* If this entry contains stat counters, animate them */
                if (entry.target.classList.contains('stat-item')) {
                    animateCounters();
                }
                /* If this is the stats-bar itself, also animate */
                if (entry.target.classList.contains('stats-bar')) {
                    animateCounters();
                }
            }
        });
    }, observerOptions);

    document.querySelectorAll(
        '.feature-card, .arch-block, .command-item, .step-list li, .stat-item, .stats-bar'
    ).forEach(function (el) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(24px)';
        el.style.transition = 'opacity 0.55s ease, transform 0.55s ease';
        el.style.transitionDelay = '0ms';
        revealObserver.observe(el);
    });

    /* ---- h2 accent-bar reveal on scroll -------------------------------- */
    var headingObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                headingObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('h2').forEach(function (h2) {
        headingObserver.observe(h2);
    });

    /* ---- Copy-to-clipboard for code blocks ----------------------------- */
    document.querySelectorAll('.code-block').forEach(function (block) {
        block.style.cursor = 'pointer';
        block.title = 'Click to select all';
        block.addEventListener('click', function () {
            var range = document.createRange();
            range.selectNodeContents(block);
            var sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        });
    });

});
