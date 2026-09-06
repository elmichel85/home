// Apex Locksmith & Auto Diagnostics — site interactions

document.addEventListener('DOMContentLoaded', function () {
  // Mobile nav toggle
  var navToggle = document.getElementById('navToggle');
  var nav = document.getElementById('nav');

  if (navToggle && nav) {
    navToggle.addEventListener('click', function () {
      var isOpen = nav.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    // Close mobile nav after clicking a link
    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        nav.classList.remove('is-open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // Footer year
  var yearEl = document.getElementById('year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  // Contact form (client-side only — no backend wired up yet)
  var form = document.getElementById('contactForm');
  var status = document.getElementById('formStatus');

  if (form && status) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var name = form.name.value.trim();
      var phone = form.phone.value.trim();

      if (!name || !phone) {
        status.style.color = '#dc2626';
        status.textContent = 'Please fill in your name and phone number.';
        return;
      }

      // NOTE: This form has no backend yet. Wire it up to your email
      // service, form endpoint (e.g. Formspree), or backend API here.
      status.style.color = '#16a34a';
      status.textContent = 'Thanks, ' + name + '! We\'ll call you back at ' + phone + ' shortly.';
      form.reset();
    });
  }
});
