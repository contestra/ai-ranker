# Contestra Design System Reference

## Brand Colors

### Primary Actions
- **Blue**: `#3D70B8` - Primary buttons, CTAs (Settings, Create Template, Refresh)
- **Green**: `#2D8A2D` - Execution/Run actions (Run Test)
- **Orange**: `#D96D14` - Running/Processing state

### Accent Colors
- **Pink/Accent**: `#ff0088` - Selected states, highlights (outline only, not filled)
- **Highlight Yellow**: `#FFFF80` - Special highlights
- **Highlight Purple**: `#6633CC` - Secondary highlights

### Gray Scale
- **Gray-50**: `#FEFEFE` - Almost white
- **Gray-75**: `#FCFCFC` - Very light gray
- **Gray-100**: `#F8F9FA` - Light backgrounds
- **Gray-300**: `#DEE2E6` - Borders, dividers
- **Gray-500**: `#ADB5BD` - Muted text
- **Gray-700**: `#495057` - Secondary text
- **Gray-900**: `#212529` - Primary text
- **Gray-950**: `#1A1E22` - Dark charcoal (main dark color)
- **Gray-1000**: `#111315` - Darker variant
- **Black**: `#000000` - Pure black

### Sparkle/Decorative Colors
- **Sparkle Cyan**: `#35FDF3`
- **Sparkle Yellow**: `#FEFFCC`
- **Sparkle Pink**: `#FFE6F3`
- **Sparkle Blue**: `#4567FF`

## Typography

### Font Families
1. **Suisse Screen** (`font-display`)
   - Display/heading font
   - Weights: 300, 350, 400, 500, 600, 700
   - Used for: Headlines, buttons text, country/grounding mode labels

2. **Suisse Intl** (`font-body`)
   - Body text font
   - Weights: 400, 500, 700
   - Used for: Paragraphs, descriptions, general content

3. **Suisse Intl Mono** (`font-mono`)
   - Monospace font
   - Weight: 400
   - Letter spacing: 0.02em
   - Used for: Field labels, code, technical text

### Font Sizes
- Base: 62.5% (10px) for easy rem calculations
- Body: 1.6rem (16px)
- Line height: 1.5 for body, 1.2 for headings

## Gradients

### Spectrum Gradients (Contestra signature)
```css
/* Primary spectrum - 95% white mix */
background: linear-gradient(to right, 
  #f2ffff 0%, #f2fff9 20%, #f9fff2 35%, 
  #fffff2 50%, #fff9f2 65%, #fff2f9 80%, #fff2f5 100%);

/* 70% white mix - for hover states */
background: linear-gradient(to right,
  #b3ffff 0%, #b3ffdb 20%, #dbffb3 35%,
  #ffffb3 50%, #ffdbb3 65%, #ffb3db 80%, #ffb3c7 100%);

/* 90% white mix - for subtle accents */
background: linear-gradient(to right,
  #E6FFFF 0%, #E6FFF3 20%, #F3FFE6 35%,
  #FFFFE6 50%, #FFF3E6 65%, #FFE6F3 80%, #FFE6EC 100%);

/* 97.5% white mix - ultra-subtle */
background: linear-gradient(to right,
  #f9ffff 0%, #f9fffc 20%, #fcfff9 35%,
  #fffff9 50%, #fffcf9 65%, #fff9fc 80%, #fff9fa 100%);
```

## Component Styling

### Buttons
- **Border radius**: 50px (signature Contestra curve)
- **Padding**: px-[2.2rem] py-2
- **Transition**: all 300ms ease-out
- **Border**: 1px solid rgba(0,0,0,0.06)
- **Font**: Suisse Intl Mono with 0.02em letter spacing
- **Hover**: opacity-90 or slight Y translation

### Button Colors by Type
- **Primary Actions**: Blue (#3D70B8) background, white text
- **Run/Execute**: Green (#2D8A2D) background, white text
- **Running State**: Orange (#D96D14) background, white text
- **Selected Toggle**: White background, pink (#ff0088) text and border
- **Unselected Toggle**: White background, gray text, subtle border

### Form Elements

#### Field Labels
- Font: Suisse Intl Mono
- Size: text-xs (0.75rem)
- Style: UPPERCASE
- Letter spacing: 0.02em
- Color: #474350 (text-meta)
- Margin bottom: 1.5

#### Input Fields
- Border radius: 8px (rounded-lg)
- Border: 1px solid rgba(0,0,0,0.06)
- Padding: px-4 py-3
- Focus: Pink accent border with shadow
- Background: White
- Font: Suisse Intl (body font)

### Cards
- Background: White
- Border radius: 16px (rounded-2xl)
- Border: 1px solid rgba(0,0,0,0.06)
- Hover: Translate Y -4px, shadow-xl, gradient strip appears
- Gradient strip: 4px height, spectrum gradient at top

## Shadows
```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 15px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 6px 20px rgba(0, 0, 0, 0.15);
--shadow-xl: 0 10px 30px rgba(0, 0, 0, 0.1);
```

## Responsive Breakpoints
- **576px**: Small mobile
- **768px**: Tablet
- **1024px**: Small desktop
- **1200px**: Large desktop
- **1440px**: Maximum container width

## Layout System
- **Container max-width**: 1440px (144rem)
- **Container padding**: 50px desktop, 15px mobile
- **Navigation height**: 70px default, 54px scrolled

## Animation & Transitions
- **Fast**: 150ms ease
- **Base**: 300ms ease
- **Slow**: 400ms cubic-bezier(0.4, 0, 0.2, 1)

## State Colors in UI

### Template/Test States
- **Ready**: Green button (#2D8A2D)
- **Running**: Orange button (#D96D14)
- **Completed**: Green checkmark icon
- **Failed**: Red X icon
- **Disabled**: Gray (#ADB5BD)

### Selection States
- **Selected**: Pink outline (#ff0088), white background
- **Unselected**: Gray outline (rgba(0,0,0,0.06)), white background
- **Hover**: Light gray background (#F8F9FA)

## Usage Guidelines

### When to Use Each Color
1. **Blue (#3D70B8)**: Primary CTAs, settings, configuration actions
2. **Green (#2D8A2D)**: Start, run, execute, positive actions
3. **Orange (#D96D14)**: Processing, loading, in-progress states
4. **Pink (#ff0088)**: Selected items, active states (outline only)
5. **Grays**: Backgrounds, borders, secondary text

### Typography Best Practices
1. Use **Suisse Screen** for display text and UI labels
2. Use **Suisse Intl** for body text and descriptions
3. Use **Suisse Intl Mono** with letter-spacing for:
   - Form field labels (UPPERCASE)
   - Technical identifiers
   - Code snippets
   - Button text

### Component Patterns
1. **Buttons**: Always 50px border radius, use brand colors
2. **Selected states**: Pink outline, never filled pink background
3. **Cards**: White with subtle border, gradient strip on hover
4. **Forms**: Uppercase mono labels, rounded inputs with focus states

## Implementation Notes

### Tailwind Classes
- Primary button: `btn-contestra-primary`
- Field label: `field-label`
- Input: `input-contestra`
- Card: `card-contestra`
- Gradient backgrounds: `bg-spectrum`, `bg-spectrum-subtle`

### CSS Variables
All colors and spacing values are available as CSS variables and Tailwind utilities with the `contestra-` prefix (e.g., `bg-contestra-blue`, `text-contestra-accent`).

---

*Last updated: August 2025*
*Design system based on contestra.com brand guidelines*