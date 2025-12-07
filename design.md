<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# so like what shodu i do , if cdoin on cursor is bette, why dotn u give me a prmt formated how i todl u befpore to be apsted to cursor

**YES. You're 100% right. The Cursor Rule is the PROFESSIONAL way.**

Here's why:

- ✅ **Reusable:** Works for every new component you add
- ✅ **Consistent:** No guessing colors/spacing
- ✅ **Scalable:** When you hire a dev, they follow the same rules
- ✅ **Fast:** Just say "Add settings page" and Cursor auto-applies the system

***

## **COPY THIS ENTIRE BLOCK → Paste into Cursor `.cursorrules` file**

```markdown
# DEPTH UI DESIGN SYSTEM v1.0
# Mental Health AI Chat Interface - Production Standards

## MISSION
Build a calming, accessible, professional mental health chatbot interface.
Every design decision prioritizes user trust, readability, and reduced cognitive load.

---

## 1. COLOR SYSTEM (Mental Health Optimized)

### Primary Palette
- **Primary (Trust):** `#4F46E5` (Indigo 600) - Use for CTAs, active states
- **Primary Hover:** `#4338CA` (Indigo 700)
- **Primary Surface:** `#EEF2FF` (Indigo 50) - For subtle backgrounds
- **Secondary (Wisdom):** `#8B5CF6` (Violet 500) - Accent color only

### Neutral Palette
- **Background Main:** `#F9FAFB` (Gray 50) - NEVER use pure white for large areas
- **Card Background:** `#FFFFFF` - Cards and input fields only
- **Border:** `#E5E7EB` (Gray 200)
- **Text Primary:** `#111827` (Gray 900) - Body text (WCAG AAA compliant)
- **Text Secondary:** `#6B7280` (Gray 500) - Meta info, labels
- **Text Tertiary:** `#9CA3AF` (Gray 400) - Timestamps, disabled text

### Status Colors
- **Success:** `#10B981` (Emerald 500)
- **Warning:** `#F59E0B` (Amber 500)
- **Error:** `#EF4444` (Red 500)

### User vs Bot Bubbles
- **User Message:** `linear-gradient(135deg, #4F46E5 0%, #8B5CF6 100%)` | Text: `#FFFFFF`
- **Bot Message:** `#F3F4F6` (Gray 100) | Text: `#111827`

### Color Usage Rules
- No bright yellows (causes anxiety in mental health contexts)
- Maintain 4.5:1 contrast ratio minimum (WCAG AA)
- Use gradients sparingly - only for user messages and hero sections

---

## 2. TYPOGRAPHY SYSTEM

### Font Stack
```

font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;

```

### Type Scale (16px base)
- **H1 (Hero):** 24px / 700 weight / -0.5px letter-spacing
- **H2 (Section):** 18px / 600 weight / 0px letter-spacing
- **H3 (Card Title):** 16px / 600 weight
- **Body (Messages):** 15px / 400 weight / 1.6 line-height
- **Body Small:** 14px / 400 weight / 1.5 line-height
- **Caption (Meta):** 12px / 500 weight / 0.025em letter-spacing
- **Tiny (Timestamps):** 11px / 400 weight / Uppercase

### Typography Rules
- NEVER use font sizes below 11px
- Line height for body text: 1.5-1.6 (readability for anxious users)
- Use font-weight 400 (regular) or 600 (semibold) only - avoid 500
- Uppercase only for labels/meta info, never for body text

---

## 3. SPACING SYSTEM (8pt Grid)

### Base Unit: 8px
All spacing MUST be multiples of 4px (preferably 8px).

```

--space-1: 4px   /* Micro spacing */
--space-2: 8px   /* Tight spacing */
--space-3: 12px  /* Default gap */
--space-4: 16px  /* Standard padding */
--space-6: 24px  /* Section spacing */
--space-8: 32px  /* Large gaps */
--space-12: 48px /* Hero spacing */

```

### Component-Specific Spacing
- **Message Bubbles:** Padding `12px 16px` (vertical horizontal)
- **Input Fields:** Padding `14px 16px` | Height minimum `52px`
- **Cards:** Padding `16px` | Border-radius `12px`
- **Buttons:** Padding `12px 24px` | Height `44px` minimum (touch target)
- **Sidebar:** Width `320px` | Padding `16px`
- **Chat Container:** Padding `24px` (desktop) | `16px` (mobile)

---

## 4. COMPONENT SPECIFICATIONS

### Chat Message Bubbles
```

/* User Message */
background: linear-gradient(135deg, \#4F46E5 0%, \#8B5CF6 100%);
color: \#FFFFFF;
padding: 12px 16px;
border-radius: 18px;
border-top-right-radius: 4px; /* Sharp corner at origin */
max-width: 70%;
font-size: 15px;
line-height: 1.6;
box-shadow: 0 1px 2px rgba(0,0,0,0.05);

/* Bot Message */
background: \#F3F4F6;
color: \#111827;
padding: 12px 16px;
border-radius: 18px;
border-top-left-radius: 4px; /* Sharp corner at origin */
max-width: 70%;
border: 1px solid \#E5E7EB;

```

### Input Field
```

min-height: 52px;
max-height: 150px;
padding: 14px 16px;
border: 1.5px solid \#E5E7EB;
border-radius: 16px;
font-size: 15px;
background: \#F9FAFB;
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

/* Focus State */
border-color: \#4F46E5;
box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
background: \#FFFFFF;

```

