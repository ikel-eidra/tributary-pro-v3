"""
Concrete Mix Cost Optimizer
Minimize material costs while maintaining strength

Key Insight: CEMENT is the most expensive component!
- Cement: ~₱280/40kg bag = ₱7,000/ton
- Sand: ~₱800/m³ ≈ ₱500/ton
- Gravel: ~₱1,200/m³ ≈ ₱450/ton

Strategy:
1. Replace cement with POZZOLANS (cheaper!)
2. Use local aggregates
3. Optimize water-cement ratio
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math


# ========== MATERIAL COSTS (PHP per ton) ==========

MATERIAL_COSTS = {
    # Binders
    "cement_opc": 7000,           # Ordinary Portland Cement
    "cement_ppc": 6500,           # Pozzolan Portland Cement (already has pozzolan)
    
    # Pozzolans (CEMENT REPLACEMENTS - much cheaper!)
    "fly_ash": 1500,              # Coal plant byproduct
    "rice_hull_ash": 800,         # Agricultural waste - VERY CHEAP
    "ggbs": 3500,                 # Ground granulated blast furnace slag
    "silica_fume": 25000,         # Expensive but small amounts needed
    
    # Fine aggregates
    "river_sand": 500,
    "manufactured_sand": 600,
    "crushed_stone_fines": 550,
    
    # Coarse aggregates
    "gravel_20mm": 450,
    "crushed_stone_20mm": 500,
    
    # Lightweight aggregates (for HYBRID mix)
    "volcanic_pumice": 1200,      # Lighter than gravel
    "scoria": 1000,
    "expanded_clay": 3000,        # LECA - more expensive
    
    # Fibers
    "coconut_coir": 2000,         # Local, cheap
    "bamboo_fiber": 3000,
    "steel_fiber": 45000,         # Expensive!
    "polypropylene_fiber": 20000,
    
    # Additives
    "water_reducer": 80000,       # Per ton (but use tiny amounts)
    "superplasticizer": 120000,
}

# Typical densities (kg/m³)
DENSITIES = {
    "cement_opc": 1500,
    "fly_ash": 1000,
    "rice_hull_ash": 400,
    "ggbs": 1200,
    "river_sand": 1600,
    "gravel_20mm": 1500,
    "volcanic_pumice": 500,
    "scoria": 800,
}


@dataclass
class ConcreteMixDesign:
    """
    Concrete mix design per cubic meter.
    All weights in kg/m³.
    """
    name: str
    description: str
    target_strength_mpa: float
    
    # Binder system (kg/m³)
    cement: float
    fly_ash: float = 0
    rice_hull_ash: float = 0
    ggbs: float = 0
    silica_fume: float = 0
    
    # Aggregates (kg/m³)
    sand: float = 700
    coarse_aggregate: float = 1000
    coarse_type: str = "gravel_20mm"  # or "volcanic_pumice"
    
    # Fiber (kg/m³) - optional
    fiber: float = 0
    fiber_type: str = "coconut_coir"
    
    # Water (kg/m³)
    water: float = 180
    
    # Admixtures (liters/m³)
    water_reducer: float = 0
    
    def total_binder(self) -> float:
        """Total cementitious content"""
        return (self.cement + self.fly_ash + self.rice_hull_ash + 
                self.ggbs + self.silica_fume)
    
    def cement_replacement_percent(self) -> float:
        """Percentage of cement replaced by pozzolans"""
        total = self.total_binder()
        if total == 0:
            return 0
        return (1 - self.cement / total) * 100
    
    def water_binder_ratio(self) -> float:
        """W/B ratio"""
        return self.water / self.total_binder()
    
    def density(self) -> float:
        """Approximate fresh density (kg/m³)"""
        return (self.cement + self.fly_ash + self.rice_hull_ash + 
                self.ggbs + self.silica_fume + self.sand + 
                self.coarse_aggregate + self.fiber + self.water)
    
    def cost_per_m3(self) -> Dict:
        """Calculate cost per cubic meter"""
        costs = {}
        
        # Binders (convert kg to tons: /1000)
        costs["cement"] = self.cement / 1000 * MATERIAL_COSTS["cement_opc"]
        costs["fly_ash"] = self.fly_ash / 1000 * MATERIAL_COSTS["fly_ash"]
        costs["rha"] = self.rice_hull_ash / 1000 * MATERIAL_COSTS["rice_hull_ash"]
        costs["ggbs"] = self.ggbs / 1000 * MATERIAL_COSTS["ggbs"]
        costs["silica_fume"] = self.silica_fume / 1000 * MATERIAL_COSTS["silica_fume"]
        
        # Aggregates
        costs["sand"] = self.sand / 1000 * MATERIAL_COSTS["river_sand"]
        costs["coarse"] = self.coarse_aggregate / 1000 * MATERIAL_COSTS.get(
            self.coarse_type, MATERIAL_COSTS["gravel_20mm"]
        )
        
        # Fiber
        if self.fiber > 0:
            costs["fiber"] = self.fiber / 1000 * MATERIAL_COSTS.get(
                self.fiber_type, MATERIAL_COSTS["coconut_coir"]
            )
        
        # Total
        costs["total"] = sum(costs.values())
        
        return costs
    
    def vs_conventional(self, conventional_cost: float = 4500) -> Dict:
        """Compare to conventional mix cost"""
        my_cost = self.cost_per_m3()["total"]
        savings = conventional_cost - my_cost
        savings_percent = savings / conventional_cost * 100
        
        return {
            "conventional_cost": conventional_cost,
            "our_cost": my_cost,
            "savings_php": savings,
            "savings_percent": savings_percent,
        }


# ========== PREDEFINED MIX DESIGNS ==========

MIX_DESIGNS = {
    
    "conventional_25mpa": ConcreteMixDesign(
        name="Conventional Mix (25 MPa)",
        description="Standard ready-mix concrete",
        target_strength_mpa=25,
        cement=350,  # All cement, no replacements
        sand=700,
        coarse_aggregate=1100,
        coarse_type="gravel_20mm",
        water=175,
    ),
    
    "eco_25mpa_flyash": ConcreteMixDesign(
        name="Fly Ash Mix (25 MPa)",
        description="25% cement replaced with fly ash",
        target_strength_mpa=25,
        cement=265,
        fly_ash=85,  # 25% replacement
        sand=700,
        coarse_aggregate=1100,
        coarse_type="gravel_20mm",
        water=170,
    ),
    
    "eco_25mpa_rha": ConcreteMixDesign(
        name="Rice Hull Ash Mix (25 MPa)",
        description="20% cement replaced with RHA",
        target_strength_mpa=25,
        cement=280,
        rice_hull_ash=70,  # 20% replacement
        sand=700,
        coarse_aggregate=1100,
        coarse_type="gravel_20mm",
        water=175,
    ),
    
    "hybrid_20mpa": ConcreteMixDesign(
        name="HYBRID Lightweight (20 MPa)",
        description="Pumice aggregate + RHA + Coir fiber",
        target_strength_mpa=20,
        cement=250,
        rice_hull_ash=50,
        fly_ash=50,  # 30% total replacement!
        sand=500,
        coarse_aggregate=350,  # Pumice is lighter
        coarse_type="volcanic_pumice",
        fiber=5,
        fiber_type="coconut_coir",
        water=170,
    ),
    
    "ultra_eco_15mpa": ConcreteMixDesign(
        name="Ultra-Eco (15 MPa)",
        description="Maximum cement replacement for non-structural",
        target_strength_mpa=15,
        cement=200,
        rice_hull_ash=60,
        fly_ash=90,  # 45% total replacement!
        sand=600,
        coarse_aggregate=400,
        coarse_type="volcanic_pumice",
        fiber=8,
        fiber_type="coconut_coir",
        water=160,
    ),
    
    "high_strength_45mpa": ConcreteMixDesign(
        name="High Strength (45 MPa)",
        description="For prestressed elements",
        target_strength_mpa=45,
        cement=400,
        silica_fume=40,  # 10% silica fume
        fly_ash=60,
        sand=650,
        coarse_aggregate=1050,
        coarse_type="crushed_stone_20mm",
        water=160,
        water_reducer=3,
    ),
}


def compare_all_mixes():
    """Compare all mix designs"""
    print("\n" + "="*70)
    print("💰 CONCRETE MIX COST COMPARISON")
    print("="*70)
    
    # Get conventional cost as baseline
    conv = MIX_DESIGNS["conventional_25mpa"]
    conv_cost = conv.cost_per_m3()["total"]
    
    print(f"\n📊 Baseline: Conventional 25MPa = ₱{conv_cost:,.0f}/m³")
    print("\n| Mix Design | Strength | Cement % | Cost/m³ | Savings |")
    print("|------------|----------|----------|---------|---------|")
    
    for key, mix in MIX_DESIGNS.items():
        cost = mix.cost_per_m3()["total"]
        savings = (conv_cost - cost) / conv_cost * 100
        cement_pct = 100 - mix.cement_replacement_percent()
        
        print(f"| {mix.name[:20]:<20} | {mix.target_strength_mpa}MPa | {cement_pct:.0f}% | ₱{cost:,.0f} | {savings:+.0f}% |")


def optimize_for_strength(
    target_mpa: float,
    max_cement_per_m3: float = None,
    use_local_pozzolans: bool = True,
) -> ConcreteMixDesign:
    """
    Find cheapest mix that achieves target strength.
    """
    print("\n" + "="*60)
    print(f"🎯 OPTIMIZING FOR {target_mpa} MPa")
    print("="*60)
    
    # Base cement content (rule of thumb: 10kg cement per MPa)
    base_cement = target_mpa * 12  # kg/m³
    
    # Maximum replacement ratios by strength class
    if target_mpa <= 15:
        max_replacement = 0.45  # 45% for non-structural
    elif target_mpa <= 25:
        max_replacement = 0.35  # 35% for normal
    elif target_mpa <= 35:
        max_replacement = 0.25  # 25% for moderate
    else:
        max_replacement = 0.15  # 15% for high strength
    
    # Calculate cement with max replacement
    total_binder = base_cement / (1 - max_replacement)
    cement = base_cement
    
    if use_local_pozzolans:
        # Use cheapest pozzolans: RHA then fly ash
        rha_amount = min(total_binder * 0.15, 60)  # Max 15% or 60kg
        fly_ash_amount = total_binder * max_replacement - rha_amount
        fly_ash_amount = max(0, fly_ash_amount)
    else:
        rha_amount = 0
        fly_ash_amount = total_binder * max_replacement
    
    # Use pumice for lightweight if low strength
    if target_mpa <= 20:
        coarse_type = "volcanic_pumice"
        coarse_amount = 400
        sand_amount = 550
    else:
        coarse_type = "gravel_20mm"
        coarse_amount = 1050
        sand_amount = 700
    
    # Fiber for low strength mixes
    fiber = 5 if target_mpa <= 20 else 0
    
    # Water (w/b ratio based on strength)
    wb_ratio = 0.65 - (target_mpa - 15) * 0.01
    wb_ratio = max(0.35, min(0.65, wb_ratio))
    water = (cement + rha_amount + fly_ash_amount) * wb_ratio
    
    mix = ConcreteMixDesign(
        name=f"Optimized {target_mpa}MPa",
        description=f"Cost-optimized with {max_replacement*100:.0f}% cement replacement",
        target_strength_mpa=target_mpa,
        cement=cement,
        rice_hull_ash=rha_amount,
        fly_ash=fly_ash_amount,
        sand=sand_amount,
        coarse_aggregate=coarse_amount,
        coarse_type=coarse_type,
        fiber=fiber,
        fiber_type="coconut_coir",
        water=water,
    )
    
    cost = mix.cost_per_m3()
    conv_cost = 4500  # Conventional baseline
    comparison = mix.vs_conventional(conv_cost)
    
    print(f"\n✅ OPTIMIZED MIX:")
    print(f"   Cement: {mix.cement:.0f} kg/m³")
    print(f"   RHA: {mix.rice_hull_ash:.0f} kg/m³")
    print(f"   Fly Ash: {mix.fly_ash:.0f} kg/m³")
    print(f"   Cement replacement: {mix.cement_replacement_percent():.0f}%")
    print(f"   Aggregate: {mix.coarse_type}")
    
    print(f"\n💰 COST:")
    print(f"   Cement cost: ₱{cost['cement']:,.0f}")
    print(f"   Pozzolans:   ₱{cost['fly_ash'] + cost['rha']:,.0f}")
    print(f"   Aggregates:  ₱{cost['sand'] + cost['coarse']:,.0f}")
    print(f"   Total:       ₱{cost['total']:,.0f}/m³")
    
    print(f"\n📈 VS CONVENTIONAL:")
    print(f"   Savings: ₱{comparison['savings_php']:,.0f}/m³ ({comparison['savings_percent']:.0f}%)")
    
    return mix


if __name__ == "__main__":
    compare_all_mixes()
    
    print("\n")
    optimize_for_strength(15)  # For non-structural blocks
    optimize_for_strength(25)  # For structural elements
    optimize_for_strength(35)  # For prestressed
