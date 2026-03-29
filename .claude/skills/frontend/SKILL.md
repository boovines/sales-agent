---
name: frontend
description: "Create distinctive, bespoke frontend interfaces using project-specific design specifications. Use when building UI components, pages, or applications. Prevents generic AI aesthetics by loading design tokens from frontend.json and applying the project's unique visual vibe."
---

# Bespoke Frontend Design Skill

## 🎨 Design Philosophy & Vibe

**VIBE_SUMMARY_PLACEHOLDER**

This vibe should permeate every component, interaction, and visual detail. The design is not generic—it's intentionally crafted to embody this specific aesthetic.

---

## CRITICAL: Load Design Specifications FIRST

**Before generating ANY frontend code, you MUST:**

### Step 1: Load frontend.json
```bash
cat .claude/skills/frontend/frontend.json
```

This file contains:
- Exact color palette (hex values)
- Typography specifications (fonts, sizes, weights)
- Spacing system
- Border radius values
- Shadow definitions
- Animation timings and easings
- Component-specific design tokens

### Step 2: Parse and Internalize
Extract these specifications and **commit them to memory** for this session:
- Primary, secondary, accent colors
- Background and surface colors
- Font families for headings, body, and code
- Spacing scale array
- Border radius sizes
- Animation durations
- Component patterns

### Step 3: Apply Religiously
**EVERY** component, style, and design decision must reference these specifications. NO exceptions.

---

## ❌ ANTI-PATTERNS: Never Use These Generic Defaults

**Forbidden Font Families:**
- Inter, Roboto, Arial, Helvetica, system-ui (unless explicitly in your frontend.json)
- Default sans-serif stacks
- Generic system fonts

**Forbidden Color Schemes:**
- Purple-to-blue gradients (#7C3AED to #3B82F6)
- Generic Tailwind defaults (blue-500, purple-600) without customization
- White backgrounds with blue accents (unless that's YOUR spec)
- Any color not explicitly defined in frontend.json

**Forbidden Layout Patterns:**
- Cookie-cutter card layouts
- Predictable navigation bars
- Generic hero sections
- Layouts that look like every other AI-generated site

**Forbidden Animations:**
- No animations when the spec calls for them
- Generic fade-ins without personality
- Robotic, linear transitions

---

## ✅ REQUIRED: Implementation Process

### Phase 1: Parse Design Tokens (MANDATORY)

After loading frontend.json, extract:

```typescript
// Example of what you should mentally construct:
const designTokens = {
  colors: {
    primary: "[value from JSON]",
    secondary: "[value from JSON]",
    accent: "[value from JSON]",
    // ... all colors from JSON
  },
  typography: {
    heading: "[value from JSON]",
    body: "[value from JSON]",
    // ... all fonts from JSON
  },
  spacing: [/* array from JSON */],
  // ... etc
};
```

### Phase 2: Generate Code Using ONLY These Specs

**For React with Tailwind:**

```tsx
// Example button using loaded specs
<button 
  className="
    bg-[{PRIMARY_COLOR}] hover:bg-[{PRIMARY_HOVER}]
    font-[{BUTTON_FONT}] font-[{BUTTON_WEIGHT}]
    px-[{BUTTON_PADDING_X}] py-[{BUTTON_PADDING_Y}]
    rounded-[{BUTTON_RADIUS}]
    shadow-[{BUTTON_SHADOW}]
    transition-all duration-[{ANIMATION_NORMAL}] ease-[{EASING}]
    hover:scale-105 hover:shadow-[{BUTTON_SHADOW_HOVER}]
  "
>
  {children}
</button>
```

**Replace placeholders with actual values from frontend.json**

**For CSS Variables Approach:**

```tsx
// 1. First, generate a CSS variables file from the JSON:
// styles/design-tokens.css
:root {
  --color-primary: {PRIMARY_FROM_JSON};
  --color-secondary: {SECONDARY_FROM_JSON};
  --font-heading: {HEADING_FONT_FROM_JSON};
  --spacing-base: {BASE_SPACING_FROM_JSON};
  /* ... all tokens */
}

// 2. Then use in components:
<button className="btn-primary">
  {children}
</button>

// 3. With corresponding CSS:
.btn-primary {
  background-color: var(--color-primary);
  font-family: var(--font-heading);
  padding: var(--spacing-4) var(--spacing-6);
  border-radius: var(--radius-medium);
}
```

### Phase 3: Vibe Alignment Check

Before completing ANY component, verify it embodies the vibe:

**Ask yourself:**
1. Does this feel like **VIBE_SUMMARY_PLACEHOLDER**?
2. Would someone look at this and immediately sense the intended aesthetic?
3. Does every detail (colors, fonts, spacing, animations) reinforce the vibe?
4. Is there anything generic or "AI-looking" that breaks the vibe?

If any answer is "no" or "unsure" → revise.

### Phase 4: Technical Verification

**Required checks before completion:**

```bash
# Check 1: No forbidden fonts
grep -r "font-inter\|font-sans\|Inter\|Roboto\|Arial" src/
# Should return EMPTY (unless these are in your JSON)

# Check 2: All colors from JSON
# Manually verify: every bg-, text-, border- color matches frontend.json

# Check 3: Spacing follows scale
# Verify: all padding/margin values exist in the spacing array

# Check 4: Animations use specified timings
# Verify: duration-[X] values match frontend.json animations
```

---

## 📋 Component Generation Workflow

When asked to create a component:

### 1. **Read the JSON**
```bash
cat .claude/skills/frontend/frontend.json
```

### 2. **Identify Relevant Tokens**
For a Button component, extract:
- `colors.primary` and `colors.primaryHover`
- `components.button.*` (if defined)
- `typography.buttonFont` or fallback to `typography.headingFont`
- `spacing.buttonPadding` or calculate from scale
- `borderRadius.button` or `borderRadius.medium`
- `animations.normal` and `animations.easing`

### 3. **Apply the Vibe**
Think: How does **VIBE_SUMMARY_PLACEHOLDER** influence this button?
- Should it be bold and in-your-face?
- Subtle and refined?
- Playful with bounce animations?
- Brutalist with sharp edges?

### 4. **Generate Code**
Write the component using:
- Exact colors from JSON (as Tailwind arbitrary values or CSS vars)
- Exact fonts from JSON
- Spacing from the scale
- Animations matching timings

### 5. **Add Personality**
Based on the vibe, add:
- Micro-interactions (hover states, active states)
- Appropriate animations (subtle vs. dramatic)
- Finishing touches (shadows, glows, textures)

### 6. **Verify Compliance**
- [ ] Colors match JSON exactly
- [ ] Fonts are from JSON
- [ ] Spacing uses the scale
- [ ] Animations use specified timings
- [ ] Component embodies the vibe
- [ ] Nothing generic remains

---

## 🎯 Vibe Translation Examples

**VIBE_SUMMARY_PLACEHOLDER**

Here's how this vibe translates to different components:

### Buttons
[Vibe-specific button guidance will be generated based on the vibe]

### Cards
[Vibe-specific card guidance will be generated based on the vibe]

### Navigation
[Vibe-specific navigation guidance will be generated based on the vibe]

### Forms
[Vibe-specific form guidance will be generated based on the vibe]

### Typography
[Vibe-specific typography guidance will be generated based on the vibe]

---

## 🔧 Integration with Tech Stack

**Tech Stack:** React, TypeScript, Tailwind CSS, Supabase

### Tailwind Configuration

Generate a `tailwind.config.ts` that imports values from frontend.json:

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '{PRIMARY_FROM_JSON}',
        secondary: '{SECONDARY_FROM_JSON}',
        accent: '{ACCENT_FROM_JSON}',
        // ... all colors from JSON
      },
      fontFamily: {
        heading: ['{HEADING_FONT_FROM_JSON}', 'sans-serif'],
        body: ['{BODY_FONT_FROM_JSON}', 'sans-serif'],
        code: ['{CODE_FONT_FROM_JSON}', 'monospace'],
      },
      spacing: {
        // Import spacing scale from JSON
      },
      borderRadius: {
        // Import border radius from JSON
      },
    },
  },
  plugins: [],
};

