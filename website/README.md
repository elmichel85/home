# Apex Locksmith & Auto Diagnostics — Website

A clean, professional, fully responsive static website for a locksmith and
car diagnostics business. No build step or dependencies — just static
HTML/CSS/JS.

## Structure

```
website/
├── index.html      # All page content/sections
├── css/styles.css  # Styling (navy/blue "clean & professional" theme)
└── js/script.js    # Mobile nav toggle, footer year, contact form handling
```

## Sections included

- Sticky top bar (24/7 badge + click-to-call phone number)
- Header/nav with mobile hamburger menu
- Hero with call-to-action buttons and key stats
- Services: Residential/Commercial Locksmith, Automotive Locksmith,
  Car Diagnostics, Emergency 24/7 Service
- "Why choose us" trust features
- About section with company stats
- Customer reviews
- Service area
- Contact section with a form and business details
- Footer + floating mobile "Call Now" button

## Customizing

All placeholder content — business name, phone number, email, address,
service area, and reviews — is in `index.html` and should be replaced with
real details. Search for:

- `(555) 123-4567` — phone number (appears in several places)
- `service@apexlocksmith.example` — email address
- `123 Main Street, Your City, ST 00000` — address
- `Apex Locksmith & Auto Diagnostics` — business name

Colors and fonts live at the top of `css/styles.css` under the `:root`
CSS variables (`--navy`, `--blue`, etc.) if you want to adjust the theme.

## The contact form

The form in the "Contact" section is client-side only right now — it
validates input and shows a confirmation message, but does not send
anywhere. To make it functional, wire it up in `js/script.js` to:

- A form backend like Formspree, Getform, or Netlify Forms, or
- Your own backend API endpoint

## Running locally

No build tools needed. Just open `index.html` in a browser, or serve the
folder locally, e.g.:

```bash
cd website
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Deploying

Since it's a static site, it can be hosted for free on GitHub Pages,
Netlify, Vercel, or Cloudflare Pages by pointing them at the `website/`
directory.
