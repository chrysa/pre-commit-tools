---
applyTo: "**/*.{ts,tsx,js,jsx,css}"
---

# Frontend Guidelines

## React / TypeScript

- Use **functional components** only — no class components
- Props must be typed with a dedicated `interface` or `type` (never inline `{}`)
- Export components as **named exports** (no default exports)
- Component files: one component per file, named after the component

---

## No `console.*` in Production Code

All `console.*` calls are forbidden in production code:

| Method | Hook that catches it |
|---|---|
| `console.log()` | `console-log-detection` |
| `console.debug()` | `console-debug-detection` |
| `console.table()` | `console-table-detection` |
| `console.warn()` | `no-console-warn` |
| `console.error()` | `react-console-error-detection` (React files) |

Use a structured logger instead (e.g. `pino`, `winston`, or a custom `logger.ts`).

---

## No Direct DOM Manipulation in React

Never use `document.getElementById`, `document.querySelector`, etc. in React components.
Use React refs or state:

```tsx
// WRONG — bypasses virtual DOM
const el = document.getElementById('input') as HTMLInputElement;

// CORRECT — React ref
const inputRef = useRef<HTMLInputElement>(null);
```

The `react-direct-dom` hook catches these patterns in `.tsx/.jsx` files.

---

## No Deep Relative Imports

Never use `../../` or deeper relative parent imports. Use configured path aliases:

```ts
// WRONG
import { Button } from '../../../components/Button';

// CORRECT
import { Button } from '@/components/Button';
```

Configure in `tsconfig.json`:
```json
{ "compilerOptions": { "paths": { "@/*": ["src/*"] } } }
```

The `import-no-relative-parent` hook catches 2+ levels of `../`.

---

## TypeScript Typing

- Use explicit return types on all exported functions
- No `any` — use `unknown` + type guard if necessary
- Prefer `interface` for object shapes, `type` for unions/aliases

---

## CSS Variables

Declare CSS custom properties at `:root` level and use them consistently.
Unused variables are caught by `css-unused-variable-detection`.
Duplicate properties are caught by `css-duplicate-property-detection`.

---

## JavaScript Syntax

All `.js` and `.gs` (Google Apps Script) files must pass Node.js syntax validation.
The `js-syntax-check` hook runs `node --check` on every `.js/.gs` file.
