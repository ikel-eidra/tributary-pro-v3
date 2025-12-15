# 🔧 Lum's Refined v2.0 Specification

**Reviewed by:** Lum
**Date:** December 15, 2025
**Status:** APPROVED with refinements

---

## ✅ VERDICT: Core is Correct

- v1.0 bug: slab → column direct ❌
- v2.0 fix: SLAB → BEAM (TA) → COLUMN (reactions) ✅

---

## 📐 REFINEMENTS TO APPLY

### (a) Factored Load Formula - CLEARER LABELS

```javascript
// DL_super: superimposed dead load (kPa) - finishes, partitions, ceiling
//           Does NOT include slab self-weight
// slab_weight: γ_conc * t_slab = 24 * (thickness_mm / 1000) kN/m²
// LL: live load (kPa)
// p_u = 1.2 * (DL_super + slab_weight) + 1.6 * LL

const DL_super = parseFloat(document.getElementById('deadLoad').value) || 5.0;
const LL = parseFloat(document.getElementById('liveLoad').value) || 2.0;
const slab_thickness_m = slabThickness / 1000;
const slab_weight = 24 * slab_thickness_m;  // kN/m² = kPa
const p_u = 1.2 * (DL_super + slab_weight) + 1.6 * LL;
```

---

### (b) Reaction Formulas - WITH ASCII SKETCHES

#### 1. Uniform Load (w kN/m)
```
    w w w w w w w w w (uniform)
    ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓
    ═══════════════════
    △                 △
   R_A               R_B
   
   Resultant = w × L
   R_A = R_B = w × L / 2
```

#### 2. Symmetric Triangular (peak at midspan)
```
           /\
          /  \
         /    \
        /      \
       /   w    \
      /   max    \
    ═══════════════
    △             △
   R_A           R_B
   
   Resultant = w_max × L / 2
   R_A = R_B = w_max × L / 4
```

#### 3. Trapezoidal Load (split method)
```
   w2 ___________
     |          /|
     |         / |
   w1|________/  | uniform + triangular
     |________|←→| Δw = |w2 - w1|
    ═════════════
    △           △
   R_A         R_B
   
   Split into:
   - Uniform: w_uniform = min(w1, w2)
   - Triangular: Δw = |w2 - w1|
   
   R_A = R_B = (w_uniform × L / 2) + (Δw × L / 4)
```

---

### (c) Double Counting Prevention - SEPARATE TA MAPS

```javascript
// WRONG: Same area counted for beam AND column
// CORRECT: Maintain TWO distinct maps

const TA_for_beams = {};   // panel_id → { beam_id: fraction_of_area }
const TA_for_columns = {}; // panel_id → { col_id: fraction_of_area }

// Each panel's area is PARTITIONED, not cloned
// Validation:
// sum(TA_beams) ≈ total_slab_area
// sum(TA_columns) ≈ total_slab_area
// But they come from NON-OVERLAPPING fractions
```

---

### (d) Multi-Floor Stacking - SUM, DON'T MULTIPLY

```javascript
// WRONG (v1.0):
col.totalLoad = col.loadPerFloor * (storeys + 1);

// CORRECT (v2.0):
column.loads_by_floor = {};  // { floor_id: P_floor }
column.loads_by_floor[floor_id] = P_floor;  // per floor

// Then aggregate:
column.total_service = Object.values(column.loads_by_floor).reduce((a, b) => a + b, 0);
column.total_factored = Object.values(column.loads_by_floor_factored).reduce((a, b) => a + b, 0);
```

---

## 📋 REFINED v2.0 IMPLEMENTATION CHECKLIST

### 1. State Setup
```javascript
const state = {
  xSpans: [4, 4, 4],      // m
  ySpans: [5, 5],          // m
  floors: 3,
  DL_super: 5.0,           // kPa (EXCLUDING slab weight)
  LL: 2.0,                 // kPa
  slabThickness: 150,      // mm
  columns: [],
  beams: [],
  slabs: []
};
```

### 2. Grid Generation
```javascript
// Build absolute coordinates from spans
let x = [0];
for (let span of state.xSpans) {
  x.push(x[x.length - 1] + span);
}
// Same for y
```

### 3. Slab Panel Generation
```javascript
// Every (i, j) → rectangle
// corners (xi, yj), (xi+1, yj), (xi+1, yj+1), (xi, yj+1)
// area = Δx * Δy
```

### 4. Tributary Distribution (Simple 2-Way v2.0)
```javascript
// Corner columns: ¼ of each touching panel
// Edge columns: ½ on edge side
// Interior columns: ¼ from each of 4 panels

// Beams:
// Interior: w_t = ½ panel width each side
// Edge: w_t = full slab width on one side
```

### 5. Loads
```javascript
const slab_weight = 24 * (state.slabThickness / 1000);
const p_u = 1.2 * (state.DL_super + slab_weight) + 1.6 * state.LL;
// Per panel: w_panel = p_u * A_panel
```

### 6. Beam Loads & Reactions
```javascript
// Convert panel contribution to line load
// For v2.0: treat as EQUIVALENT UNIFORM LOAD
const w_eq = p_u * tributary_width;
const R_left = w_eq * L / 2;
const R_right = w_eq * L / 2;
```

### 7. Column Loads
```javascript
// Sum all reactions from beams framing into column
// Store per floor
// Then sum across floors for total
```

### 8. Visualization
- Grid lines
- Columns as dots/squares
- Beams as lines
- Labels for loads

### 9. Validation
- total_slab_area ≈ sum(TA_beam)
- symmetric test frame check
- manual textbook example match

---

## 🎯 v2.0 BOUNDARIES (Keep It Boring)

### ✅ INCLUDE:
- Regular 2-way slabs
- Uniform equivalent loads
- Clean JSON I/O
- Strict area accounting

### ❌ EXCLUDE (Future):
- Triangular/trapezoidal curves (v2.1+)
- One-way slabs (v2.2)
- Voronoi (v3.0)
- FEA (v4.0)

---

## 🧪 NEXT: Design Test Frame

Lum suggests designing ONE calibrated test frame:
- Exact spans, DL, LL
- Expected answers calculated manually
- Kira must match these numbers for v2.0 approval

---

**"Keep it simple and boring - then it becomes trusted."** - Lum 🔧
