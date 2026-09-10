---
name: web-accessibility-profile
description: Use when web implementation decisions affect native semantics, accessible names, keyboard and focus behavior, images/SVG, forms, dynamic content, motion, contrast, or accessibility evidence; not for test-runner mechanics or a claim of automated WCAG conformance.
---

# Web Accessibility Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Proposed`.

## Core principle

Implement usable semantics and interaction, then test them at the evidence layer
that can establish the claim. Prefer native HTML behavior before adding ARIA.
An accessibility-tree observation is not proof of a person's experience.

## Do not use

Do not use for generic visual design, SVG geometry, CSS language semantics,
JavaScript/TypeScript behavior, React composition or Playwright runner mechanics.
Those owners remain separate and explicitly selected. This profile does not
replace an accessibility audit, legal determination or assistive-technology study.

## Procedure

1. Identify the user task, document language, target devices and assistive
   technologies, applicable standard/version and project acceptance criteria.
2. Inspect native elements, rendered state, name/description sources and keyboard
   behavior before choosing ARIA. Preserve visible instructions and meaning.
3. Apply the clauses below; exercise meaningful positive and negative cases.
4. Separate source, tree, interaction, rendered, manual and real assistive-technology
   evidence. Record untested layers and unresolved user impact.

### Accessible implementation contracts

**AX-01-NATIVE.** Use links with destinations for navigation and buttons for
actions. Choose native controls with established keyboard and state behavior.
ARIA roles do not add focusability, event handling or form behavior. Respect
permitted ARIA-in-HTML combinations; expose accurate roles, states and properties
and update them with actual application state.

**AX-02-NAMES.** Give controls a concise accessible name that identifies purpose
and includes their visible label where applicable. Prefer associated labels and
native content; resolve aria-labelledby references and precedence deliberately.
Use descriptions for supplementary instructions, not a substitute name. Check
computed outcomes, not merely the presence of aria-label/title. Avoid duplicate
or contradictory announcements and unexplained icon-only actions.

**AX-03-STRUCTURE.** Use meaningful heading levels, one coherent page structure
and landmarks that expose regions; distinguish repeated landmarks with names
where useful. Provide bypass/navigation paths. Preserve semantic lists and tables;
associate data headers with cells, caption relevant tables and avoid data-table
semantics for layout. Set document and changed-content language correctly.

**AX-04-FORMS.** Associate labels, instructions, required state and validation
errors with their controls. Identify errors in text and explain correction when
known; preserve entered values. Do not rely only on color, placeholders or a
transient toast. Announce status without stealing focus unnecessarily; coordinate
error summary focus and links with the user's task.

**AX-05-IMAGES.** Decide whether an image conveys meaning in its context.
Decorative HTML images use empty alt; decorative inline SVG must not create
redundant names or tab stops. Meaningful images need an equivalent alternative.
Inline SVG can use appropriate role and resolvable title/label relationships,
verified in the target tree. A complex chart needs its essential relationships,
values or trends available as nearby text, structured data or another equivalent
view; a short title alone is insufficient. SVG authoring still owns geometry,
references and serialization. Do not hide a meaningful descendant accidentally.

**AX-06-KEYBOARD.** Make functionality operable by keyboard with predictable
focus order, visible focus and no trap. Prefer DOM order over positive tabindex.
Custom SVG controls require actual focusability, name, keyboard activation and
state behavior; a role attribute alone is insufficient. Check focus appearance
in rendered states and relevant themes; engine focus-ring pixels can differ.
Avoid pointer/touch-only actions and provide alternatives to complex gestures,
dragging and hover-only content where the applicable criteria require them.

**AX-07-WIDGETS.** For dialogs, popovers and menus, specify opening/closing,
initial focus, traversal, dismissal and focus return. Modal behavior must match
the exposed semantics and background interaction state. Do not apply menu roles
to ordinary navigation merely for appearance. Consult the selected widget contract
and test its keyboard behavior; ARIA does not implement it.

**AX-08-STATE.** Distinguish hidden rendering, inert interaction suppression,
disabled native controls and aria-disabled semantics. aria-hidden changes exposure
without necessarily preventing focus; never leave focus in hidden tree content.
aria-disabled alone does not suppress activation. Check actual focus, activation
and tree consequences, including state transitions and descendants.

**AX-09-DYNAMIC.** Expose live/status updates at suitable urgency without
unnecessary interruption; arrange region presence and updates for target support.
Keep expanded, selected, pressed and busy states accurate. Browser text/tree
changes do not prove that a screen reader announced an update; test real target
assistive technology for that claim.

**AX-10-VISUAL.** Measure rendered text and non-text contrast under applicable
WCAG criteria, including backgrounds, gradients, state and opacity; a CSS color
token alone is insufficient. Do not encode information only in color. Check
zoom, text spacing, reflow and orientation without loss of content or controls,
respecting criterion-specific exceptions. Preserve user styles and visibility.
Honor reduced-motion preferences where relevant, provide pause/stop controls
when required and avoid harmful flashing. Preference queries do not establish
contrast or motion conformance by themselves.

**AX-11-EVIDENCE.** Source/DOM checks establish markup and relationships;
accessibility-tree checks establish observed exposure; keyboard tests establish
actual focus and activation; rendered checks address visibility and measured
contrast; manual review assesses meaning and task usability; real assistive
technology tests address device/software interaction and announcements.
Playwright/ARIA snapshots are not a screen reader. Passing automated checks is
not WCAG conformance proof. State coverage, standard/status, target versions,
manual findings and missing layers separately.

### Response guide

| Level | Accessibility signal | Response |
| --- | --- | --- |
| Green — routine | Native semantics and known interaction contract | Implement and verify proportionally |
| Yellow — caution | Name, mapping, preference or target behavior is uncertain | Inspect computed and rendered outcomes |
| Orange — warning | Custom widget, complex alternative or focus transition changes tasks | Record the bounded interaction decision and layered validation |
| Red — crisis / stop | Keyboard barrier, lost meaning or false conformance claim | Stop the completion claim and resolve the user-facing barrier |

## Project-owned parameters

The project selects conformance target, user tasks, supported platforms and
assistive technologies, widget contracts, content alternatives and review scope.
Do not invent universal document-size thresholds or declare a draft normative
merely because current tooling exposes its terminology.

## Evidence and completion

Report the user task, affected semantics, interaction, standard/version, each
evidence layer and unresolved barriers. APG123 navigation binds AX01 native
naming, AX02 adverse naming, AX03 structure, AX04 rendered focus, AX05 interactive
SVG, AX06 image purpose, AX07 complex alternatives, AX08 state, AX09 live status,
AX10 ARIA snapshot and AX11 form validation. These representative observations
do not cover every clause or establish manual/assistive-technology acceptance.
The [contract](../../docs/specs/web-accessibility-profile.md) records exact
Recommendation and draft statuses and the intentionally limited SVG-AAM use.

## Stop or escalate

Stop a dependent completion claim when meaningful content lacks an alternative,
keyboard users cannot complete the task, focus is lost/trapped, standards status
is misrepresented or automated observations are presented as conformance.
Route missing product decisions or specialist evaluation explicitly.

## Common mistakes

- Adding ARIA before checking native semantics and computed names.
- Treating an SVG title as a complete complex-image alternative.
- Hiding focusable content from the accessibility tree.
- Checking CSS tokens instead of rendered focus or contrast.
- Equating a live-region DOM update with a screen-reader announcement.
