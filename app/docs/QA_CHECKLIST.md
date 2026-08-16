# Accessibility & responsive QA checklist

Run through this before shipping any change.

## Responsive

- [ ] App usable at exactly 360px width (Chrome DevTools device toolbar, no horizontal scroll on any screen)
- [ ] Sidebar hidden below 900px; bottom nav visible and usable with a thumb
- [ ] Transactions table becomes stacked cards below 760px (`.desktop-table` / `.mobile-cards` classes)
- [ ] Add-transaction textarea and confirm dialog remain fully usable at 360px
- [ ] No element requires horizontal scrolling to complete a financial action (confirm, reject, add transaction)
- [ ] Common desktop sizes checked: 1280px, 1440px, 1920px

## Keyboard & focus

- [ ] Every nav link, button, and form field reachable via Tab in a sensible order
- [ ] `:focus-visible` ring visible on every interactive element (see `src/styles/global.css`)
- [ ] Confirm/reject dialog: focus should move into the dialog on open and back to the trigger on close (currently relies on browser default \u2014 verify manually, consider a focus trap if it doesn't feel right)
- [x] Escape key closes the confirm dialog and the transaction detail drawer
- [ ] Language switcher buttons show `aria-pressed` state correctly

## Screen reader / semantics

- [ ] Confirm dialog has `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing at its title (already done in `ConfirmDialog.tsx` \u2014 verify with VoiceOver/NVDA)
- [ ] Status pills (`StatusBadge`, sync status) are never the only signal \u2014 confirm text label always accompanies color
- [ ] Charts (`IncomeExpenseChart`, `CategoryBars`) have an `aria-label`/`role="img"` summary; consider adding a visually-hidden data table fallback for screen reader users before general release
- [ ] Every `<img>`-equivalent icon (`<i className="ti ...">`) is `aria-hidden` and paired with visible or `aria-label` text

## States (every data-driven screen)

- [ ] Loading state shown immediately on mount, not a blank screen
- [ ] Empty state has a clear, specific message (not just "no data")
- [ ] API error state offers a retry action
- [ ] Permission-denied state (`PermissionDeniedState`) is wired up once roles are enforced server-side \u2014 currently unused, since role enforcement isn't real yet
- [ ] Offline state: verify behavior when `navigator.onLine` is false during a submit (not yet explicitly handled \u2014 add a check before general release)
- [ ] Duplicate-submission protection: confirm/reject buttons disable immediately on click and stay disabled until the request resolves (`ConfirmDialog` handles this globally)

## Financial-specific

- [ ] All UZS amounts use `formatUzs`/`CurrencyAmount` \u2014 no ad hoc `toLocaleString()` calls
- [ ] Tabular numerals (`.tabular-num`) applied everywhere a number appears in a list or table
- [ ] Negative/reversal amounts always red, confirmed/positive always green, pending/clarification always amber \u2014 grep for raw hex colors outside `tokens.css` to catch drift
- [x] Production pages use backend data; no mock layer is shipped

## Build

- [ ] `npm run typecheck` passes with zero errors
- [ ] `npm run build` completes successfully
- [ ] No secret, token, or `.env` value committed to the repo (`git grep -i "token\|secret"` before each release)
