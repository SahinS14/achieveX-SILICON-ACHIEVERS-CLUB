# Student UI audit — 31 October 2026

## Scope and verification limit

Reviewed the source and interactions for Leaderboard, Badges & Achievements, Examination Schedule, About Achievers' Club, shared navigation/footer, themes and admin controls. Students finding their result or next assessment are the priority. Preserved the purple palette, podium waves, mobile badge carousel and supplied preloader duration.

**Rendered visual review is pending.** The computer-use tool consistently reported “Local browser use is disabled in Work settings”, including after the user selected enable. No browser screenshots, computed layout measurements, physical-device gestures or complete accessibility certification were obtained. The viewport figures below describe DOM test configurations, not proof that rendered layouts fit those widths.

## Confirmed findings and implemented corrections

| Before | After | Why it matters to students |
| --- | --- | --- |
| Essential mobile metadata and captions at 6–9px | SIC/year at 11–12px, body text at 14–15px, inputs at 16px; small decorative labels enlarged | Students can read results without needing to zoom |
| Pale rank numbers and white nested mobile menu text in light mode | Explicit solid rank text and dark menu titles/descriptions in light mode | Makes ranking and navigation discernible |
| Search follows a large podium with no shortcut | A “Find your result” shortcut scrolls to standings and focuses SIC/name search | Returning students can reach their result quickly |
| Mixed demo and registered participants labelled official | Mixed results labelled “Includes demo data”; table footer repeats the sample-data state | Students can distinguish sample standings from published-only data |
| First load appears as zero contenders or unpublished results | Explicit loading, unavailable, retry and busy states | Network delay does not masquerade as a competition result |
| Failed background refresh replaces the table with an error | Last loaded scores remain visible with a refresh warning and retry action | Students retain useful results while knowing freshness is uncertain |
| Badge evidence is available through hover titles | Keyboard- and touch-operable badge buttons open an evidence dialog; two badges plus a count keep rows compact | Students can understand their achievements on a phone |
| Pagination buttons around 30–33px tall | 44px-high controls, larger arrows, compact spacing on narrow screens | Easier pagination with a thumb; single-page pagination is hidden |
| Badge slide selection may drift on resize; keyboard arrows animate | Width observer preserves the selected card; keyboard changes are immediate | Better orientation changes and keyboard access |
| Schedule failure can look like unrevealed subjects after changing categories | Explicit error and retry persist across category changes | Students do not mistake a connection failure for a confidential subject |
| Long schedule text competes with date/category columns on mobile | Two-column mobile cards with a separate date line; readable syllabus/date labels | Long subject names and announced dates have room |
| Navigation changes give no keyboard reading position | Focus moves to the destination heading; skip-to-content link added | Keyboard and assistive-technology users can find the new page |
| Small admin labels, cramped five-score row and short edit/delete controls | Readable labels, three score columns on mobile, larger actions and focus indicators | Reduces entry mistakes that affect student results |
| Background refreshes run while another public page is open | Periodic results refresh runs while leaderboard is visible | Avoids unnecessary updates and data requests |
| Some moving effects ignore reduced-motion rules | Final shared reduced-motion rules cover decorative motion and smooth scrolling | Respects motion-sensitive students |

## Evidence

- `npm run check`: 35 Python tests plus DOM interaction smoke tests configured for 320, 390, 768 and 1440px.
- DOM tests cover initial results, SIC search, two-page navigation, category changes, badge evidence, native-dialog open/close, syllabus dialog, menu Escape, light/dark toggle, route focus, carousel selection/end controls, offline first load, background-refresh failure and retry recovery.
- No duplicate IDs or missing local HTML-referenced assets found.
- Selected solid foreground/background pairs calculate contrast ratios of 6.1:1 to 10.8:1 (caption text, light mobile menu, schedule ribbons). These calculations do not measure every composited gradient, background image or rendered state.
- Backend checks remain green. No participant scores, settings or subject reveals changed for this UI work.

## Still needs rendered/device validation

1. Test all four public pages in both themes at 320/390/768/1440px, including 200% text zoom, long names, tied ranks and multiple badges. Check for horizontal page overflow and sticky/floating controls obscuring content.
2. Test the badge carousel with actual touch in iOS Safari and Android Chrome: axis handling, momentum, orientation changes, expanded criteria and selected-dot accuracy. DOM tests cannot simulate the physics or accessibility tree of a real browser.
3. Run a browser accessibility audit and keyboard/screen-reader pass. Check composite contrast on the glass/podium and every disabled/revealed schedule state.
4. Check low-end phone performance and mobile data loading. The avatar atlas is about 2.5MB, the club logo 946KB and header illustration 913KB; conversion to smaller faithful delivery assets is a worthwhile follow-up. Small badge-chip images now lazy-load, but the larger existing artwork is retained.
5. The requested preloader remains 2.4 seconds minimum / 6.5 seconds fallback with a skip control. That is a deliberate branding preference; repeat student visits would benefit from a shorter returning-user path if approved later.

Run regression checks after `npm ci` with `npm run check`. The jsdom development dependency is used only for source/DOM tests; production remains static HTML/CSS/JS with Python APIs.
