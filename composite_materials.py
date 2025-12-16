"""
Composite Materials Module
Cheap, locally available composite materials for Philippines construction

Focus:
1. Agricultural waste (abundant in PH)
2. Lightweight aggregates
3. Fiber reinforcement
4. Pozzolanic additives
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import math


# ========== COMPOSITE MATERIALS ==========

@dataclass
class CompositeMaterial:
    """
    Composite material properties for construction blocks/slabs.
    """
    name: str
    description: str
    
    # Physical properties
    density_kg_m3: float      # Typical density
    strength_mpa: float       # Compressive strength
    tensile_mpa: float        # Tensile strength
    
    # Cost (PHP per kg or per unit)
    cost_per_kg: float
    availability: str         # "abundant", "moderate", "limited"
    
    # Source
    source: str               # Where to get it
    processing: str           # How to prepare
    
    # Performance modifiers
    insulation_factor: float  # 1.0 = normal, >1 = better insulation
    water_resistance: float   # 0-1 scale
    fire_resistance: float    # 0-1 scale


# ========== CHEAP LOCAL COMPOSITES (PHILIPPINES) ==========

LOCAL_COMPOSITES = {
    
    # === AGRICULTURAL WASTE (PRACTICALLY FREE) ===
    
    "rice_hull_ash": CompositeMaterial(
        name="Rice Hull Ash (RHA)",
        description="Burned rice husk - high silica content, pozzolanic",
        density_kg_m3=400,
        strength_mpa=0,  # Additive, not standalone
        tensile_mpa=0,
        cost_per_kg=2,  # Very cheap, mostly transport cost
        availability="abundant",
        source="Rice mills (Bulacan, Nueva Ecija, Isabela)",
        processing="Burn at 500-700°C, grind to powder",
        insulation_factor=1.3,
        water_resistance=0.7,
        fire_resistance=0.9,
    ),
    
    "coconut_coir": CompositeMaterial(
        name="Coconut Coir Fiber",
        description="Coconut husk fiber - excellent tensile strength",
        density_kg_m3=150,
        strength_mpa=0,
        tensile_mpa=175,  # Very strong in tension!
        cost_per_kg=5,
        availability="abundant",
        source="Coconut farms, copra drying facilities",
        processing="Clean, dry, cut to length (25-50mm)",
        insulation_factor=1.5,
        water_resistance=0.6,
        fire_resistance=0.4,
    ),
    
    "bagasse": CompositeMaterial(
        name="Bagasse (Sugarcane Fiber)",
        description="Sugarcane waste - fiber reinforcement",
        density_kg_m3=120,
        strength_mpa=0,
        tensile_mpa=20,
        cost_per_kg=1,  # Almost free
        availability="abundant",
        source="Sugar mills (Negros, Pampanga, Batangas)",
        processing="Dry, chop to 20-40mm fibers",
        insulation_factor=1.4,
        water_resistance=0.3,
        fire_resistance=0.3,
    ),
    
    "bamboo_fiber": CompositeMaterial(
        name="Bamboo Fiber",
        description="Processed bamboo - high strength natural fiber",
        density_kg_m3=350,
        strength_mpa=0,
        tensile_mpa=350,  # Stronger than steel per weight!
        cost_per_kg=15,
        availability="abundant",
        source="Bamboo farms (everywhere in PH)",
        processing="Split, soak in lime, dry, shred",
        insulation_factor=1.2,
        water_resistance=0.5,
        fire_resistance=0.5,
    ),
    
    # === LIGHTWEIGHT AGGREGATES ===
    
    "volcanic_pumice": CompositeMaterial(
        name="Volcanic Pumice",
        description="Lightweight volcanic rock - excellent for blocks",
        density_kg_m3=500,
        strength_mpa=2,
        tensile_mpa=0.5,
        cost_per_kg=8,
        availability="moderate",
        source="Taal, Pinatubo, Mayon areas",
        processing="Crush to 5-20mm aggregate",
        insulation_factor=2.0,  # Excellent insulation!
        water_resistance=0.8,
        fire_resistance=0.95,
    ),
    
    "scoria": CompositeMaterial(
        name="Volcanic Scoria",
        description="Black volcanic rock - stronger than pumice",
        density_kg_m3=800,
        strength_mpa=5,
        tensile_mpa=1,
        cost_per_kg=10,
        availability="moderate",
        source="Volcanic regions",
        processing="Crush to aggregate size",
        insulation_factor=1.5,
        water_resistance=0.85,
        fire_resistance=0.95,
    ),
    
    # === RECYCLED MATERIALS ===
    
    "recycled_plastic": CompositeMaterial(
        name="Recycled Plastic Aggregate",
        description="Shredded PET/HDPE bottles as aggregate replacement",
        density_kg_m3=950,
        strength_mpa=0,
        tensile_mpa=25,
        cost_per_kg=5,  # Cheap if sourced from junk shops
        availability="abundant",
        source="Junk shops, MRFs, eco-bricks programs",
        processing="Shred to 5-15mm flakes, wash, dry",
        insulation_factor=1.4,
        water_resistance=0.95,
        fire_resistance=0.2,  # Low - needs treatment
    ),
    
    "crushed_glass": CompositeMaterial(
        name="Crushed Glass Aggregate",
        description="Recycled glass as sand replacement",
        density_kg_m3=2500,
        strength_mpa=0,
        tensile_mpa=0,
        cost_per_kg=3,
        availability="moderate",
        source="Glass recyclers, junk shops",
        processing="Crush, tumble to remove sharp edges",
        insulation_factor=1.0,
        water_resistance=0.95,
        fire_resistance=0.9,
    ),
    
    # === POZZOLANIC ADDITIVES (CEMENT REDUCERS) ===
    
    "fly_ash": CompositeMaterial(
        name="Coal Fly Ash",
        description="Coal plant byproduct - cement replacement up to 30%",
        density_kg_m3=1000,
        strength_mpa=0,
        tensile_mpa=0,
        cost_per_kg=3,
        availability="abundant",
        source="Coal power plants (Batangas, Quezon, Cebu)",
        processing="Sieve to remove coarse particles",
        insulation_factor=1.1,
        water_resistance=0.8,
        fire_resistance=0.9,
    ),
    
    "silica_fite": CompositeMaterial(
        name="Silica Fume",
        description="Ultra-fine silica - high-performance concrete additive",
        density_kg_m3=200,
        strength_mpa=0,
        tensile_mpa=0,
        cost_per_kg=50,  # More expensive
        availability="limited",
        source="Import or silicon smelters",
        processing="Use as-is, 5-10% cement replacement",
        insulation_factor=1.0,
        water_resistance=0.9,
        fire_resistance=0.95,
    ),
}


# ========== MIX DESIGNS ==========

@dataclass
class ConcreteMix:
    """
    Concrete mix design with composites.
    All quantities per cubic meter.
    """
    name: str
    description: str
    
    # Base materials (kg/m³)
    cement_kg: float
    sand_kg: float
    gravel_kg: float
    water_liters: float
    
    # Composites (kg/m³)
    composites: Dict[str, float]  # material_id: kg/m³
    
    # Expected properties
    density_kg_m3: float
    strength_28day_mpa: float
    cost_per_m3: float
    
    def total_weight(self) -> float:
        return (self.cement_kg + self.sand_kg + self.gravel_kg + 
                self.water_liters + sum(self.composites.values()))


# Pre-defined mix designs
MIX_DESIGNS = {
    
    "lightweight_block": ConcreteMix(
        name="Lightweight CHB Mix",
        description="For lego blocks - pumice + coir fiber",
        cement_kg=250,
        sand_kg=400,
        gravel_kg=0,  # Use pumice instead
        water_liters=150,
        composites={
            "volcanic_pumice": 350,
            "coconut_coir": 5,
            "rice_hull_ash": 30,  # 12% cement replacement
        },
        density_kg_m3=1600,  # Much lighter than 2400!
        strength_28day_mpa=10,  # Adequate for non-load-bearing
        cost_per_m3=3500,
    ),
    
    "structural_block": ConcreteMix(
        name="Structural CHB Mix",
        description="Load-bearing blocks with fiber reinforcement",
        cement_kg=350,
        sand_kg=600,
        gravel_kg=200,
        water_liters=175,
        composites={
            "bamboo_fiber": 8,
            "fly_ash": 50,  # 14% cement replacement
        },
        density_kg_m3=2100,
        strength_28day_mpa=17.5,  # Standard CHB strength
        cost_per_m3=4200,
    ),
    
    "eco_slab_light": ConcreteMix(
        name="Eco Lightweight Slab",
        description="Strong but light slab - for upper floors",
        cement_kg=400,
        sand_kg=500,
        gravel_kg=300,
        water_liters=180,
        composites={
            "volcanic_pumice": 200,
            "bamboo_fiber": 10,
            "fly_ash": 60,
        },
        density_kg_m3=1900,  # 20% lighter!
        strength_28day_mpa=25,
        cost_per_m3=4800,
    ),
    
    "ultra_light_insulation": ConcreteMix(
        name="Ultra-Light Insulation Panel",
        description="Non-structural, excellent insulation",
        cement_kg=200,
        sand_kg=200,
        gravel_kg=0,
        water_liters=150,
        composites={
            "volcanic_pumice": 400,
            "bagasse": 20,
            "rice_hull_ash": 50,
        },
        density_kg_m3=1200,  # 50% lighter!
        strength_28day_mpa=5,  # Non-structural
        cost_per_m3=2800,
    ),
}


# ========== LIGHTWEIGHT SLAB SYSTEMS ==========

@dataclass
class LightweightSlab:
    """
    Lightweight slab system design.
    """
    name: str
    system_type: str  # "hollow_core", "waffle", "bubble_deck", "sandwich"
    
    # Dimensions
    thickness_mm: float
    span_m: float
    
    # Materials
    concrete_mix: str  # Reference to MIX_DESIGNS
    void_percentage: float  # 0-0.5 (how much is void/filler)
    
    # Performance
    self_weight_kpa: float
    capacity_kpa: float  # Live load capacity
    
    def weight_reduction(self) -> float:
        """Weight reduction vs solid slab"""
        solid_weight = self.thickness_mm / 1000 * 2400 * 9.81 / 1000  # kPa
        return (solid_weight - self.self_weight_kpa) / solid_weight


SLAB_SYSTEMS = {
    
    "hollow_core_150": LightweightSlab(
        name="Hollow Core Slab 150mm",
        system_type="hollow_core",
        thickness_mm=150,
        span_m=6.0,
        concrete_mix="eco_slab_light",
        void_percentage=0.35,
        self_weight_kpa=2.8,  # vs 3.6 for solid
        capacity_kpa=5.0,
    ),
    
    "waffle_250": LightweightSlab(
        name="Waffle Slab 250mm",
        system_type="waffle",
        thickness_mm=250,
        span_m=9.0,
        concrete_mix="structural_block",
        void_percentage=0.40,
        self_weight_kpa=4.2,  # vs 6.0 for solid
        capacity_kpa=7.5,
    ),
    
    "bubble_deck_200": LightweightSlab(
        name="Bubble Deck 200mm",  
        system_type="bubble_deck",
        thickness_mm=200,
        span_m=8.0,
        concrete_mix="eco_slab_light",
        void_percentage=0.35,
        self_weight_kpa=3.5,
        capacity_kpa=6.0,
    ),
    
    "sandwich_eps_125": LightweightSlab(
        name="EPS Sandwich Panel 125mm",
        system_type="sandwich",
        thickness_mm=125,
        span_m=4.0,
        concrete_mix="eco_slab_light",
        void_percentage=0.50,  # EPS core
        self_weight_kpa=1.8,  # Very light!
        capacity_kpa=3.0,
    ),
}


def print_materials_summary():
    """Print summary of available materials"""
    print("\n" + "="*70)
    print("🌱 CHEAP LOCAL COMPOSITES FOR PHILIPPINES")
    print("="*70)
    
    print("\n📦 AGRICULTURAL WASTE (PRACTICALLY FREE):")
    for key in ["rice_hull_ash", "coconut_coir", "bagasse", "bamboo_fiber"]:
        m = LOCAL_COMPOSITES[key]
        print(f"   • {m.name}: ₱{m.cost_per_kg}/kg - {m.availability}")
        print(f"     {m.source}")
    
    print("\n🌋 LIGHTWEIGHT AGGREGATES:")
    for key in ["volcanic_pumice", "scoria"]:
        m = LOCAL_COMPOSITES[key]
        print(f"   • {m.name}: ₱{m.cost_per_kg}/kg - {m.availability}")
        print(f"     Density: {m.density_kg_m3} kg/m³ (vs 2700 for gravel)")
    
    print("\n♻️ RECYCLED MATERIALS:")
    for key in ["recycled_plastic", "crushed_glass"]:
        m = LOCAL_COMPOSITES[key]
        print(f"   • {m.name}: ₱{m.cost_per_kg}/kg")
        print(f"     {m.source}")
    
    print("\n⚗️ CEMENT REDUCERS (POZZOLANS):")
    for key in ["fly_ash", "rice_hull_ash"]:
        m = LOCAL_COMPOSITES[key]
        print(f"   • {m.name}: Can replace 10-30% cement!")


def print_slab_comparison():
    """Compare slab systems"""
    print("\n" + "="*70)
    print("🏗️ LIGHTWEIGHT SLAB SYSTEMS")
    print("="*70)
    
    print("\n| System | Thickness | Span | Weight | Reduction |")
    print("|--------|-----------|------|--------|-----------|")
    for key, slab in SLAB_SYSTEMS.items():
        reduction = slab.weight_reduction() * 100
        print(f"| {slab.name[:20]:<20} | {slab.thickness_mm}mm | {slab.span_m}m | {slab.self_weight_kpa} kPa | {reduction:.0f}% |")


if __name__ == "__main__":
    print_materials_summary()
    print_slab_comparison()
    
    print("\n" + "="*70)
    print("💡 RECOMMENDED MIX: Lightweight CHB with Pumice + Coir")
    print("="*70)
    mix = MIX_DESIGNS["lightweight_block"]
    print(f"\n{mix.name}:")
    print(f"   Cement: {mix.cement_kg} kg")
    print(f"   Sand: {mix.sand_kg} kg")
    print(f"   Pumice: {mix.composites.get('volcanic_pumice', 0)} kg")
    print(f"   Coir fiber: {mix.composites.get('coconut_coir', 0)} kg")
    print(f"   RHA: {mix.composites.get('rice_hull_ash', 0)} kg (cement replacement)")
    print(f"\n   Final density: {mix.density_kg_m3} kg/m³ (33% lighter!)")
    print(f"   Strength: {mix.strength_28day_mpa} MPa")
    print(f"   Cost: ₱{mix.cost_per_m3}/m³")
