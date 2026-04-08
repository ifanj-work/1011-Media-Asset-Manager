---
name: brand-guidelines
description: Applies 1011 (Sepuluh Sebelas Group) brand colors, typography, and design language to any artifact. Use when brand consistency is needed across the 1011 Media Asset Manager UI.
license: Complete terms in LICENSE.txt
---

# 1011 (Sepuluh Sebelas Group) Brand Styling — v2

## Overview

Official brand identity for 1011 PC / Sepuluh Sebelas Group, derived from the official `Logo 1011.svg` and cross-referenced with https://www.1011.id/. This design system is adapted for the **1011 Media Asset Manager** — a professional dark-mode DAM tool used by the creative team.

**Keywords**: branding, corporate identity, visual identity, styling, brand colors, typography, 1011, Sepuluh Sebelas, DAM, media asset manager

## Logo

- **File**: `Image/Logo 1011.svg` (57KB SVG)
- **Shape**: Square with rounded corners (~37px radius at original scale)
- **Border**: Pastel rainbow gradient frame (pink → green → cyan → purple)
- **Inner icon**: Charcoal `#212121` bars on white `#FFFFFF` — forming stylized "1011" (one bar + three bars)
- **App Title**: "1011 Media Asset Manager" — Use Poppins SemiBold, white on dark backgrounds

> **Design rule**: The UI chrome uses neutral (zinc) grays derived from the logo's `#212121` charcoal. The cyan accent echoes the logo's gradient. This ensures the logo always feels "at home" in the interface.

## Brand Guidelines

### Colors

**Logo-Derived Core:**

- Charcoal (Logo Dark): `#212121` → modernized to `#18181B` (zinc-900)
- White (Logo Light): `#FFFFFF`
- Cyan (Logo Gradient Accent): `#06B6D4` (cyan-500)
- Pink (Logo Gradient): `#EC4899` — used sparingly as a decorative accent
- Purple (Logo Gradient): `#A855F7` — used sparingly as a decorative accent

**Dark Mode Application Palette (Zinc-based, neutral):**

| Token | Hex | Zinc | Use | Contrast on zinc-950 |
|---|---|---|---|---|
| `--bg-primary` | `#09090B` | zinc-950 | Main app background | — |
| `--bg-surface` | `#18181B` | zinc-900 | Cards, panels, sidebar | — |
| `--bg-elevated` | `#27272A` | zinc-800 | Modals, dropdowns, hover states | — |
| `--bg-hover` | `#3F3F46` | zinc-700 | Hover highlight | — |
| `--text-primary` | `#FAFAFA` | zinc-50 | Headings, primary content | 19.5:1 ✅ |
| `--text-secondary` | `#A1A1AA` | zinc-400 | Secondary text, captions | 5.07:1 ✅ |
| `--text-tertiary` | `#71717A` | zinc-500 | Timestamps, metadata labels | 4.54:1 ✅ |
| `--border-default` | `#27272A` | zinc-800 | Default borders | — |
| `--border-subtle` | `#3F3F46` | zinc-700 | Active/secondary borders | — |
| `--border-active` | `#06B6D4` | cyan-500 | Active selection, focus ring | — |

> **Why Zinc (neutral) over Slate (blue-tinted)?** Photography/media tools (Adobe Lightroom, Figma, DaVinci Resolve) use neutral grays because blue-tinted backgrounds shift color perception and make thumbnails appear inaccurately warm. Since media assets are the hero content, the UI chrome must be color-neutral.

**Accent & Interactive:**

| Token | Hex | Use |
|---|---|---|
| `--color-accent` | `#06B6D4` (cyan-500) | Primary accent, active states, links |
| `--color-accent-hover` | `#0891B2` (cyan-600) | Accent hover state |
| `--color-accent-subtle` | `rgba(6, 182, 212, 0.1)` | Accent backgrounds (selected items) |

**Semantic:**

| Token | Hex | Use |
|---|---|---|
| `--color-success` | `#22C55E` (green-500) | Import complete, tag applied, scan done |
| `--color-warning` | `#F59E0B` (amber-500) | NAS disconnected, scan warning |
| `--color-error` | `#EF4444` (red-500) | Failed operation, missing files |
| `--color-info` | `#3B82F6` (blue-500) | Info notices, result counts |