export default config;
```

### CSS Variables Approach (Alternative)

If not using Tailwind's theme extension:

```css
/* styles/design-tokens.css */
@import url('https://fonts.googleapis.com/css2?family={HEADING_FONT}&family={BODY_FONT}&display=swap');

:root {
  /* Colors */
  --color-primary: {PRIMARY};
  --color-primary-hover: {PRIMARY_HOVER};
  --color-secondary: {SECONDARY};
  --color-accent: {ACCENT};
  --color-background: {BACKGROUND};
  --color-surface: {SURFACE};
  --color-text: {TEXT};
  
  /* Typography */
  --font-heading: {HEADING_FONT}, sans-serif;
  --font-body: {BODY_FONT}, sans-serif;
  --font-code: {CODE_FONT}, monospace;
  
  /* Spacing (using Tailwind's scale) */
  --spacing-0: 0;
  --spacing-1: 0.25rem; /* 4px */
  --spacing-2: 0.5rem;  /* 8px */
  /* ... generate from JSON spacing array */
  
  /* Animations */
  --transition-fast: {FAST}ms;
  --transition-normal: {NORMAL}ms;
  --transition-slow: {SLOW}ms;
  --easing: {EASING};
}
```

---

## 🚨 Critical Reminders

### ALWAYS Do This:
1. ✅ Read frontend.json FIRST
2. ✅ Use EXACT values from the JSON
3. ✅ Apply the vibe to every decision
4. ✅ Verify colors, fonts, spacing match specs
5. ✅ Add personality and micro-interactions
6. ✅ Make it distinctive and memorable

### NEVER Do This:
1. ❌ Use generic fonts (Inter, Roboto) unless in JSON
2. ❌ Use Tailwind defaults without checking JSON
3. ❌ Create cookie-cutter layouts
4. ❌ Ignore the vibe description
5. ❌ Skip the verification checks
6. ❌ Make assumptions about design preferences

---

## 📦 Deliverables Checklist

When you complete a frontend task, ensure:

- [ ] Generated code uses colors from frontend.json (verify hex values)
- [ ] Fonts match typography section exactly
- [ ] Spacing uses values from the spacing scale
- [ ] Border radius matches specifications
- [ ] Animations use specified timings and easing
- [ ] Component embodies the stated vibe
- [ ] No generic AI aesthetics present
- [ ] Micro-interactions and polish added
- [ ] Responsive design implemented (mobile-first)
- [ ] Accessibility considered (ARIA labels, keyboard navigation)
- [ ] TypeScript types defined
- [ ] Component is production-ready

---

## 💡 Remember

**You are not generating "good enough" UI. You are crafting a bespoke, distinctive interface that:**
- Reflects the project's unique personality
- Uses an intentionally chosen design system
- Avoids all generic AI patterns
- Feels designed by a human with taste
- Makes users say "wow, this looks different"

**The vibe is your north star. The JSON is your rulebook. Together, they create something unique.**

---

## 🔄 Iteration Process

If the user requests changes:
1. Re-read frontend.json to confirm specs
2. Re-read the vibe description
3. Apply the specific feedback
4. Maintain consistency with other components
5. Verify against the checklist

---

**Load frontend.json now and let's create something distinctive! 🎨**
