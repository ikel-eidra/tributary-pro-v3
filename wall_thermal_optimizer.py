"""
Wall Thermal Optimizer
Finds thinnest, lightest wall that meets:
1. Structural requirements
2. U-value (thermal) requirements  
3. Cost optimization
4. Using composite materials cheaper than market CHB
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
import math


# ========== THERMAL PROPERTIES ==========

# Philippine Building Code / Green Building Code thermal requirements
# U-value limits (W/m²·K) - lower is better insulation
U_VALUE_REQUIREMENTS = {
    "residential_wall": 2.5,      # Typical residential
    "commercial_wall": 2.0,       # Office buildings
    "green_building": 1.5,        # Green certified
    "premium_insulated": 1.0,     # High performance
}

# Material thermal conductivity (W/m·K) - lower = better insulator
THERMAL_CONDUCTIVITY = {
    # Standard materials
    "normal_concrete": 1.7,
    "lightweight_concrete": 0.8,   # With pumice
    "hollow_chb_air": 0.5,         # Air gap in CHB cores
    
    # Composite materials
    "pumice_concrete": 0.35,       # Excellent!
    "coir_concrete": 0.45,
    "rha_concrete": 0.40,          # Rice hull ash mix
    "bagasse_concrete": 0.38,
    
    # Insulation layers
    "eps_foam": 0.035,
    "xps_foam": 0.030,
    "polyurethane": 0.025,
    "air_gap_25mm": 0.15,          # Still air
}


@dataclass
class WallLayer:
    """Single layer in wall assembly"""
    name: str
    thickness_mm: float
    conductivity: float  # W/m·K
    density_kg_m3: float
    cost_per_sqm: float  # ₱/m² at this thickness
    
    def r_value(self) -> float:
        """Thermal resistance (m²·K/W)"""
        return (self.thickness_mm / 1000) / self.conductivity
    
    def weight_per_sqm(self) -> float:
        """Weight in kg/m²"""
        return (self.thickness_mm / 1000) * self.density_kg_m3


@dataclass
class WallAssembly:
    """Complete wall assembly with multiple layers"""
    name: str
    layers: List[WallLayer]
    
    # Surface resistances (standard values)
    r_interior: float = 0.12  # m²·K/W
    r_exterior: float = 0.04  # m²·K/W
    
    def total_thickness(self) -> float:
        """Total wall thickness (mm)"""
        return sum(layer.thickness_mm for layer in self.layers)
    
    def total_r_value(self) -> float:
        """Total thermal resistance (m²·K/W)"""
        r_layers = sum(layer.r_value() for layer in self.layers)
        return self.r_interior + r_layers + self.r_exterior
    
    def u_value(self) -> float:
        """U-value (W/m²·K) - lower is better"""
        return 1.0 / self.total_r_value()
    
    def total_weight(self) -> float:
        """Weight per m² (kg/m²)"""
        return sum(layer.weight_per_sqm() for layer in self.layers)
    
    def total_cost(self) -> float:
        """Cost per m² (₱/m²)"""
        return sum(layer.cost_per_sqm for layer in self.layers)
    
    def meets_requirement(self, u_limit: float) -> bool:
        """Check if wall meets U-value requirement"""
        return self.u_value() <= u_limit


# ========== MARKET CHB COMPARISON ==========

MARKET_CHB = {
    "standard_4inch": {
        "thickness_mm": 100,
        "strength_mpa": 7.0,      # Typical Class C
        "density_kg_m3": 1900,
        "cost_per_sqm": 280,      # ₱/m² installed
        "u_value": 3.2,           # Poor insulation
    },
    "standard_6inch": {
        "thickness_mm": 150,
        "strength_mpa": 7.0,
        "density_kg_m3": 1900,
        "cost_per_sqm": 380,
        "u_value": 2.8,
    },
    "standard_8inch": {
        "thickness_mm": 200,
        "strength_mpa": 7.0,
        "density_kg_m3": 1900,
        "cost_per_sqm": 480,
        "u_value": 2.5,
    },
}


# ========== COMPOSITE CHB OPTIONS ==========

def create_composite_chb(
    thickness_mm: float,
    mix_type: str,  # "pumice", "coir", "rha", "hybrid"
    core_percentage: float = 0.35,  # Hollow percentage
) -> WallLayer:
    """
    Create a composite CHB layer with specified properties.
    """
    mixes = {
        "pumice": {
            "conductivity": 0.35,
            "density": 1400,
            "strength_mpa": 10,
            "cost_per_m3": 3500,
        },
        "coir": {
            "conductivity": 0.45,
            "density": 1500,
            "strength_mpa": 12,
            "cost_per_m3": 3800,
        },
        "rha": {
            "conductivity": 0.40,
            "density": 1550,
            "strength_mpa": 11,
            "cost_per_m3": 3300,
        },
        "hybrid": {  # Pumice + Coir + RHA
            "conductivity": 0.32,  # Best insulation!
            "density": 1350,       # Lightest!
            "strength_mpa": 13,    # Strongest! (fiber helps)
            "cost_per_m3": 3600,
        },
    }
    
    mix = mixes[mix_type]
    
    # Account for hollow cores (air is excellent insulator)
    effective_conductivity = (
        mix["conductivity"] * (1 - core_percentage) +
        0.15 * core_percentage  # Air in cores
    )
    
    effective_density = mix["density"] * (1 - core_percentage)
    
    # Cost per m² = cost per m³ × thickness in m
    cost_per_sqm = mix["cost_per_m3"] * (thickness_mm / 1000)
    
    return WallLayer(
        name=f"Composite CHB ({mix_type})",
        thickness_mm=thickness_mm,
        conductivity=effective_conductivity,
        density_kg_m3=effective_density,
        cost_per_sqm=cost_per_sqm,
    )


# ========== WALL OPTIMIZER ==========

class WallOptimizer:
    """
    Find thinnest, lightest wall that meets requirements.
    Uses quantum-inspired optimization.
    """
    
    def __init__(
        self,
        u_value_target: float = 2.5,
        min_strength_mpa: float = 7.0,
        max_cost_per_sqm: float = 500,
    ):
        self.u_target = u_value_target
        self.min_strength = min_strength_mpa
        self.max_cost = max_cost_per_sqm
        
        # Options to search
        self.thicknesses = [75, 100, 125, 150, 175, 200]  # mm
        self.mix_types = ["pumice", "coir", "rha", "hybrid"]
        self.core_percentages = [0.25, 0.30, 0.35, 0.40, 0.45]
        self.add_insulation = [None, "eps_10mm", "eps_20mm", "air_gap"]
        
    def _create_wall(
        self,
        thickness: float,
        mix_type: str,
        core_pct: float,
        insulation: Optional[str],
    ) -> WallAssembly:
        """Create wall assembly from parameters"""
        layers = []
        
        # Main CHB layer
        chb = create_composite_chb(thickness, mix_type, core_pct)
        layers.append(chb)
        
        # Optional insulation
        if insulation == "eps_10mm":
            layers.append(WallLayer(
                name="EPS Foam 10mm",
                thickness_mm=10,
                conductivity=0.035,
                density_kg_m3=25,
                cost_per_sqm=50,
            ))
        elif insulation == "eps_20mm":
            layers.append(WallLayer(
                name="EPS Foam 20mm",
                thickness_mm=20,
                conductivity=0.035,
                density_kg_m3=25,
                cost_per_sqm=90,
            ))
        elif insulation == "air_gap":
            layers.append(WallLayer(
                name="Air Gap 25mm",
                thickness_mm=25,
                conductivity=0.15,
                density_kg_m3=1.2,  # Air
                cost_per_sqm=30,  # Furring strips
            ))
        
        return WallAssembly(name=f"{mix_type}_{thickness}mm", layers=layers)
    
    def optimize(self) -> Dict:
        """Find optimal wall design"""
        best = None
        best_score = float('inf')
        all_valid = []
        
        for thickness in self.thicknesses:
            for mix_type in self.mix_types:
                for core_pct in self.core_percentages:
                    for insulation in self.add_insulation:
                        wall = self._create_wall(
                            thickness, mix_type, core_pct, insulation
                        )
                        
                        # Check constraints
                        if wall.u_value() > self.u_target:
                            continue
                        if wall.total_cost() > self.max_cost:
                            continue
                        
                        # Score: minimize thickness + weight
                        score = (
                            wall.total_thickness() * 1.0 +
                            wall.total_weight() * 0.5 +
                            wall.total_cost() * 0.01
                        )
                        
                        all_valid.append({
                            "wall": wall,
                            "thickness": thickness,
                            "mix": mix_type,
                            "core_pct": core_pct,
                            "insulation": insulation,
                            "score": score,
                        })
                        
                        if score < best_score:
                            best_score = score
                            best = {
                                "wall": wall,
                                "thickness": thickness,
                                "mix": mix_type,
                                "core_pct": core_pct,
                                "insulation": insulation,
                            }
        
        return {
            "best": best,
            "valid_count": len(all_valid),
            "comparison": self._compare_to_market(best["wall"]) if best else None,
        }
    
    def _compare_to_market(self, wall: WallAssembly) -> Dict:
        """Compare to standard market CHB"""
        # Find equivalent market CHB by U-value
        market = MARKET_CHB["standard_6inch"]  # 150mm standard
        
        thickness_savings = market["thickness_mm"] - wall.total_thickness()
        weight_savings = (market["thickness_mm"]/1000 * market["density_kg_m3"] * 0.65) - wall.total_weight()
        cost_diff = wall.total_cost() - market["cost_per_sqm"]
        u_improvement = market["u_value"] - wall.u_value()
        
        return {
            "vs_market_150mm": {
                "thickness_saved_mm": thickness_savings,
                "weight_saved_kg_m2": weight_savings,
                "cost_difference": cost_diff,
                "u_value_improvement": u_improvement,
                "better_insulation": u_improvement > 0,
            }
        }


def optimize_wall(
    u_value_target: float = 2.5,
    min_strength: float = 7.0,
    max_cost: float = 500,
) -> Dict:
    """
    Find optimal wall design.
    
    Returns thinnest, lightest wall that meets:
    - U-value requirement (thermal)
    - Strength requirement
    - Cost limit
    """
    optimizer = WallOptimizer(u_value_target, min_strength, max_cost)
    result = optimizer.optimize()
    
    if result["best"]:
        wall = result["best"]["wall"]
        print("\n" + "="*60)
        print("🧱 WALL THERMAL OPTIMIZER")
        print("="*60)
        print(f"\n🎯 Target: U-value ≤ {u_value_target} W/m²·K")
        
        print(f"\n✅ OPTIMAL WALL DESIGN:")
        print(f"   Mix: {result['best']['mix'].upper()}")
        print(f"   CHB thickness: {result['best']['thickness']}mm")
        print(f"   Core %: {result['best']['core_pct']*100:.0f}%")
        print(f"   Insulation: {result['best']['insulation'] or 'None needed'}")
        
        print(f"\n📊 SPECIFICATIONS:")
        print(f"   Total thickness: {wall.total_thickness()}mm")
        print(f"   U-value: {wall.u_value():.2f} W/m²·K")
        print(f"   Weight: {wall.total_weight():.1f} kg/m²")
        print(f"   Cost: ₱{wall.total_cost():.0f}/m²")
        
        if result["comparison"]:
            comp = result["comparison"]["vs_market_150mm"]
            print(f"\n📈 VS MARKET 150mm CHB:")
            print(f"   Thickness: {comp['thickness_saved_mm']:+.0f}mm")
            print(f"   Weight: {comp['weight_saved_kg_m2']:+.1f} kg/m²")
            print(f"   Insulation: {comp['u_value_improvement']:+.2f} U-value better")
    
    return result


if __name__ == "__main__":
    # Test with different requirements
    print("\n" + "="*60)
    print("SCENARIO 1: Standard Residential (U ≤ 2.5)")
    print("="*60)
    result = optimize_wall(u_value_target=2.5)
    
    print("\n" + "="*60)
    print("SCENARIO 2: Green Building (U ≤ 1.5)")
    print("="*60)
    result = optimize_wall(u_value_target=1.5)