**Tag Category Colors:**

| Category | Hex | Tailwind | Visual |
|---|---|---|---|
| Event | `#6366F1` | indigo-500 | 🟣 |
| Team | `#EC4899` | pink-500 | 🩷 |
| Player | `#8B5CF6` | violet-500 | 💜 |
| League | `#F59E0B` | amber-500 | 🟡 |
| Year | `#0EA5E9` | sky-500 | 🔵 |
| Custom | `#71717A` | zinc-500 | ⚪ |

### Typography

**Font Pairing: Poppins (headings) + Inter (body)**

- **Headings**: Poppins SemiBold (600) / Bold (700) — brand recognition from 1011.id
- **Body/UI**: Inter Regular (400) / Medium (500) — optimized for screens, tabular numbers, better at 12-14px for metadata-dense views
- **Monospace**: JetBrains Mono Regular (400) — for file paths, EXIF values, technical info
- **Fallback**: system-ui, -apple-system, sans-serif

**Google Fonts Import (optimized — only needed weights):**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Poppins:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
```

**Type Scale:**

| Level | Font | Size | Weight | Line Height | Use |
|---|---|---|---|---|---|
| H1 | Poppins | 28px | 700 | 1.2 | Page titles |
| H2 | Poppins | 22px | 600 | 1.3 | Section headers |
| H3 | Poppins | 18px | 600 | 1.3 | Card titles, modal headers |
| Body | Inter | 14px | 400 | 1.5 | Default body text |
| Body (medium) | Inter | 14px | 500 | 1.5 | Emphasized body, nav labels |
| Small | Inter | 12px | 400 | 1.5 | Captions, metadata, timestamps |
| Mono | JetBrains Mono | 13px | 400 | 1.4 | File paths, EXIF data |
| Tag | Inter | 12px | 500 | 1 | Tag pills |

### Shape & Spacing

**Border Radius:**

| Element | Radius | Notes |
|---|---|---|
| Buttons, Inputs | `8px` | Consistent interactive elements |
| Cards, Thumbnails | `12px` | Slightly rounder for modern feel |
| Panels, Sidebar | `0px` | Flush edges (like Figma/VS Code) |
| Modals, Popovers | `16px` | Clear elevation separation |
| Tag chips | `999px` (pill) | Tags are the one place pills work |
| Filter chips | `999px` (pill) | Same as tags — compact identifiers |

**Spacing Scale (4px base):**
`4, 8, 12, 16, 20, 24, 32, 48, 64`

**Layout Constants:**

| Element | Value |
|---|---|
| Sidebar (expanded) | 260px |
| Sidebar (collapsed) | 64px |
| Header height | 56px |
| Grid gap (assets) | 16px |
| Grid gap (dense tables) | 12px |
| Card padding (text area) | 12px |
| Modal padding | 24px |
| Table row height (min) | 44px (touch target) |

### Button Styles

**Primary Button:**
```css
.btn-primary {
  background: var(--color-accent);       /* #06B6D4 */
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-family: var(--font-body);         /* Inter */
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
  transition: filter 150ms ease, transform 150ms ease;
}
.btn-primary:hover {
  filter: brightness(1.15);
}
.btn-primary:active {
  transform: scale(0.97);
}
.btn-primary:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

**Secondary Button (outline):**
```css
.btn-secondary {
  background: transparent;
  color: var(--color-accent);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 10px 20px;
  font-weight: 500;
  cursor: pointer;
  transition: background 150ms ease, border-color 150ms ease;
}
.btn-secondary:hover {
  background: var(--color-accent-subtle);
  border-color: var(--color-accent);
}
```

**Ghost Button:**
```css
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: color 150ms ease, background 150ms ease;
}
.btn-ghost:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}
```

### Elevation & Shadows

