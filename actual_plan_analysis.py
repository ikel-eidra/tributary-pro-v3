"""
Actual Foundation Plan Analysis
Based on uploaded plan for 2-storey + roof deck

Extracted Data:
- Tie Beams: TB1 (200×350)
- Columns: Various (200×500, 400×400, etc.)
- Footings:
  - F1: 1700×1700×300mm
  - F2: 1400×1400×300mm
  - F3: 1200×1200×250mm
  - F4: 1000×1000×250mm
- Overall: ~10m × 12m
- 2 Storeys + Concrete Roof Deck
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math


@dataclass
class Column:
    """Column from the plan"""
    id: str
    width: float  # mm
    depth: float  # mm
    footing_type: str
    location: Tuple[float, float]  # Grid coordinates
    
    def area_mm2(self) -> float:
        return self.width * self.depth
    
    def area_m2(self) -> float:
        return self.area_mm2() / 1e6


@dataclass
class Footing:
    """Footing type from plan"""
    type_id: str
    width: float   # mm
    length: float  # mm
    depth: float   # mm
    
    def volume_m3(self) -> float:
        return self.width * self.length * self.depth / 1e9
    
    def concrete_volume(self) -> float:
        return self.volume_m3()


@dataclass
class TieBeam:
    """Tie beam from plan"""
    id: str
    width: float   # mm
    depth: float   # mm
    length: float  # m
    
    def volume_m3(self) -> float:
        return (self.width / 1000) * (self.depth / 1000) * self.length


# ========== ACTUAL PLAN DATA ==========

FOOTINGS = {
    "F1": Footing("F1", 1700, 1700, 300),
    "F2": Footing("F2", 1400, 1400, 300),
    "F3": Footing("F3", 1200, 1200, 250),
    "F4": Footing("F4", 1000, 1000, 250),
}

# Standard tie beam
TIE_BEAM = TieBeam("TB1", 250, 350, 1.0)  # 250×350 (corrected)

# From the plan, I can see the grid dimensions
GRID_X = [0, 1.2, 2.525, 3.925, 5.325, 7.225, 8.925, 10.525, 11.925, 13.125]  # Approximate
GRID_Y = [0, 1.2, 2.4, 3.8, 5.5, 7.0, 8.2]  # Approximate

# Column positions and types (CORRECTED based on user input)
# Most columns are 250×400
COLUMNS = [
    # Corner columns - F3 (1200×1200)
    Column("C1", 250, 400, "F3", (0, 0)),
    Column("C2", 250, 400, "F3", (13.125, 0)),
    Column("C3", 250, 400, "F3", (0, 8.2)),
    Column("C4", 250, 400, "F3", (13.125, 8.2)),
    
    # Edge columns - F2 (1400×1400)
    Column("C5", 250, 400, "F2", (3.925, 0)),
    Column("C6", 250, 400, "F2", (7.225, 0)),
    Column("C7", 250, 400, "F2", (3.925, 8.2)),
    Column("C8", 250, 400, "F2", (7.225, 8.2)),
    
    # Interior columns - F1 (1700×1700) - heaviest load
    Column("C9", 250, 400, "F1", (3.925, 3.8)),
    Column("C10", 250, 400, "F1", (7.225, 3.8)),
    
    # Small columns - F4 (1000×1000)
    Column("C11", 250, 400, "F4", (5.575, 8.2)),
    Column("C12", 250, 400, "F4", (5.575, 0)),
]


class PlanAnalyzer:
    """Analyze the actual foundation plan"""
    
    def __init__(
        self,
        num_storeys: int = 2,
        has_roof_deck: bool = True,
        fc: float = 21,  # MPa (current design)
        fy: float = 275,  # MPa
        dead_load: float = 5.0,  # kPa
        live_load: float = 2.0,  # kPa
        soil_bearing: float = 75,  # kPa (CLAY - conservative for shallow water table!)
    ):
        """
        SITE CONDITIONS - STA. MAGDALENA, LAGUNA:
        - Soil: Clay (matigas pero clay pa rin)
        - Water table: 2 ft (0.6m) - shallow!
        - Backfill: 1.5m compacted fill to raise 2m above road
        - Bearing capacity: 50-100 kPa for clay, use 75 kPa conservative
        
        IMPORTANT: Shallow water table reduces effective stress!
        Consider oversizing footings or using raft foundation.
        """
        self.num_storeys = num_storeys
        self.has_roof_deck = has_roof_deck
        self.fc = fc
        self.fy = fy
        self.dead_load = dead_load
        self.live_load = live_load
        self.soil_bearing = soil_bearing
        
        # Site-specific
        self.water_table_depth = 0.6  # m (2 ft)
        self.backfill_height = 1.5    # m
        self.fill_surcharge = 18 * self.backfill_height  # kN/m² from fill weight
        
        # Calculate building footprint (CORRECTED)
        # Main structure: 8m × 11.5m
        # Porch/Balcony: 4.9m × 2.5m
        self.main_length = 11.5  # m
        self.main_width = 8.0    # m
        self.porch_length = 4.9  # m
        self.porch_width = 2.5   # m
        
        self.main_area = self.main_length * self.main_width  # 92 m²
        self.porch_area = self.porch_length * self.porch_width  # 12.25 m²
        self.floor_area = self.main_area + self.porch_area  # 104.25 m²
        
        # For beam design
        self.length = self.main_length  # For calculations
        self.width = self.main_width
        
    def total_floors(self) -> int:
        """Total floor slabs including roof"""
        return self.num_storeys + (1 if self.has_roof_deck else 0)
    
    def floor_load_per_sqm(self) -> float:
        """Floor load per sqm (kPa)"""
        # Dead load includes slab self-weight
        slab_weight = 0.15 * 24  # 150mm slab × 24 kN/m³ = 3.6 kPa
        return self.dead_load + slab_weight + self.live_load
    
    def factored_load_per_sqm(self) -> float:
        """Factored floor load (kPa)"""
        slab_weight = 0.15 * 24
        DL = self.dead_load + slab_weight
        LL = self.live_load
        return 1.2 * DL + 1.6 * LL
    
    def total_building_load(self) -> float:
        """Total building load (kN)"""
        # Load from floors
        floor_load = self.factored_load_per_sqm() * self.floor_area * self.total_floors()
        
        # Wall weight (estimate)
        wall_height = 3.0 * self.num_storeys
        wall_length = 2 * (self.length + self.width)
        wall_weight = wall_length * wall_height * 2.5  # 2.5 kN/m² for CHB wall
        
        # Column/beam weight (estimate 10% of floor)
        frame_weight = floor_load * 0.10
        
        return floor_load + wall_weight * 1.2 + frame_weight
    
    def analyze_footings(self) -> Dict:
        """Check footing adequacy"""
        results = {}
        
        # Estimate load per column (simplified - equal distribution)
        num_columns = len(COLUMNS)
        avg_load = self.total_building_load() / num_columns
        
        # Interior columns carry more
        interior_factor = 1.5
        edge_factor = 1.0
        corner_factor = 0.6
        
        for col in COLUMNS:
            ftg = FOOTINGS[col.footing_type]
            
            # Determine load factor
            if col.footing_type == "F1":
                load = avg_load * interior_factor
            elif col.footing_type == "F2":
                load = avg_load * edge_factor
            else:
                load = avg_load * corner_factor
            
            # Check bearing
            ftg_area = (ftg.width / 1000) * (ftg.length / 1000)
            bearing_pressure = load / ftg_area
            bearing_ratio = bearing_pressure / self.soil_bearing
            
            results[col.id] = {
                "column_size": f"{col.width}×{col.depth}",
                "footing": col.footing_type,
                "load_kN": load,
                "bearing_pressure": bearing_pressure,
                "bearing_ratio": bearing_ratio,
                "status": "OK" if bearing_ratio <= 1.0 else "OVER",
            }
        
        return results
    
    def concrete_quantities(self) -> Dict:
        """Calculate concrete quantities"""
        # Footings
        ftg_vol = sum(FOOTINGS[c.footing_type].volume_m3() for c in COLUMNS)
        
        # Tie beams - estimate total length from grid
        tb_length = 2 * (self.length + self.width) + self.length * 2 + self.width * 4
        tb_vol = (TIE_BEAM.width/1000) * (TIE_BEAM.depth/1000) * tb_length
        
        # Ground floor slab (on fill)
        gf_slab_vol = self.floor_area * 0.10  # 100mm thick
        
        # Suspended slabs
        susp_slab_vol = self.floor_area * 0.15 * self.total_floors()
        
        # Columns per storey
        col_height = 3.0
        col_vol = sum(c.area_m2() * col_height for c in COLUMNS) * self.num_storeys
        
        # Beams per storey (estimate)
        beam_vol = tb_vol * self.num_storeys  # Similar to tie beams
        
        return {
            "footings_m3": ftg_vol,
            "tie_beams_m3": tb_vol,
            "ground_slab_m3": gf_slab_vol,
            "suspended_slabs_m3": susp_slab_vol,
            "columns_m3": col_vol,
            "beams_m3": beam_vol,
            "total_m3": ftg_vol + tb_vol + gf_slab_vol + susp_slab_vol + col_vol + beam_vol,
        }
    
    def cost_estimate_conventional(self) -> Dict:
        """Cost estimate with conventional construction"""
        vol = self.concrete_quantities()
        
        # Unit rates (PHP)
        concrete_rate = 4500  # per m³
        rebar_rate = 2500     # per m³ of concrete
        formwork_rate = 800   # per m² (slabs/beams)
        labor_rate = 2000     # per m³
        
        # Concrete cost
        concrete_cost = vol["total_m3"] * concrete_rate
        
        # Rebar (estimate 100kg per m³)
        rebar_cost = vol["total_m3"] * rebar_rate
        
        # Formwork (slabs + beams)
        formwork_area = self.floor_area * self.total_floors() + vol["beams_m3"] * 10
        formwork_cost = formwork_area * formwork_rate
        
        # Labor
        labor_cost = vol["total_m3"] * labor_rate
        
        # CHB walls
        wall_area = 2 * (self.length + self.width) * 3.0 * self.num_storeys * 0.6  # 60% solid
        chb_cost = wall_area * 450  # ₱450/m²
        
        return {
            "concrete": concrete_cost,
            "rebar": rebar_cost,
            "formwork": formwork_cost,
            "labor": labor_cost,
            "walls": chb_cost,
            "total": concrete_cost + rebar_cost + formwork_cost + labor_cost + chb_cost,
        }
    
    def cost_estimate_optimized(self) -> Dict:
        """Cost estimate with our optimized system"""
        vol = self.concrete_quantities()
        
        # HYBRID mix is 40% cheaper
        concrete_rate = 2700  # vs 4500
        rebar_rate = 2000     # slightly less rebar
        formwork_rate = 0     # NO FORMWORK for precast!
        labor_rate = 800      # 60% less labor
        
        # Reduce slab volume by 40% (hollow core)
        hollow_core_vol = vol["suspended_slabs_m3"] * 0.6
        other_vol = vol["footings_m3"] + vol["tie_beams_m3"] + vol["ground_slab_m3"] + vol["columns_m3"] + vol["beams_m3"]
        total_vol = hollow_core_vol + other_vol
        
        # Costs
        concrete_cost = total_vol * concrete_rate
        rebar_cost = total_vol * rebar_rate
        labor_cost = total_vol * labor_rate
        
        # Precast wall panels vs CHB
        wall_area = 2 * (self.length + self.width) * 3.0 * self.num_storeys * 0.6
        wall_cost = wall_area * 270  # ₱270/m² for our panels
        
        # Crane rental
        crane_cost = 15000 * 3  # 3 days
        
        return {
            "concrete": concrete_cost,
            "rebar": rebar_cost,
            "formwork": 0,
            "labor": labor_cost,
            "walls": wall_cost,
            "crane": crane_cost,
            "total": concrete_cost + rebar_cost + labor_cost + wall_cost + crane_cost,
        }


def analyze_plan():
    """Full analysis of the actual plan"""
    analyzer = PlanAnalyzer(
        num_storeys=2,
        has_roof_deck=True,
        fc=21,
        soil_bearing=100,
    )
    
    print("\n" + "="*70)
    print("📐 ACTUAL FOUNDATION PLAN ANALYSIS")
    print("="*70)
    
    print(f"\n🏠 BUILDING DATA:")
    print(f"   Footprint: {analyzer.length}m × {analyzer.width}m = {analyzer.floor_area:.0f} m²")
    print(f"   Storeys: {analyzer.num_storeys} + Roof Deck")
    print(f"   Total Floor Area: {analyzer.floor_area * analyzer.total_floors():.0f} m²")
    
    print(f"\n📊 LOADING:")
    print(f"   Floor load: {analyzer.floor_load_per_sqm():.1f} kPa")
    print(f"   Factored: {analyzer.factored_load_per_sqm():.1f} kPa")
    print(f"   Total building: {analyzer.total_building_load():.0f} kN")
    
    print(f"\n📦 CONCRETE QUANTITIES:")
    vol = analyzer.concrete_quantities()
    for key, value in vol.items():
        print(f"   {key}: {value:.1f} m³")
    
    print(f"\n💰 COST COMPARISON:")
    conv = analyzer.cost_estimate_conventional()
    opt = analyzer.cost_estimate_optimized()
    
    print(f"\n   CONVENTIONAL:")
    print(f"   Concrete:  ₱{conv['concrete']:,.0f}")
    print(f"   Rebar:     ₱{conv['rebar']:,.0f}")
    print(f"   Formwork:  ₱{conv['formwork']:,.0f}")
    print(f"   Labor:     ₱{conv['labor']:,.0f}")
    print(f"   Walls:     ₱{conv['walls']:,.0f}")
    print(f"   TOTAL:     ₱{conv['total']:,.0f}")
    
    print(f"\n   OPTIMIZED (Our System):")
    print(f"   Concrete:  ₱{opt['concrete']:,.0f} (HYBRID mix)")
    print(f"   Rebar:     ₱{opt['rebar']:,.0f}")
    print(f"   Formwork:  ₱{opt['formwork']:,.0f} (NONE - precast!)")
    print(f"   Labor:     ₱{opt['labor']:,.0f} (60% less)")
    print(f"   Walls:     ₱{opt['walls']:,.0f} (precast panels)")
    print(f"   Crane:     ₱{opt['crane']:,.0f}")
    print(f"   TOTAL:     ₱{opt['total']:,.0f}")
    
    savings = conv['total'] - opt['total']
    savings_pct = savings / conv['total'] * 100
    print(f"\n   🎉 SAVINGS: ₱{savings:,.0f} ({savings_pct:.0f}%)")
    
    return analyzer, vol, conv, opt


if __name__ == "__main__":
    analyze_plan()
