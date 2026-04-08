---
name: ui-ux-pro-max
description: AI skill that provides design intelligence for building professional UI/UX across multiple platforms. Includes 67 UI styles, 96 color palettes, 57 font pairings, 100 industry-specific reasoning rules, and intelligent design system generation.
license: MIT
---

# UI/UX Pro Max - Design Intelligence Skill

This skill provides comprehensive design intelligence for building professional UI/UX across multiple platforms and frameworks.

## What This Skill Provides

### Design System Generator

An AI-powered reasoning engine that analyzes your project requirements and generates a complete, tailored design system including:

- **Landing Page Patterns** - Conversion-optimized structures
- **UI Styles** - 67 curated styles (Glassmorphism, Neumorphism, Brutalism, etc.)
- **Color Palettes** - 96 industry-specific color schemes
- **Typography** - 57 professional font pairings with Google Fonts
- **Key Effects** - Animations and interactions
- **Anti-Patterns** - What to avoid for your industry

### Databases

- **67 UI Styles**: Glassmorphism, Claymorphism, Minimalism, Brutalism, Neumorphism, Bento Grid, Dark Mode, AI-Native UI, and more
- **96 Color Palettes**: Industry-specific palettes for SaaS, E-commerce, Healthcare, Fintech, Beauty, etc.
- **57 Font Pairings**: Curated typography combinations with Google Fonts imports
- **25 Chart Types**: Recommendations for dashboards and analytics
- **100 Reasoning Rules**: Industry-specific design system generation
- **13 Tech Stacks**: React, Next.js, Astro, Vue, Nuxt.js, SwiftUI, React Native, Flutter, HTML+Tailwind, shadcn/ui, Jetpack Compose

## How to Use

### Automatic Activation

The skill activates automatically when you request UI/UX work. Just chat naturally:

- "Build a landing page for my SaaS product"
- "Create a dashboard for healthcare analytics"
- "Design a portfolio website with dark mode"
- "Make a mobile app UI for e-commerce"
- "Build a fintech banking app with dark theme"

### Design System Generation

When you request UI/UX work, the skill will:

1. **Analyze your request** - Understand product type and requirements
2. **Search databases** - Find matching styles, colors, typography, and patterns
3. **Apply reasoning rules** - Match industry-specific best practices
4. **Generate complete design system** - Pattern + Style + Colors + Typography + Effects
5. **Provide anti-patterns** - What to avoid for your industry
6. **Include checklist** - Pre-delivery validation items

### Manual Search (Advanced)

You can directly search specific domains:

```bash
# Search for UI styles
python3 SKILLS/ui-ux-pro-max/scripts/search.py "glassmorphism" --domain style

# Search for color palettes
python3 SKILLS/ui-ux-pro-max/scripts/search.py "fintech dark" --domain color

# Search for typography
python3 SKILLS/ui-ux-pro-max/scripts/search.py "elegant serif" --domain typography

# Generate complete design system
python3 SKILLS/ui-ux-pro-max/scripts/search.py "beauty spa wellness" --design-system -p "Serenity Spa"
```

## Supported Tech Stacks

The skill provides stack-specific guidelines for:

| Category            | Stacks                    |
| ------------------- | ------------------------- |
| **Web (HTML)**      | HTML + Tailwind (default) |
| **React Ecosystem** | React, Next.js, shadcn/ui |
| **Vue Ecosystem**   | Vue, Nuxt.js, Nuxt UI     |
| **Other Web**       | Svelte, Astro             |
| **iOS**             | SwiftUI                   |
| **Android**         | Jetpack Compose           |
| **Cross-Platform**  | React Native, Flutter     |

Just mention your preferred stack in the prompt, or let it default to HTML + Tailwind.

## Industry-Specific Reasoning

The skill includes 100 specialized rules for industries including:

- **Tech & SaaS**: SaaS, Micro SaaS, B2B Enterprise, Developer Tools, AI/Chatbot Platform
- **Finance**: Fintech, Banking, Crypto, Insurance, Trading Dashboard
- **Healthcare**: Medical Clinic, Pharmacy, Dental, Veterinary, Mental Health
- **E-commerce**: General, Luxury, Marketplace, Subscription Box
- **Services**: Beauty/Spa, Restaurant, Hotel, Legal, Consulting
- **Creative**: Portfolio, Agency, Photography, Gaming, Music Streaming
- **Emerging Tech**: Web3/NFT, Spatial Computing, Quantum Computing, Autonomous Systems

Each rule includes:

- Recommended landing page pattern
- Style priority ranking
- Color mood matching
- Typography personality
- Key effects and animations
- Anti-patterns to avoid

## Pre-Delivery Checklist

Every design system includes validation items:

- [ ] No emojis as icons (use SVG: Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive breakpoints: 375px, 768px, 1024px, 1440px

## Examples

### Example 1: SaaS Landing Page

**Request**: "Build a landing page for my project management SaaS"

**Generated Design System**:

- Pattern: Hero-Centric + Feature Grid
- Style: Glassmorphism
- Colors: Blue gradient (#4F46E5 → #7C3AED)
- Typography: Inter + Space Grotesk
- Effects: Smooth transitions, subtle blur effects
- Anti-patterns: Avoid dark mode, avoid brutalism

### Example 2: Beauty Spa Website

**Request**: "Create a website for my luxury spa"

**Generated Design System**:

- Pattern: Hero-Centric + Social Proof
- Style: Soft UI Evolution
- Colors: Soft Pink (#E8B4B8) + Sage Green (#A8D5BA)
- Typography: Cormorant Garamond + Montserrat
- Effects: Soft shadows, gentle hover states
- Anti-patterns: Avoid bright neon, avoid harsh animations

### Example 3: Fintech Dashboard

**Request**: "Build a trading dashboard for crypto"

**Generated Design System**:

- Pattern: Dashboard Grid + Real-time Data
- Style: Dark Mode + Glassmorphism
- Colors: Dark background (#0F172A) + Accent (#10B981)
- Typography: JetBrains Mono + Inter
- Effects: Real-time updates, smooth chart animations
- Anti-patterns: Avoid AI purple/pink gradients, avoid light mode

## File Structure

```
SKILLS/ui-ux-pro-max/
├── SKILL.md                    # This file
├── data/
│   ├── styles.csv             # 67 UI styles database
│   ├── colors.csv             # 96 color palettes
│   ├── typography.csv         # 57 font pairings
│   ├── ui-reasoning.csv       # 100 industry rules
│   ├── landing.csv            # Landing page patterns
│   ├── charts.csv             # Chart recommendations
│   ├── icons.csv              # Icon library recommendations
│   ├── products.csv           # Product category mapping
│   ├── ux-guidelines.csv      # UX best practices
│   └── web-interface.csv      # Web interface patterns
├── scripts/
│   └── search.py              # Python search engine
└── templates/
    └── (platform-specific templates)
```

## Requirements

- **Python 3.x** - Required for the search script
- **Internet connection** - For Google Fonts links (optional)

## License

MIT License - See LICENSE file for details

## Credits

Created by nextlevelbuilder
Repository: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
