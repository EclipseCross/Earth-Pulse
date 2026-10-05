# Observed GUNW granule layout

This document records observations from one real NASA NISAR file. It is a
layout reference, not a claim that every GUNW release has identical contents.

## Provenance

- Granule: `NISAR_L2_PR_GUNW_023_040_A_014_024_4000_SH_20260616T230456_20260616T230531_20260628T230456_20260628T230530_P05023_N_F_J_001.h5`
- Root `title`: `NISAR L2 GUNW Product`
- Root `institution`: `NASA JPL`
- Root `Conventions`: `CF-1.7`
- Root `reference_document`: `D-102272 NISAR NASA SDS Product Specification L2 Geocoded Unwrapped Interferogram`
- Filename acquisition interval: `2026-06-16T23:04:56` to `2026-06-16T23:05:31`
- Filename processing interval: `2026-06-28T23:04:56` to `2026-06-28T23:05:30`

## Confirmed grid

The following datasets were observed below
`science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram/`:

| HDF5 path | Shape | Type | Observed units/fill |
|---|---:|---|---|
| `HH/unwrappedPhase` | `(4257, 4338)` | `float32` | `radians`, `_FillValue=NaN` |
| `HH/coherenceMagnitude` | `(4257, 4338)` | `float32` | `1`, `_FillValue=NaN` |
| `mask` | `(4257, 4338)` | `uint32` | `_FillValue=255` |
| `xCoordinates` | `(4338,)` | `float64` | `meters` |
| `yCoordinates` | `(4257,)` | `float64` | `meters` |
| `xCoordinateSpacing` | scalar `80.0` | `float64` | `meters` |
| `yCoordinateSpacing` | scalar `-80.0` | `float64` | `meters` |

`unwrappedPhase` is described in the file as an unwrapped interferogram
between HH layers. Its observed summary attributes were minimum
`-15.134798`, maximum `23.998388`, mean `4.421261`, and sample standard
deviation `5.736570` radians. These are file metadata summaries, not a
displacement result.

The coherence field is a quality indicator with observed range
`0.003232` to `0.983127`. It is not displacement.

## Projection

The scalar dataset
`science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram/projection`
contains the value `32646` and attributes identifying:

- EPSG code: `32646`
- CRS: WGS 84 / UTM zone 46N
- `grid_mapping_name`: `transverse_mercator`
- Ellipsoid: WGS84
- UTM zone: `46`
- Central meridian: `93`
- Coordinate axes: projected X/easting and Y/northing in meters

The `xCoordinates` and `yCoordinates` arrays are projected coordinate axes,
not latitude/longitude arrays.

## Mask semantics observed in the file

The mask description says it is a packed 32-bit unsigned integer. It combines
water/subswath validity and anomaly information:

- bits 0–7: water and reference/secondary subswath encoding
- bits 8–15: secondary RSLC anomaly flags
- bits 16–23: reference RSLC anomaly flags
- bit 24: ionospheric phase-mask flag
- bits 25–31: reserved

The file reports `percentage_water=0.5573008435757318` and `valid_min=0`.
The mask must not be treated as a continuous measurement.

## Related observed GUNW fields

The same file also contains pixel-offset rasters under
`science/LSAR/GUNW/grids/frequencyA/pixelOffsets/HH/`:
`alongTrackOffset`, `slantRangeOffset`, and `correlationSurfacePeak`, each
with shape `(4257, 4338)`. The two offset fields were observed in meters;
`correlationSurfacePeak` was observed with units `1`.

## Limits of this inspection

This inspection did not establish the full scientific interpretation of every
mask bit, nor did it validate a displacement inversion from phase. The Phase 3
reader therefore validates structure and metadata only. Phase 4 must apply
the documented phase/coherence/mask workflow before reporting line-of-sight
displacement. If required fields are absent or incompatible, the application
must report: **Insufficient data for reliable analysis.**
