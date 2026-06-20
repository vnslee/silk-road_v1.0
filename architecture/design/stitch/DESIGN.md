---
name: Kinetic Enterprise
colors:
  surface: '#fbf9f9'
  surface-dim: '#dbdad9'
  surface-bright: '#fbf9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#e9e8e7'
  surface-container-highest: '#e3e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#434751'
  inverse-surface: '#303031'
  inverse-on-surface: '#f2f0f0'
  outline: '#747782'
  outline-variant: '#c4c6d2'
  surface-tint: '#395da2'
  primary: '#00204e'
  on-primary: '#ffffff'
  primary-container: '#003478'
  on-primary-container: '#7d9fe9'
  inverse-primary: '#aec6ff'
  secondary: '#005db7'
  on-secondary: '#ffffff'
  secondary-container: '#599bfe'
  on-secondary-container: '#003268'
  tertiary: '#4d000a'
  on-tertiary: '#ffffff'
  tertiary-container: '#750015'
  on-tertiary-container: '#ff7576'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#aec6ff'
  on-primary-fixed: '#001a43'
  on-primary-fixed-variant: '#1c4489'
  secondary-fixed: '#d6e3ff'
  secondary-fixed-dim: '#a9c7ff'
  on-secondary-fixed: '#001b3d'
  on-secondary-fixed-variant: '#00468c'
  tertiary-fixed: '#ffdad8'
  tertiary-fixed-dim: '#ffb3b1'
  on-tertiary-fixed: '#410007'
  on-tertiary-fixed-variant: '#92001c'
  background: '#fbf9f9'
  on-background: '#1b1c1c'
  surface-variant: '#e3e2e2'
  surface-light: '#F8F9FA'
  surface-border: '#DCDCDC'
  text-primary: '#000000'
  text-secondary: '#555555'
  text-disabled: '#BEBEBE'
  accent-red: '#E63946'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Hanken Grotesk
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style

The design system is engineered for a premium financial environment that balances institutional stability with technological agility. It targets high-stakes corporate and personal finance users who demand precision and reliability. 

The aesthetic is **Corporate / Modern**, characterized by a rigorous information hierarchy, expansive use of whitespace, and a sophisticated color application. It avoids visual clutter, favoring a flat design language that uses subtle tonal layers and precise geometry to guide the user's focus through complex data-heavy interfaces. The emotional response is one of confidence, transparency, and architectural order.

## Colors

The palette is anchored by a deep Navy Primary (`#003478`), symbolizing authority and heritage. A secondary "Digital Blue" (`#2F79D9`) is utilized for interactive elements and highlights to ensure the interface feels modern rather than static. 

A vibrant Red is reserved exclusively for high-priority alerts, critical actions, and selective brand accents, ensuring its impact is not diluted. The background environment uses a high-contrast White and a Light Gray (`#F8F9FA`) to differentiate between the canvas and nested surface containers. Text is strictly tiered to ensure legibility, using deep blacks for headers and softened grays for metadata.

## Typography

This design system utilizes **Hanken Grotesk** for its exceptional clarity and professional weight distribution. The type scale is optimized for high-density data interfaces where legibility at small sizes is paramount. 

Headlines use a tighter letter-spacing and heavier weights to create a strong visual anchor. Body text is set with generous line heights to facilitate long-form reading of financial reports. Labels and captions utilize semi-bold weights and slight tracking to remain distinct even at 11px-12px.

## Layout & Spacing

The layout is built on a **12-column fluid grid** for desktop and a **4-column fluid grid** for mobile. A strict 4px base increment governs all spacing, ensuring rhythmic consistency across components.

- **Desktop:** 12 columns, 24px gutters, 48px side margins.
- **Tablet:** 8 columns, 24px gutters, 32px side margins.
- **Mobile:** 4 columns, 16px gutters, 16px side margins.

Horizontal spacing between related elements (like an icon and its label) should use `xs` (4px) or `sm` (8px), while vertical separation between distinct sections should use `xl` (32px) or higher.

## Elevation & Depth

Hierarchy is established through **Tonal Layering** supplemented by **Ambient Shadows**. 

1. **Level 0 (Base):** Pure white background for primary content areas.
2. **Level 1 (Surface):** Light gray (#F8F9FA) for secondary sidebars or navigation bars, often separated by a 1px border (#DCDCDC).
3. **Level 2 (Cards):** White surfaces with a soft, 12% opacity navy-tinted shadow (8px blur, 4px Y-offset).
4. **Level 3 (Popups/Modals):** High-elevation surfaces with a 16% opacity shadow (24px blur, 12px Y-offset) to indicate immediate interaction priority.

Backdrop blurs (8px - 12px) are used behind modals to maintain context while focusing the user on the task at hand.

## Shapes

The shape language reflects the system's "Kinetic" nature—precise but approachable. 

- **Standard Components:** Buttons and input fields use a consistent 8px radius.
- **Containment:** Standard cards and content modules use 8px.
- **Overlays:** Modals, popups, and dialogs use a more pronounced 12px radius to soften their impact on the interface.
- **Status Markers:** Small badges and tags are fully rounded (pill-shaped) to distinguish them from interactive buttons.

## Components

### Buttons
- **Primary:** Solid Primary Navy background with White text. 8px radius. Subtle scale-down effect (0.98) on click.
- **Outline:** 1px border using Primary Navy, transparent background. Text in Primary Navy.
- **Text:** No border or background. Primary Navy text. Used for secondary navigation or "Cancel" actions.

### Inputs
- Height: 48px for standard, 40px for dense.
- Style: 1px border (#DCDCDC) with 8px radius. Focus state uses a 2px Primary Navy border and a subtle blue outer glow.

### Badges & Status
- Small, uppercase label text.
- Use Semantic colors: Success (Green), Warning (Amber), Error (Red/Accent), Info (Secondary Blue). Backgrounds should be 10-15% opacity of the semantic color.

### Progress Bars
- 4px height for subtle tracking, 8px for major steps.
- Track: Light gray (#DCDCDC). 
- Indicator: Gradient from Primary Navy to Secondary Blue to indicate movement and advancement.

### Modals & Popups
- 12px corner radius.
- Centered on screen with a dark, semi-transparent backdrop (40% opacity Navy).
- Header includes a clear title in `headline-md` and a close icon in the top right.

### Cards
- White background, 1px border (#DCDCDC), and Level 2 shadow.
- Inner padding should follow the `lg` (24px) spacing token.