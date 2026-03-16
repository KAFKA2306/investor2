---
name: frontend-design
description: |
  [PROJECT-SPECIFIC] Build responsive, production-ready web interfaces with Tailwind CSS, DaisyUI, and HTMX.
  This project uses Tailwind CSS + DaisyUI + HTMX stack (NOT React/shadcn).
  Use this skill whenever the user mentions: HTMX form integration, Tailwind responsive design,
  DaisyUI components, form validation with server-side rendering, or HTML-based frontend architecture.
  Include this skill for any discussion of web interface design in this project context.
compatibility: Requires Tailwind CDN, DaisyUI CDN, HTMX
---

# Frontend Design Guide

## HTMX Form Integration

### Critical: `name` attribute is required

When using HTMX's `hx-include` to submit form values, each input/select **must have a `name` attribute**.

```html
<!-- ✅ CORRECT -->
<input
  type="text"
  id="search-input"
  name="search-input"
  hx-trigger="keyup changed delay:500ms"
  hx-get="/api/search"
  hx-include="[id='search-input'],[id='filter']"
/>

<!-- ❌ WRONG - no name attribute -->
<input
  type="text"
  id="search-input"
  hx-trigger="keyup"
  hx-get="/api/search"
/>
```

The `hx-include` selector finds elements by ID, but HTMX transmits their `name` values in the request. Without `name`, the field value is never sent.

### Why this matters

HTMX works by:
1. Selector (`hx-include`) finds the DOM element
2. Element's `name` attribute becomes the query parameter name
3. Element's `value` attribute becomes the query parameter value
4. Server receives `?name-attribute=value`

If `name` is missing, the value is lost.

### Form Validation Patterns

Use server-side validation with HTMX for real-time feedback:

```html
<form hx-post="/api/validate">
  <div class="form-control">
    <label class="label">Email</label>
    <input
      type="email"
      name="email"
      class="input input-bordered"
      hx-post="/api/validate/email"
      hx-trigger="change"
      hx-target="next .error"
    />
    <div class="error"></div>
  </div>
</form>
```

Server responds with error or success:

```typescript
app.post("/api/validate/email", (c) => {
  const email = c.req.query("email");

  if (!email.includes("@")) {
    return c.html(`
      <div class="alert alert-error">
        <span>Invalid email format</span>
      </div>
    `);
  }

  return c.html(`
    <div class="alert alert-success">
      <span>Valid email</span>
    </div>
  `);
});
```

### Multi-field Form with Validation

```html
<div class="card bg-white shadow">
  <div class="card-body">
    <h2 class="card-title">Contact Form</h2>

    <div class="form-control">
      <label class="label">
        <span class="label-text">Email</span>
      </label>
      <input
        type="email"
        name="email"
        class="input input-bordered"
        hx-post="/api/validate/email"
        hx-trigger="blur"
        hx-target="next .error"
      />
      <div class="error mt-1"></div>
    </div>

    <div class="form-control mt-4">
      <label class="label">
        <span class="label-text">Phone</span>
      </label>
      <input
        type="tel"
        name="phone"
        class="input input-bordered"
        hx-post="/api/validate/phone"
        hx-trigger="blur"
        hx-target="next .error"
      />
      <div class="error mt-1"></div>
    </div>

    <div class="form-control mt-4">
      <label class="label">
        <span class="label-text">Message</span>
      </label>
      <textarea
        name="message"
        class="textarea textarea-bordered"
        hx-post="/api/validate/message"
        hx-trigger="blur"
        hx-target="next .error"
      ></textarea>
      <div class="error mt-1"></div>
    </div>

    <button
      hx-post="/api/contact"
      hx-include="[name='email'],[name='phone'],[name='message']"
      class="btn btn-primary w-full mt-6"
    >
      Submit
    </button>
  </div>
</div>
```

### Validation Response Patterns

**Error response:**
```html
<div class="alert alert-error">
  <span>Email must contain @</span>
</div>
```

**Success response:**
```html
<div class="alert alert-success">
  <span>✓ Valid</span>
</div>
```

Empty response clears previous feedback.

## Responsive Design with Tailwind + DaisyUI

Use Tailwind's responsive prefixes:
- `grid-cols-1` (mobile)
- `lg:grid-cols-4` (desktop)
- `overflow-x-auto` (mobile table scrolling)

```html
<div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
  <aside class="lg:col-span-1">Filter sidebar</aside>
  <main class="lg:col-span-3">Results</main>
</div>
```

---

## Checklist: Common HTMX Form Issues

- [ ] All inputs/selects have `name` attribute (required for value transmission)
- [ ] `hx-include` selector correctly targets elements by ID
- [ ] Server endpoint receives query parameters matching input `name` attributes
- [ ] Validation endpoints return inline error/success HTML
- [ ] Form submission includes all required fields via `hx-include`
- [ ] DaisyUI alert classes used for error/success feedback
