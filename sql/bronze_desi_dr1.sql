-- Bronze pull: DESI DR1 cross-survey test set (evaluation only; never trained on).
-- ADQL for the NOIRLab Astro Data Lab TAP service (anonymous access works for public tables).
-- random_id runs 0-100, so random_id < 0.25 is a deterministic ~0.25% sample (~47k rows).
-- Objects with an SDSS DR17 spectrum within 1.5" are dropped: they may be in our SDSS training set.
-- (A fast-moving star can drift past 1.5" between the surveys; that affects very few objects.)
-- flux_* are Legacy Surveys total (Tractor model) fluxes in nanomaggies; there is no u or i band.
SELECT z.targetid, z.spectype, z.z, z.program,
       p.ra, p.dec, p.morphtype,
       p.flux_g, p.flux_r, p.flux_z,
       p.flux_ivar_g, p.flux_ivar_r, p.flux_ivar_z
FROM desi_dr1.zpix AS z
JOIN desi_dr1.photometry AS p ON p.targetid = z.targetid
LEFT JOIN desi_dr1.x1p5__zpix__sdss_dr17__specobj AS x ON x.id1 = z.id
WHERE z.random_id < 0.25
  AND z.survey = 'main'
  AND z.main_primary = 'true'
  AND z.zwarn = 0
  AND x.id1 IS NULL