| Level | Shadow | Use |
|---|---|---|
| 0 | none | Flat elements |
| 1 | `0 1px 3px rgba(0,0,0,0.3)` | Cards at rest |
| 2 | `0 4px 12px rgba(0,0,0,0.4)` | Hovered cards, dropdowns |
| 3 | `0 8px 24px rgba(0,0,0,0.5)` | Modals, overlays |
| 4 | `0 16px 48px rgba(0,0,0,0.6)` | Lightbox |

### Animations & Transitions

**Timing:**

| Duration | Value | Use |
|---|---|---|
| Fast | `150ms` | Hover states, color changes, button press |
| Normal | `200ms` | Panel reveal, tab switch, modal open |
| Slow | `300ms` | Sidebar expand, complex transitions |

**Easing:**

| Type | Value | Use |
|---|---|---|
| Standard | `cubic-bezier(0.4, 0, 0.2, 1)` | General UI motion |
| Enter | `cubic-bezier(0, 0, 0.2, 1)` | Elements appearing (ease-out) |
| Exit | `cubic-bezier(0.4, 0, 1, 1)` | Elements disappearing (ease-in) |

**Key Animations:**

| Element | Animation | Duration | Notes |
|---|---|---|---|
| Card hover | `translateY(-2px)` + shadow + bg | 200ms | Three-signal hover |
| Modal open | Scale 0.95→1 + fade in | 200ms ease-out | |
| Modal close | Scale 1→0.95 + fade out | 150ms ease-in | Exits faster than entries |
| Tag add | Pill scales 0→1 | 150ms spring | Micro-feedback |
| Toast | Slide from right + auto-dismiss | 200ms + 4s display | |
| Selection | `box-shadow: 0 0 0 2px var(--color-accent)` | 150ms | Cyan glow ring |
| Skeleton | Pulse opacity 0.5→1→0.5 | 1.5s infinite | Loading indicator |

**Accessibility**: All animations respect `prefers-reduced-motion: reduce`. When reduced motion is preferred, all transitions become instant (0ms duration).

### Interaction States

**Selection States:**
- Single select: Cyan border ring (`box-shadow: 0 0 0 2px var(--color-accent)`)
- Multi-select: Same ring + checkmark badge top-right
- Range select: Shift+Click highlights range with accent background

**Focus States (CRITICAL — never remove without replacement):**
```css
*:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

**Disabled States:**
```css
[disabled], .disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}
```

### Loading States

**Skeleton screen pattern** (for grid, table, detail panel):
- Background: `var(--bg-surface)`
- Pulse color: `var(--bg-elevated)`
- Animation: 1.5s infinite pulse
- Border radius: Match the element being loaded

**Loading button:**
```css
.btn-loading {
  position: relative;
  color: transparent;
  pointer-events: none;
}
.btn-loading::after {
  content: "";
  position: absolute;
  width: 16px; height: 16px;
  border: 2px solid var(--text-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 600ms linear infinite;
}
```

### Empty States

Pattern for all pages (no results, empty collection, no tags):
- Icon or illustration (Lucide icon, 48px, `--text-tertiary`)
- Heading: "No [items] found" (H3, `--text-secondary`)
- Description: helpful suggestion (Body, `--text-tertiary`)
- Primary action CTA button

### Icons

- **Library**: Lucide Icons (https://lucide.dev)
- **Size**: 20px default, 16px in tight spaces, 24px for nav items
- **Stroke width**: 1.5px (Lucide default)
- **Color**: `currentColor` — inherits from parent text color
- **Rule**: No emojis as functional icons. SVG only.

### Design Vibe

**Professional, Content-Forward, and Neutral.**

The design philosophy is "invisible UI" — the interface recedes so media assets are the hero. Neutral zinc backgrounds ensure accurate color perception for photography and video thumbnails.

Key principles:
1. **Content-forward** — Thumbnails and media are the hero; UI chrome is neutral and quiet
2. **Color-neutral** — Zinc grays prevent color perception bias on media assets
3. **Information-dense but clean** — Show metadata without clutter; Inter font maximizes readability
4. **Responsive interactions** — Hover states, smooth transitions, keyboard-first support
5. **Brand-aligned** — Charcoal + cyan palette echoes the 1011 logo's dark bars and gradient accent
6. **Accessible** — WCAG AA minimum on all text, visible focus states, reduced motion support
