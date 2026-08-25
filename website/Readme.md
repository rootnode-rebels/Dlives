# DLives — Marketing & Documentation Website

Official static marketing and documentation website for **DLives** — the dynamic floating island productivity app for Windows 10 & 11.

---

## 📁 Project Structure

```
website/
├── index.html                  # Main landing page (hero, features, requirements, CTA)
├── docs/
│   ├── getting-started.html   # Installation & first-run setup guide
│   ├── features.html          # In-depth breakdown of all 11 tabs & features
│   ├── faq.html               # Frequently asked questions & SmartScreen info
│   └── support.html           # Bug reporting & direct support contact (suhashoskere@gmail.com)
├── assets/
│   ├── app-icon.png           # DLives official logo icon
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



## 🔗 Official Direct Installer Download URL

All download buttons in the website link directly to download the `.exe` installer:
👉 [**Download Dlives_Setup.exe**](https://github.com/rootnode-rebels/Dlives/releases/download/v1.0.0/Dlives_Setup.exe)

---

## 📧 Support & Contact

- **Company / Publisher:** Fugentech
- **Support Email:** `suhashoskere@gmail.com`
- **Application Version:** 1.0
