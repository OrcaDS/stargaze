-- Bronze pull: SDSS DR17 spectroscopic labels joined to imaging (see docs/decisions/0001).
-- specObjID % 15 = 0 is a deterministic ~1/15 sample (~283k rows) that keeps the class mix.
-- {lo} / {hi} are filled per chunk by src/stargaze/bronze.py so each query stays under the timeout.
SELECT s.specObjID, s.class, s.z, s.zWarning,
       p.objID, p.ra, p.dec,
       p.psfMag_u, p.psfMag_g, p.psfMag_r, p.psfMag_i, p.psfMag_z,
       p.psfMagErr_u, p.psfMagErr_g, p.psfMagErr_r, p.psfMagErr_i, p.psfMagErr_z,
       p.modelMag_u, p.modelMag_g, p.modelMag_r, p.modelMag_i, p.modelMag_z,
       p.modelMagErr_u, p.modelMagErr_g, p.modelMagErr_r, p.modelMagErr_i, p.modelMagErr_z,
       p.clean
FROM SpecObj AS s
JOIN PhotoObj AS p ON s.bestObjID = p.objID
WHERE s.zWarning = 0
  AND s.specObjID % 15 = 0
  AND s.specObjID >= {lo} AND s.specObjID < {hi}