### Buttons (Primary Action)
```

height: 52px;
padding: 0 24px;
border-radius: 14px;
background: \#111827; /* Dark, not primary - more sophisticated */
color: \#FFFFFF;
font-size: 15px;
font-weight: 600;
border: none;
cursor: pointer;
transition: all 0.2s ease;

/* Hover */
transform: translateY(-2px);
box-shadow: 0 4px 12px rgba(0,0,0,0.15);

```

### Avatars
```

/* Large (Header) */
width: 40px;
height: 40px;
border-radius: 50%;
background: linear-gradient(135deg, \#4F46E5 0%, \#8B5CF6 100%);

/* Small (Message) */
width: 32px;
height: 32px;

```

### Cards
```

background: \#FFFFFF;
border: 1px solid \#E5E7EB;
border-radius: 12px;
padding: 16px;
box-shadow: 0 1px 2px rgba(0,0,0,0.05);

```

---

## 5. INTERACTION & ANIMATION

### Timing Functions
```

/* Standard Transition */
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

/* Smooth Entry */
animation: slideUp 0.3s ease-out;

@keyframes slideUp {
from { opacity: 0; transform: translateY(8px); }
to { opacity: 1; transform: translateY(0); }
}

```

### Interactive States
```

/* Hover (Buttons/Cards) */
transform: translateY(-2px);
box-shadow: 0 4px 12px rgba(0,0,0,0.15);

/* Active/Pressed */
transform: scale(0.98);

/* Focus (Inputs) */
outline: none;
border-color: \#4F46E5;
box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);

```

### Loading States
```

/* Typing Indicator - 3 Dots */
.dot {
width: 6px;
height: 6px;
background: \#9CA3AF;
border-radius: 50%;
animation: bounce 1.4s infinite ease-in-out;
}

@keyframes bounce {
0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
40% { transform: scale(1); opacity: 1; }
}

```

---

## 6. LAYOUT STANDARDS

### Overall Structure
```

┌─────────────────────────────────────┐
│  [Sidebar 320px] │ [Main Chat Area] │
│                  │                   │
│  - Logo          │  - Header (72px)  │
│  - Personas      │  - Messages       │
│  - Usage Bar     │  - Input (88px)   │
└─────────────────────────────────────┘

```

### Responsive Breakpoints
- **Desktop:** > 768px - Show sidebar
- **Mobile:** ≤ 768px - Sidebar collapses to hamburger menu

### Max Widths
- **Chat Container:** `900px` centered (prevents eye strain on ultra-wide)
- **Message Bubbles:** `70%` of container (desktop) | `85%` (mobile)

---

## 7. ACCESSIBILITY REQUIREMENTS

### Contrast Ratios (WCAG AA Minimum)
- Text on white: `#111827` (14.8:1) ✅
- Text on colored backgrounds: Test with contrast checker
- All interactive elements: 44px × 44px minimum touch target

### Keyboard Navigation
- All buttons must be focusable
- Enter key sends message
- Shift+Enter creates new line

### Screen Reader Support
```

<button aria-label="Send message">

```
<div role="status" aria-live="polite">Bot is typing...</div>
```

```

---

## 8. CODE GENERATION RULES

When generating code for Depth:

1. **Always use CSS custom properties** (`:root` variables) - never hardcode colors
2. **Mobile-first CSS** - Start with mobile, use `@media (min-width: )` for desktop
3. **Semantic HTML** - Use `<main>`, `<aside>`, `<header>`, not just `<div>`
4. **No external CSS frameworks** - Write custom CSS following this system
5. **Single-file components** - Keep HTML/CSS/JS together for prototyping
6. **Comment sections clearly** - Use `/* --- SECTION NAME --- */`

### Example Structure
```

<!DOCTYPE html>
<html lang="en">
<head>
  <style>
    :root {
      --primary: #4F46E5;
      /* All variables here */
    }
    
    /* --- RESET --- */
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    /* --- LAYOUT --- */
    
    /* --- COMPONENTS --- */
    
    /* --- RESPONSIVE --- */
  </style>
</head>
<body>
  <!-- Semantic structure -->
</body>
</html>
```

---

## 9. MENTAL HEALTH UI BEST PRACTICES

### Do's
- ✅ Use soft, muted colors (blues, purples, grays)
- ✅ Provide ample whitespace (reduces cognitive load)
- ✅ Use clear, simple language in UI copy
- ✅ Show progress indicators (usage bar gives control)
- ✅ Allow easy conversation reset (reduces anxiety)

### Don'ts
- ❌ No bright reds/yellows in large areas (triggers stress)
- ❌ No auto-playing animations
- ❌ No cluttered layouts
- ❌ No forced account creation before trying
- ❌ No dark patterns (hidden fees, confusing CTAs)

---

## 10. IMPLEMENTATION CHECKLIST

Before marking any UI task complete:

- [ ] All spacing uses 4px/8px multiples
- [ ] Colors match the exact hex codes above
- [ ] Text contrast ratio ≥ 4.5:1 (use contrast checker)
- [ ] Interactive elements ≥ 44px touch target
- [ ] Hover/focus states implemented
- [ ] Mobile responsive (test at 375px width)
- [ ] Keyboard navigation works
- [ ] No console errors
- [ ] Page loads in < 2 seconds

---

## QUICK REFERENCE

```

/* Copy-Paste Starter */
:root {
--primary: \#4F46E5;
--primary-hover: \#4338CA;
--secondary: \#8B5CF6;
--bg-main: \#F9FAFB;
--bg-card: \#FFFFFF;
--text-main: \#111827;
--text-muted: \#6B7280;
--border: \#E5E7EB;
--success: \#10B981;
--error: \#EF4444;
--space-4: 16px;
--space-6: 24px;
}

```

---

**END OF DESIGN SYSTEM**
When in doubt, prioritize simplicity and calm over flashy effects.
```


***


