# CareerPilot Frontend Optimization Plan
## Using Taste Skill Framework (v2)

**Design Read:** B2B SaaS dashboard for job seekers, with a clean / professional / trust-first language, leaning toward Radix UI + Geist + restrained motion.

**Dial Settings:**
- DESIGN_VARIANCE: 6 (moderate - professional but not boring)
- MOTION_INTENSITY: 4 (restrained - subtle transitions only)
- VISUAL_DENSITY: 3 (airy - data needs to breathe)

---

## Phase 1: Typography & Font System

### Current Issues
- Using default Inter font (AI-default)
- Inconsistent heading scales
- Missing tracking adjustments for uppercase text

### Optimizations
1. **Switch to Geist Sans** (Vercel's modern, professional font)
2. **Add Geist Mono** for code/technical elements
3. **Tighten headline tracking** (`tracking-tighter` on `text-4xl+`)
4. **Add leading discipline** (relaxed body text `leading-relaxed`)

---

## Phase 2: Icon System Upgrade

### Current Issues
- Using `lucide-react` (discouraged by taste-skill as LLM-default)
- Inconsistent stroke widths

### Optimizations
1. **Replace with `@phosphor-icons/react`** (more professional, better variety)
2. **Standardize on 1.5px stroke weight**
3. **Use Phosphor's duotone variant sparingly for key actions**

---

## Phase 3: Layout & Spacing

### Current Issues
- Overuse of centered layouts
- Card-heavy design (elevation abuse)
- Inconsistent section padding

### Optimizations
1. **Asymmetric dashboard grid** (sidebar + main, varying column widths)
2. **Reduce card usage** - use `border-t` and whitespace for grouping
3. **Standardize breakpoints** (sm:640, md:768, lg:1024, xl:1280, 2xl:1536)
4. **Add `max-w-7xl` container** for large screens
5. **Use viewport units properly** (`min-h-[100dvh]` for hero sections)

---

## Phase 4: Color Calibration

### Current Issues
- Neutral palette is good (no AI-purple sickness)
- Missing subtle color differentiation

### Optimizations
1. **Keep current neutral base** (Zinc/Slate works well)
2. **Add single accent color** (Emerald for success, deep blue for primary)
3. **Tint shadows** to background color (no pure black shadows)
4. **Consistent border colors** across light/dark mode

---

## Phase 5: Motion & Interaction

### Current Issues
- No animation library installed
- Basic CSS transitions only
- Missing tactile feedback on buttons

### Optimizations
1. **Install `motion/react`** (formerly Framer Motion)
2. **Add page transition** (subtle fade/slide, 200ms)
3. **Button press physics** (`scale-[0.98]` on `:active`)
4. **Smooth hover transitions** (`transition-all duration-200`)
5. **Loading animations** (skeleton layouts, not spinners)

---

## Phase 6: Component-Level Improvements

### Dashboard (`page.tsx`)
1. **Scraper card** - add visual asset (real icon, not gradient blob)
2. **Stats cards** - better hierarchy with typography
3. **Activity feed** - better spacing between items

### Job Cards (`job-card.tsx`)
1. **Remove excessive badges** - consolidate status + tier
2. **Better description truncation** - `line-clamp-3` for readability
3. **Add hover states** - subtle lift (`hover:shadow-md`)

### Navigation
1. **Single-line nav enforcement** on desktop
2. **Better mobile hamburger** with smooth transition
3. **Reduce nav height** to 64px max

---

## Phase 7: Loading & Error States

### Current Issues
- Generic spinners everywhere
- No empty states

### Optimizations
1. **Skeleton loaders** matching final layout shape
2. **Beautiful empty states** with call-to-action
3. **Inline error states** (not just toasts)
4. **Optimistic UI updates** (show changes immediately)

---

## Dependencies to Install

```bash
cd /home/ubuntu/careerpilot/frontend

# Icons (replace lucide-react)
npm install @phosphor-icons/react

# Motion (replaces framer-motion)
npm install motion

# Fonts (optional - already using next/font)
# Geist is available via next/font/google
```

---

## Implementation Priority

### High Priority (do first)
1. ✅ Typography system upgrade
2. ✅ Container/layout standardization
3. ✅ Button tactile feedback
4. ✅ Skeleton loading states

### Medium Priority
5. Icon system migration (lucide → phospor)
6. Motion library integration
7. Card reduction (replace with borders/whitespace)

### Low Priority (nice-to-have)
8. Asymmetric layout experiments
9. Custom accent color palette refinement
10. Advanced page transitions

---

## Pre-Flight Checklist (Before Each Component)

- [ ] Hero fits in initial viewport (no forced scroll)
- [ ] CTA text fits on one line (no wrap)
- [ ] Button contrast passes WCAG AA
- [ ] No duplicate CTA intent on same page
- [ ] Skeleton loader matches final shape
- [ ] Mobile collapse explicitly handled
- [ ] No generic AI-purple gradients
- [ ] Typography tracking appropriate for size
- [ ] Section uses intentional layout (not centered default)
- [ ] Real images/icons (no div-based fake screenshots)

---

**Final Note:** CareerPilot is a dashboard/tool, not a landing page. The taste-skill framework is adapted here - we're optimizing for **clarity, trust, and efficiency** rather than "wow factor". The restrained, professional aesthetic is correct for this use case.