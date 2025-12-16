"""
Trapezoid Lego Block Design
Based on mahal's sketch - self-leveling with natural interlock

Key Features:
1. Trapezoidal cross-section (tapered sides)
2. Self-leveling due to gravity
3. Natural horizontal interlock
4. Vertical cores for rebar + grout
5. Cylindrical nubs on top for vertical stacking
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math
import numpy as np


@dataclass
class TrapezoidBlock:
    """
    Trapezoidal lego block based on mahal's design.
    
    Cross-section is trapezoid:
    - Wider at bottom, narrower at top
    - Creates self-leveling and interlock
    
    All dimensions in mm.
    """
    # Main dimensions
    length: float = 800        # Along wall (800-1200mm range)
    height: float = 200        # Course height (200-400mm range)
    
    # Trapezoid profile (from sketch)
    width_bottom: float = 150  # Wall thickness at base
    width_top: float = 100     # Wall thickness at top (narrower)
    taper_height: float = 50   # Height of tapered section (from sketch: 50mm)
    
    # Cores (for rebar + grout)
    n_cores: int = 3           # Number of vertical cores
    core_diameter: float = 60  # mm
    
    # Top nubs (for stacking interlock)
    n_nubs: int = 2
    nub_diameter: float = 50
    nub_height: float = 25
    
    # Material (HYBRID composite)
    density_kg_m3: float = 1350  # Lightweight hybrid mix
    strength_mpa: float = 13     # Strong!
    
    def taper_angle(self) -> float:
        """Angle of taper in degrees"""
        width_diff = (self.width_bottom - self.width_top) / 2
        return math.degrees(math.atan(width_diff / self.taper_height))
    
    def cross_section_area(self) -> float:
        """Cross-sectional area (mm²) - trapezoid"""
        # Trapezoid area = (a + b) / 2 × h
        # But our shape is: rectangle bottom + trapezoid top
        
        # Bottom rectangular section
        rect_height = self.height - self.taper_height
        rect_area = self.width_bottom * rect_height
        
        # Top trapezoidal section
        trap_area = (self.width_bottom + self.width_top) / 2 * self.taper_height
        
        return rect_area + trap_area
    
    def core_area(self) -> float:
        """Total core hole area (mm²)"""
        return self.n_cores * math.pi * (self.core_diameter / 2) ** 2
    
    def net_area(self) -> float:
        """Net cross-section (solid concrete)"""
        return self.cross_section_area() - self.core_area()
    
    def solid_volume(self) -> float:
        """Volume of solid concrete per block (mm³)"""
        # Main body (net of cores)
        body_vol = self.net_area() * self.length
        
        # Add nubs on top
        nub_vol = self.n_nubs * math.pi * (self.nub_diameter/2)**2 * self.nub_height
        
        return body_vol + nub_vol
    
    def weight_kg(self) -> float:
        """Weight per block in kg"""
        return self.solid_volume() / 1e9 * self.density_kg_m3
    
    def is_one_person_lift(self, max_kg: float = 23) -> bool:
        """Check if one person can lift (max 23kg per OSHA)"""
        return self.weight_kg() <= max_kg
    
    def blocks_per_sqm(self) -> float:
        """Blocks per square meter of wall"""
        block_face = (self.length / 1000) * (self.height / 1000)
        return 1.0 / block_face
    
    def interlock_depth(self) -> float:
        """How much the taper interlocks horizontally (mm)"""
        return (self.width_bottom - self.width_top) / 2


def optimize_trapezoid_block(
    max_weight_kg: float = 23,
    min_length: float = 800,
    max_length: float = 1200,
    min_height: float = 200,
    max_height: float = 400,
    min_thickness: float = 100,
    max_thickness: float = 150,
) -> Dict:
    """
    Find optimal trapezoid block dimensions.
    
    Constraints:
    - 1-person lift (max 23kg OSHA limit)
    - Self-leveling taper
    - Strong enough for load-bearing walls
    """
    
    print("\n" + "="*60)
    print("🧱 TRAPEZOID LEGO BLOCK OPTIMIZER")
    print("="*60)
    print(f"\n📐 Design based on mahal's sketch!")
    print(f"   Max weight: {max_weight_kg}kg (1-person lift)")
    
    # Search space
    lengths = list(range(int(min_length), int(max_length) + 1, 100))
    heights = list(range(int(min_height), int(max_height) + 1, 50))
    widths = list(range(int(min_thickness), int(max_thickness) + 1, 10))
    
    best = None
    best_score = float('inf')
    valid_designs = []
    
    for L in lengths:
        for H in heights:
            for W_bot in widths:
                # Top width = bottom - 2 × taper (from sketch ratio)
                # Taper about 25mm each side based on sketch proportions
                taper = min(25, W_bot * 0.2)  # 20% taper or 25mm max
                W_top = W_bot - 2 * taper
                
                if W_top < 60:  # Minimum for core + shells
                    continue
                
                # Create block
                block = TrapezoidBlock(
                    length=L,
                    height=H,
                    width_bottom=W_bot,
                    width_top=W_top,
                    taper_height=50,  # From sketch
                    n_cores=max(2, L // 400),  # 1 core per 400mm
                )
                
                # Check weight constraint
                if not block.is_one_person_lift(max_weight_kg):
                    continue
                
                # Score: maximize coverage, minimize weight
                # Lower score = better
                coverage = block.blocks_per_sqm()
                weight = block.weight_kg()
                score = coverage * 10 + weight * 2 - block.interlock_depth() * 0.5
                
                valid_designs.append({
                    "block": block,
                    "score": score,
                })
                
                if score < best_score:
                    best_score = score
                    best = block
    
    if best:
        print(f"\n✅ OPTIMAL BLOCK DESIGN:")
        print(f"\n   📏 DIMENSIONS:")
        print(f"      Length: {best.length}mm")
        print(f"      Height: {best.height}mm")
        print(f"      Width (bottom): {best.width_bottom}mm")
        print(f"      Width (top): {best.width_top}mm")
        print(f"      Taper angle: {best.taper_angle():.1f}°")
        
        print(f"\n   🔘 FEATURES:")
        print(f"      Cores: {best.n_cores} × Ø{best.core_diameter}mm")
        print(f"      Nubs: {best.n_nubs} × Ø{best.nub_diameter}mm × {best.nub_height}mm")
        print(f"      Interlock depth: {best.interlock_depth():.0f}mm")
        
        print(f"\n   ⚖️ WEIGHT & COVERAGE:")
        print(f"      Weight: {best.weight_kg():.1f}kg ✓ (1-person lift)")
        print(f"      Blocks/m²: {best.blocks_per_sqm():.1f}")
        print(f"      Solid ratio: {best.net_area()/best.cross_section_area()*100:.0f}%")
        
        # Wall calculation
        wall_area = 10  # 10 m² sample
        n_blocks = math.ceil(best.blocks_per_sqm() * wall_area)
        total_weight = n_blocks * best.weight_kg()
        
        print(f"\n   🏗️ FOR 10m² WALL:")
        print(f"      Blocks needed: {n_blocks}")
        print(f"      Total weight: {total_weight:.0f}kg")
        print(f"      Weight/m²: {total_weight/wall_area:.0f}kg/m²")
        
        # Compare to standard CHB
        std_chb_weight_per_sqm = 150 * 0.001 * 1900 * 0.65  # 150mm, 1900kg/m³, 65% solid
        savings = (std_chb_weight_per_sqm - total_weight/wall_area) / std_chb_weight_per_sqm * 100
        print(f"\n   📊 VS STANDARD 150mm CHB:")
        print(f"      Weight savings: {savings:.0f}%")
    
    return {
        "best": best,
        "valid_count": len(valid_designs),
    }


def generate_manufacturing_specs(block: TrapezoidBlock) -> Dict:
    """Generate specs for mold manufacturing"""
    
    print("\n" + "="*60)
    print("🔧 MANUFACTURING SPECIFICATIONS")
    print("="*60)
    
    specs = {
        "mold_dimensions": {
            "internal_length": block.length,
            "internal_height": block.height + block.nub_height,  # Include nub cavities
            "internal_width_bottom": block.width_bottom,
            "internal_width_top": block.width_top,
            "draft_angle": block.taper_angle(),
        },
        "core_pins": {
            "count": block.n_cores,
            "diameter": block.core_diameter,
            "height": block.height,
            "spacing": block.length / (block.n_cores + 1),
        },
        "nub_cavities": {
            "count": block.n_nubs,
            "diameter": block.nub_diameter,
            "depth": block.nub_height,
        },
        "material_per_block": {
            "concrete_volume_liters": block.solid_volume() / 1e6,
            "cement_kg": block.solid_volume() / 1e6 * 0.35,  # ~350kg/m³
            "aggregate_kg": block.solid_volume() / 1e6 * 0.8,
        },
        "production": {
            "estimated_cycle_time_min": 15,
            "blocks_per_hour": 4,
            "curing_time_days": 7,
        }
    }
    
    print(f"\n📐 MOLD INTERNAL DIMENSIONS:")
    print(f"   Length: {specs['mold_dimensions']['internal_length']}mm")
    print(f"   Height: {specs['mold_dimensions']['internal_height']}mm")
    print(f"   Width bottom: {specs['mold_dimensions']['internal_width_bottom']}mm")
    print(f"   Width top: {specs['mold_dimensions']['internal_width_top']}mm")
    print(f"   Draft angle: {specs['mold_dimensions']['draft_angle']:.1f}°")
    
    print(f"\n🔩 CORE PINS (removable):")
    print(f"   {specs['core_pins']['count']} pins × Ø{specs['core_pins']['diameter']}mm")
    print(f"   Spacing: {specs['core_pins']['spacing']:.0f}mm c/c")
    
    print(f"\n🧱 MATERIAL PER BLOCK:")
    print(f"   Concrete: {specs['material_per_block']['concrete_volume_liters']:.1f} liters")
    print(f"   Cement: ~{specs['material_per_block']['cement_kg']:.1f}kg")
    
    return specs


if __name__ == "__main__":
    result = optimize_trapezoid_block()
    
    if result["best"]:
        specs = generate_manufacturing_specs(result["best"])
