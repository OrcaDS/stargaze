# 0001: Which SDSS release to pin

_Status: decided · Raised 2026-10-26 · Decided 2026-10-26_

## Context
Table and column names can differ between SDSS releases, and every bronze export must record the release it came from. We need one pinned release for the legacy imaging (`PhotoObj`) and spectroscopy (`SpecObj`) tables used by the core query in [sql/bronze_sdss_dr17.sql](../../sql/bronze_sdss_dr17.sql).

## Options
- **DR20** (latest, public since 30 July 2026): its new content is SDSS-V (new BOSS spectra, LVM, APOGEE copied from DR19). For the legacy imaging survey, its own page points back to DR17.
- **DR19**: also SDSS-V-era; same legacy content.
- **DR17** (final SDSS-IV release): what the KAN robustness paper (arXiv 2605.29039, "100,000 SDSS DR17 objects") and Kaggle SDSS17 use.

## Evidence (checked 2026-10-26 on public SkyServer, `SkyServerWS/SearchTools/SqlSearch`)
- The spec's core query (`SpecObj` JOIN `PhotoObj` ON `bestObjID = objID`, `zWarning = 0`) runs unchanged on DR17, DR19 and DR20, with all columns present.
- Row counts by class are identical in all three: GALAXY 2,617,800 · QSO 751,178 · STAR 881,004 (4,249,982 rows).
- In DR17, all rows are `sciencePrimary = 1`, but there are 4,249,921 distinct `bestObjID`s: 61 photometric objects have two primary spectra.

## Decision
Pin **DR17**. The legacy tables give the same rows as DR19/DR20, so newer releases add nothing for this project, while DR17 makes comparisons with the KAN paper and Kaggle SDSS17 like-for-like.

## Consequences
- Queries target the DR17 context (SkyServer `https://skyserver.sdss.org/dr17/`, CasJobs context `DR17`); bronze metadata records `release = DR17`.
- Silver must de-duplicate on `objID` (keep one spectrum per object, e.g. lowest `specObjID`) so no object can fall in more than one split.
- Revisit only if a later release changes the legacy tables (re-run the class-count check above).
