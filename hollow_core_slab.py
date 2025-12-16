"""
Prestressed Hollow Core Slab System
Lightweight, long-span floor/roof slabs

Key Features:
1. Hollow cores - 40-50% weight reduction
2. Prestressing - longer spans, thinner sections
3. Factory produced - consistent quality
4. No formwork on site - just crane and grout

Cost Optimization:
- Use HYBRID composite for lighter weight
- Optimize strand pattern for each span
- Reduce thickness where possible
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math
import numpy as np


# ========== MATERIAL COSTS (PHP) ==========

COSTS = {
    # Concrete per m³
    "normal_concrete": 4500,      # Standard ready-mix
    "high_strength": 6000,        # f'c = 40+ MPa for prestress
    "hybrid_composite": 3800,     # Our lightweight mix
    
    # Prestressing
    "strand_12.7mm_per_m": 120,   # 7-wire strand
    "strand_15.2mm_per_m": 180,
    "anchor_set": 800,            # Per anchor
    
    # Labor per m² of slab
    "casting_labor": 150,
    "strand_labor": 80,
    "erection_labor": 200,
    
    # Equipment
    "tensioning_jack_per_slab": 50,
    "crane_per_hour": 3500,
    "crane_panels_per_hour": 8,
}


@dataclass
class HollowCoreSection:
    """
    Hollow core slab cross-section design.
    """
    # Overall dimensions (mm)
    width: float = 1200       # Standard module width
    depth: float = 200        # Slab depth
    
    # Hollow cores
    n_cores: int = 6
    core_width: float = 150   # Oval core width
    core_height: float = 140  # Oval core height
    
    # Flanges (top and bottom)
    flange_thickness: float = 30  # mm
    
    # Web (walls between cores)
    web_thickness: float = 35     # mm
    
    # Prestressing
    n_strands: int = 6
    strand_diameter: float = 12.7  # mm
    strand_area: float = 100       # mm² per strand
    fpu: float = 1860              # Ultimate strength MPa
    fse: float = 1200              # Effective stress after losses MPa
    
    # Material
    fc: float = 45                 # Concrete strength MPa (prestress needs high)
    density_kg_m3: float = 1600    # Lightweight hybrid mix
    
    def gross_area(self) -> float:
        """Gross cross-section area (mm²)"""
        return self.width * self.depth
    
    def void_area(self) -> float:
        """Area of hollow cores (mm²) - approximate as ellipses"""
        return self.n_cores * math.pi * (self.core_width/2) * (self.core_height/2)
    
    def net_area(self) -> float:
        """Net concrete area (mm²)"""
        return self.gross_area() - self.void_area()
    
    def void_ratio(self) -> float:
        """Percentage of cross-section that is void"""
        return self.void_area() / self.gross_area()
    
    def weight_per_m(self) -> float:
        """Weight per linear meter (kg/m)"""
        return (self.net_area() / 1e6) * self.density_kg_m3
    
    def weight_per_sqm(self) -> float:
        """Weight per square meter (kg/m²)"""
        return self.weight_per_m() / (self.width / 1000)
    
    def moment_of_inertia(self) -> float:
        """Approximate I (mm⁴) for gross section"""
        # Simplified: I_gross - I_voids
        I_gross = self.width * self.depth**3 / 12
        # Cores as ellipses at mid-height
        # I_core = π/64 × a × b³ for ellipse
        I_each_core = math.pi * self.core_width * self.core_height**3 / 64
        I_cores = self.n_cores * I_each_core
        return max(I_gross - I_cores, I_gross * 0.4)  # At least 40% of gross
    
    def prestress_force(self) -> float:
        """Total prestress force (kN)"""
        total_area = self.n_strands * self.strand_area
        return total_area * self.fse / 1000
    
    def moment_capacity(self) -> float:
        """Approximate moment capacity (kN·m)"""
        # Simplified: M = Aps × fps × d
        d = self.depth - 40  # Effective depth
        fps = min(self.fpu, self.fse * 1.1)  # Stress at ultimate
        return self.n_strands * self.strand_area * fps * d / 1e6


# Standard hollow core sizes - OPTIMIZED for typical loads
STANDARD_SECTIONS = {
    "150mm": HollowCoreSection(
        depth=150, n_cores=5, core_width=130, core_height=90,
        flange_thickness=25, web_thickness=30,
        n_strands=4, strand_diameter=9.5, strand_area=55,  # Smaller strand
        density_kg_m3=1400,
    ),
    "200mm": HollowCoreSection(
        depth=200, n_cores=6, core_width=140, core_height=130,
        flange_thickness=30, web_thickness=30,
        n_strands=5, strand_diameter=12.7, strand_area=100,
        density_kg_m3=1400,
    ),
    "265mm": HollowCoreSection(
        depth=265, n_cores=6, core_width=150, core_height=185,
        flange_thickness=35, web_thickness=35,
        n_strands=6, strand_diameter=12.7, strand_area=100,
        density_kg_m3=1400,
    ),
    "320mm": HollowCoreSection(
        depth=320, n_cores=6, core_width=160, core_height=240,
        flange_thickness=35, web_thickness=35,
        n_strands=7, strand_diameter=12.7, strand_area=100,
        density_kg_m3=1400,
    ),
    "400mm": HollowCoreSection(
        depth=400, n_cores=5, core_width=180, core_height=320,
        flange_thickness=40, web_thickness=40,
        n_strands=8, strand_diameter=12.7, strand_area=100,
        density_kg_m3=1400,
    ),
}


@dataclass 
class HollowCoreSlab:
    """
    Complete hollow core slab unit.
    """
    section: HollowCoreSection
    length: float  # mm (span)
    
    def weight_kg(self) -> float:
        """Total slab weight (kg)"""
        return self.section.weight_per_m() * (self.length / 1000)
    
    def can_crane_lift(self, crane_kg: float = 8000) -> bool:
        """Check if typical crane can lift"""
        return self.weight_kg() <= crane_kg
    
    def deflection_check(self, live_load_kpa: float = 2.0) -> Dict:
        """Check deflection under service load"""
        L = self.length  # mm
        I = self.section.moment_of_inertia()
        E = 30000  # MPa for high strength concrete
        
        # Self-weight deflection
        w_self = self.section.weight_per_m() * 9.81 / 1000  # N/mm
        delta_self = 5 * w_self * L**4 / (384 * E * I)
        
        # Live load deflection 
        w_live = live_load_kpa * self.section.width  # N/mm
        delta_live = 5 * w_live * L**4 / (384 * E * I)
        
        # Limit: L/360 for live load
        limit = L / 360
        
        return {
            "self_weight_mm": delta_self,
            "live_load_mm": delta_live,
            "limit_mm": limit,
            "passes": delta_live <= limit,
        }


class HollowCoreDesigner:
    """
    Design optimal hollow core slab for given span and load.
    """
    
    def __init__(
        self,
        span_m: float,
        live_load_kpa: float = 2.0,
        use_composite: bool = True,  # Use our lightweight mix
    ):
        self.span_m = span_m
        self.span_mm = span_m * 1000
        self.live_load = live_load_kpa
        self.use_composite = use_composite
    
    def select_section(self) -> HollowCoreSection:
        """Select thinnest section that works"""
        # Rule of thumb: depth ≈ span/35 for hollow core
        min_depth = self.span_mm / 35
        
        for name, section in STANDARD_SECTIONS.items():
            if section.depth >= min_depth:
                # Modify for composite if requested
                if self.use_composite:
                    section.density_kg_m3 = 1400  # Our HYBRID mix
                    section.fc = 35  # Slightly lower, still works
                
                # Verify deflection
                slab = HollowCoreSlab(section, self.span_mm)
                check = slab.deflection_check(self.live_load)
                
                if check["passes"]:
                    return section
        
        # If none work, return largest
        return STANDARD_SECTIONS["400mm"]
    
    def cost_estimate(self, section: HollowCoreSection, area_sqm: float) -> Dict:
        """Estimate costs"""
        
        # Concrete cost
        volume_per_sqm = section.net_area() / 1e6  # m³ per m² of slab
        total_concrete_m3 = volume_per_sqm * area_sqm
        
        if self.use_composite:
            concrete_cost = total_concrete_m3 * COSTS["hybrid_composite"]
        else:
            concrete_cost = total_concrete_m3 * COSTS["high_strength"]
        
        # Strand cost
        strand_length = self.span_m + 0.5  # Extra for anchors
        strands_per_width = section.n_strands * (1200 / section.width)
        n_slabs = area_sqm / (section.width/1000 * self.span_m)
        total_strand_m = n_slabs * strands_per_width * strand_length
        
        if section.strand_diameter == 12.7:
            strand_cost = total_strand_m * COSTS["strand_12.7mm_per_m"]
        else:
            strand_cost = total_strand_m * COSTS["strand_15.2mm_per_m"]
        
        # Anchor cost
        anchor_cost = n_slabs * strands_per_width * 2 * COSTS["anchor_set"]
        
        # Labor
        casting_cost = area_sqm * COSTS["casting_labor"]
        strand_cost_labor = area_sqm * COSTS["strand_labor"]
        erection_cost = area_sqm * COSTS["erection_labor"]
        
        # Crane
        crane_hours = math.ceil(n_slabs / COSTS["crane_panels_per_hour"])
        crane_cost = crane_hours * COSTS["crane_per_hour"]
        
        total = (concrete_cost + strand_cost + anchor_cost + 
                 casting_cost + strand_cost_labor + erection_cost + crane_cost)
        
        return {
            "concrete": concrete_cost,
            "strand": strand_cost,
            "anchors": anchor_cost,
            "labor_casting": casting_cost,
            "labor_strand": strand_cost_labor,
            "labor_erection": erection_cost,
            "crane": crane_cost,
            "total": total,
            "per_sqm": total / area_sqm,
        }
    
    def design(self, area_sqm: float = 100) -> Dict:
        """Full design and cost estimate"""
        section = self.select_section()
        slab = HollowCoreSlab(section, self.span_mm)
        defl = slab.deflection_check(self.live_load)
        cost = self.cost_estimate(section, area_sqm)
        
        return {
            "section": section,
            "slab": slab,
            "deflection": defl,
            "cost": cost,
        }


def design_hollow_core(
    span_m: float,
    area_sqm: float = 100,
    live_load_kpa: float = 2.0,
    use_composite: bool = True,
) -> Dict:
    """
    Design prestressed hollow core slab system.
    """
    designer = HollowCoreDesigner(span_m, live_load_kpa, use_composite)
    result = designer.design(area_sqm)
    
    section = result["section"]
    slab = result["slab"]
    cost = result["cost"]
    
    print("\n" + "="*60)
    print("🏗️ PRESTRESSED HOLLOW CORE SLAB DESIGN")
    print("="*60)
    print(f"\n📐 Design Parameters:")
    print(f"   Span: {span_m}m")
    print(f"   Area: {area_sqm}m²")
    print(f"   Live load: {live_load_kpa} kPa")
    print(f"   Mix: {'HYBRID Composite' if use_composite else 'Normal High-Strength'}")
    
    print(f"\n📦 SELECTED SECTION: {section.depth}mm deep")
    print(f"   Width: {section.width}mm")
    print(f"   Void ratio: {section.void_ratio()*100:.0f}%")
    print(f"   Weight: {section.weight_per_sqm():.0f}kg/m²")
    
    print(f"\n🔩 PRESTRESSING:")
    print(f"   Strands: {section.n_strands} × Ø{section.strand_diameter}mm")
    print(f"   Force: {section.prestress_force():.0f}kN")
    
    print(f"\n📊 PERFORMANCE:")
    print(f"   Slab weight: {slab.weight_kg():.0f}kg")
    print(f"   Crane lift: {'✓ OK' if slab.can_crane_lift() else '✗ Need larger crane'}")
    print(f"   Deflection: {'✓ PASS' if result['deflection']['passes'] else '✗ FAIL'}")
    
    # Compare normal vs composite
    print(f"\n💰 COST BREAKDOWN (for {area_sqm}m²):")
    print(f"   Concrete:  ₱{cost['concrete']:,.0f}")
    print(f"   Strands:   ₱{cost['strand']:,.0f}")
    print(f"   Labor:     ₱{cost['labor_casting'] + cost['labor_strand'] + cost['labor_erection']:,.0f}")
    print(f"   Crane:     ₱{cost['crane']:,.0f}")
    print(f"   ─────────────────────")
    print(f"   TOTAL:     ₱{cost['total']:,.0f}")
    print(f"   Per m²:    ₱{cost['per_sqm']:,.0f}/m²")
    
    # Compare to solid slab
    solid_weight = (span_m / 28) * 2400  # Rule of thumb: d = L/28 for solid
    solid_cost = (span_m / 28) * area_sqm * 6000  # ₱6000/m³ concrete + rebar
    
    weight_savings = (solid_weight - section.weight_per_sqm()) / solid_weight * 100
    cost_comparison = cost['per_sqm'] / (solid_cost / area_sqm) * 100
    
    print(f"\n📈 VS SOLID SLAB:")
    print(f"   Weight: {weight_savings:.0f}% lighter!")
    print(f"   Cost: {100 - cost_comparison:.0f}% savings!")
    
    return result


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SCENARIO 1: 6m span residential floor")
    print("="*60)
    result1 = design_hollow_core(span_m=6, area_sqm=50, use_composite=True)
    
    print("\n" + "="*60)
    print("SCENARIO 2: 8m span commercial floor")
    print("="*60)
    result2 = design_hollow_core(span_m=8, area_sqm=100, use_composite=True)
    
    print("\n" + "="*60)
    print("SCENARIO 3: 10m span long roof")
    print("="*60)
    result3 = design_hollow_core(span_m=10, area_sqm=80, live_load_kpa=1.0, use_composite=True)
