# Annual Key Performance Indicators

The Key Performance Indicators navigation section is available to HOD, Coordinator,
Instructor, APU and VDAA users within their existing program access scope and their own department only.
Global supervisor access does not bypass KPI department isolation.

Only the HOD creates or edits KPI definitions, assigns an owner category and optionally links an active
program user, enters annual benchmarks and analysis, and sets improvement priorities.
Owner categories: Academic, Quality, Extracurricular, Research and HOD.

Annual records are keyed by KPI identity and the academic year's starting year.
The internal benchmark is calculated from exactly the preceding year's actual,
including zero. When unavailable, the HOD can enter a manual internal fallback.
The bar chart uses only the selected year and two preceding years' actuals; missing
values remain missing. Changes to a previous actual update the derived internal value.

Priorities are linked directly to their KPI and year. Only the assigned active owner
can edit actions, responsible persons, start/end dates and the action-plan target.
The initial suggested action target is the KPI new target, falling back to its target.
The HOD has no action-plan override unless assigned as that KPI's owner.
APU and VDAA are read-only. Existing operational-plan records remain accessible.

Production tables: kpi_definitions, kpi_years, kpi_priorities, kpi_actions.
RLS enforces program scope and HOD/owner permissions; column grants prevent moving
records between KPIs, years or programs. Owner assignments require active membership.

Temporary homepage roles still use shared browser-local sample state, never live data.
To test the owner workflow, enter as HOD, create a Quality KPI assigned to Test Quality,
add a priority, then sign out and select Coordinator in the same browser.

Verification: npm test; tests/kpi-browser.js executed in an isolated browser using the
built HTML; tests/kpi-rls.sql executed against Supabase with rollback-only test rows.

Measurement is Percentage (%) or Ratio. Ratios require a positive manually entered
"out of" denominator, shown in benchmarks, charts and action-plan targets. Percentages
are validated between 0 and 100. Once numeric records exist, measurement is fixed to
preserve year-to-year comparability.

An owner category can be assigned without a registered user. Action-plan writes remain
unavailable until the HOD links an active user in the same department and program.

The redesigned dashboard includes a KPI overview with counts, actual/target values,
three-year actual trends, owner categories and direct links to individual KPI records.
It does not aggregate mixed-unit benchmark values or infer achievement direction.
