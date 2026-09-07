# Dlives — Marketing & Documentation Website

Official static marketing and documentation website for **Dlives** — the dynamic floating island productivity app for Windows 10 & 11.

---

## 📁 Project Structure

```
website/
├── index.html                  # Main landing page (hero, features, requirements, CTA)
├── docs/
│   ├── getting-started.html   # Installation & first-run setup guide
│   ├── features.html          # In-depth breakdown of all 11 tabs & features
│   ├── faq.html               # Frequently asked questions & SmartScreen info
│   ├── privacy.html           # 100% offline Privacy Policy
│   └── support.html           # Bug reporting & direct support contact (suhashoskere@gmail.com)
├── assets/
│   ├── app-icon.png           # Dlives official logo icon
│   ├── css/
│   │   ├── style.css          # Core Liquid Glass / dark glassmorphism stylesheet
│   │   └── docs.css           # Documentation layout & components
│   ├── js/
│   │   └── main.js            # Navbar, mobile drawer, scroll reveals, clock & accordion
│   └── screenshots/           # High-resolution real app screenshots
│       ├── home-tab.png
│       ├── control-media.png
│       ├── system-diagnostics.png
│       ├── clipboard-shelf.png
│       ├── calendar.png
│       ├── alarms.png
│       ├── app-launcher.png
│       ├── notes.png
│       ├── settings.png
│       ├── notifications.png
│       └── app-interface-configurator.png
├── PROJECT_INFO.md             # Complete marketing copy, features manifest & specs
└── README.md                   # Deployment & hosting guide
```

---

## ⚡ Running Locally

Because this is a pure static site (zero build steps, zero npm dependencies), you can run it with any local HTTP server:

### Option 1: Python HTTP Server (Built-in)
```bash
python -m http.server 8000 --directory "d:\projects\dlives\website"
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

### Option 2: Node `npx -y serve`
```bash
npx -y serve "d:\projects\dlives\website"
```

### Option 3: VS Code Live Server Extension
Right-click `website/index.html` → **"Open with Live Server"**.

---

## 🚀 Deployment Instructions

This website has zero server requirements and can be deployed instantly to any static host:

### 1. Vercel
1. Install Vercel CLI: `npm i -g vercel`
2. Run from the `website` directory:
   ```bash
   cd website
   vercel --prod
   ```
3. Or link your GitHub repository on [vercel.com](https://vercel.com) and set the **Root Directory** to `website`.

### 2. Netlify
- **Drag & Drop:** Drag the `website/` folder directly into [app.netlify.com/drop](https://app.netlify.com/drop).
- **Git:** Link your repo on Netlify and set the **Publish directory** to `website`.

### 3. GitHub Pages
- If hosting from the root repository, configure GitHub Pages in **Settings → Pages** to serve from the `/docs` or `/root` branch, or use a GitHub Action to deploy the `website/` folder to the `gh-pages` branch.

---

## 🔗 Official Direct Installer Download URL

All download buttons in the website link directly to download the `.exe` installer:
👉 [**Download Dlives_Setup.exe**](https://github.com/rootnode-rebels/Dlives/releases/download/v1.0.0/Dlives_Setup.exe)

---

## 📄 License

This project is licensed under the MIT License — see the root [LICENSE](../LICENSE) for details.

---

## 📧 Support & Contact

- **Company / Publisher:** Fugentech
- **Support Email:** `suhashoskere@gmail.com`
- **Application Version:** 1.0
