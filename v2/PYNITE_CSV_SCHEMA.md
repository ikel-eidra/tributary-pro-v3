# 📊 PyNite Frame Builder - CSV Schema

**Purpose:** Bridge from Tributary Pro → PyNite FEA
**Date:** December 15, 2025
**From:** Lum

---

## 1. GRIDS.csv

Master coordinates for grid axes.

| Column | Type | Description |
|--------|------|-------------|
| axis_id | text | e.g. `X1`, `X2`, `Y1`, `Y2` |
| direction | text | `X` or `Y` |
| coord_m | number | global coordinate in meters |

**Example:**
```csv
axis_id,direction,coord_m
X1,X,0.0
X2,X,4.0
X3,X,8.0
Y1,Y,0.0
Y2,Y,5.0
Y3,Y,10.0
```

---

## 2. FLOORS.csv

Vertical levels & slab loads per floor.

| Column | Type | Description |
|--------|------|-------------|
| floor_id | text | `F1`, `F2`, `F3`, `RF` |
| z_elev_m | number | elevation of slab |
| slab_thk_m | number | slab thickness (m) |
| DL_super_kPa | number | superimposed dead load |
| LL_kPa | number | live load |
| occupancy_class | text | e.g. `Residential`, `Office` |

**Example:**
```csv
floor_id,z_elev_m,slab_thk_m,DL_super_kPa,LL_kPa,occupancy_class
F1,3.0,0.15,2.0,2.0,Residential
F2,6.0,0.15,2.0,2.0,Residential
F3,9.0,0.15,2.0,2.0,Residential
RF,12.0,0.12,1.5,0.75,Roof
```

---

## 3. COLUMNS.csv

Columns per grid intersection.

| Column | Type | Description |
|--------|------|-------------|
| col_id | text | e.g. `C1`, `B2` |
| grid_x | text | axis_id in X |
| grid_y | text | axis_id in Y |
| base_floor | text | e.g. `Foundation` |
| top_floor | text | highest floor supported |
| b_mm | number | column width |
| h_mm | number | column depth |
| fc_MPa | number | concrete strength (optional) |
| fy_MPa | number | steel strength (optional) |

**Example:**
```csv
col_id,grid_x,grid_y,base_floor,top_floor,b_mm,h_mm,fc_MPa,fy_MPa
C1,X1,Y1,Base,RF,250,250,25,415
C2,X2,Y1,Base,RF,250,250,25,415
```

---

## 4. BEAMS.csv

Beams per floor between grid intersections.

| Column | Type | Description |
|--------|------|-------------|
| beam_id | text | `B-F2-X1-X2-Y1` etc. |
| floor_id | text | which floor |
| from_grid_x | text | start X axis_id |
| from_grid_y | text | start Y axis_id |
| to_grid_x | text | end X axis_id |
| to_grid_y | text | end Y axis_id |
| b_mm | number | beam width |
| h_mm | number | beam depth |
| fc_MPa | number | concrete strength (opt) |
| fy_MPa | number | steel strength (opt) |
| slab_zone | text | `interior`, `edge`, `corner` |

---

## 5. TRIBUTARY_REGIONS.csv (from v2.1)

Export from Tributary Pro for load application.

| Column | Type | Description |
|--------|------|-------------|
| beam_id | text | beam this region belongs to |
| direction | text | X or Y |
| floor_id | text | floor level |
| region_id | text | unique region ID |
| slab_id | text | source slab |
| area_m2 | number | tributary area |
| centroid_x_m | number | centroid X coordinate |
| centroid_y_m | number | centroid Y coordinate |
| tributary_width_m | number | effective width |
| w_kN_per_m | number | factored line load |

---

## 6. PyNite Builder Skeleton

```python
from Pynite import FEModel3D
import csv

def load_grids(path):
    grids_x, grids_y = {}, {}
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['direction'] == 'X':
                grids_x[row['axis_id']] = float(row['coord_m'])
            else:
                grids_y[row['axis_id']] = float(row['coord_m'])
    return grids_x, grids_y

def build_model(grids_csv, floors_csv, cols_csv, beams_csv):
    grids_x, grids_y = load_grids(grids_csv)
    model = FEModel3D()
    # Add nodes, columns, beams...
    return model
```

---

**This schema connects Tributary Pro → PyNite FEA!** 🔗
