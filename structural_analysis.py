"""
Structural Analysis Module
Classical mechanics calculations for structural members
Following NSCP 2015 provisions
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional


@dataclass
class Material:
    """Material properties"""
    fc: float = 28.0  # Concrete compressive strength (MPa)
    fy: float = 415.0  # Steel yield strength (MPa)
    Es: float = 200000.0  # Steel modulus (MPa)
    concrete_density: float = 24.0  # kN/m³


@dataclass
class Load:
    """Load case"""
    dead: float = 5.0  # Dead load (kPa)
    live: float = 2.0  # Live load (kPa)
    
    def factored(self) -> float:
        """NSCP factored load: 1.2D + 1.6L"""
        return 1.2 * self.dead + 1.6 * self.live
    
    def service(self) -> float:
        """Service load: D + L"""
        return self.dead + self.live


@dataclass
class MemberSize:
    """Generic member size"""
    width: float  # mm or m depending on context
    depth: float  # mm or m
    
    def area_mm2(self) -> float:
        return self.width * self.depth
    
    def area_m2(self) -> float:
        return (self.width / 1000) * (self.depth / 1000)


# Standard member size options (mm)
# 10 options per member = 40 qubits total for quantum optimization

COLUMN_SIZES = [
    MemberSize(200, 200),   # Minimum for light loads
    MemberSize(225, 225),   # Non-standard but efficient
    MemberSize(250, 250),
    MemberSize(275, 275),   # Non-standard
    MemberSize(300, 300),
    MemberSize(325, 325),   # Non-standard
    MemberSize(350, 350),
    MemberSize(400, 400),
    MemberSize(450, 450),
    MemberSize(500, 500),   # Heavy duty
]

BEAM_SIZES = [
    MemberSize(200, 250),   # Minimum
    MemberSize(200, 300),
    MemberSize(200, 350),
    MemberSize(250, 350),
    MemberSize(250, 400),
    MemberSize(250, 450),
    MemberSize(300, 450),
    MemberSize(300, 500),
    MemberSize(300, 550),
    MemberSize(350, 600),   # Heavy duty
]

SLAB_THICKNESSES = [
    100,   # Minimum for light residential
    110,   # Non-standard but efficient
    120,
    125,
    130,   # Non-standard
    140,
    150,   # Standard residential
    175,
    200,
    250,   # Heavy duty / long spans
]

FOOTING_SIZES = [  # in mm for consistency with other members
    MemberSize(600, 600),    # Light loads / good soil
    MemberSize(700, 700),    # Non-standard
    MemberSize(800, 800),
    MemberSize(900, 900),    # Non-standard
    MemberSize(1000, 1000),
    MemberSize(1100, 1100),  # Non-standard
    MemberSize(1200, 1200),
    MemberSize(1400, 1400),  # Non-standard
    MemberSize(1500, 1500),
    MemberSize(1800, 1800),  # Heavy/poor soil
]


class StructuralAnalysis:
    """
    Classical structural analysis for a simple frame structure.
    Supports 4-column single bay frame with slab.
    """
    
    def __init__(
        self,
        width: float,  # Plan width (m)
        length: float,  # Plan length (m)
        height: float,  # Story height (m)
        material: Material = None,
        load: Load = None,
        soil_bearing: float = 100.0  # kPa
    ):
        self.width = width
        self.length = length
        self.height = height
        self.material = material or Material()
        self.load = load or Load()
        self.soil_bearing = soil_bearing
    
    @property
    def slab_area(self) -> float:
        """Slab area in m²"""
        return self.width * self.length
    
    def slab_self_weight(self, thickness_mm: float) -> float:
        """Slab self-weight in kPa"""
        return (thickness_mm / 1000) * self.material.concrete_density
    
    def total_load(self, slab_thickness_mm: float) -> float:
        """Total distributed load including slab weight (kPa)"""
        return self.load.service() + self.slab_self_weight(slab_thickness_mm)
    
    def total_factored_load(self, slab_thickness_mm: float) -> float:
        """Total factored load (kPa)"""
        slab_weight = self.slab_self_weight(slab_thickness_mm)
        return 1.2 * (self.load.dead + slab_weight) + 1.6 * self.load.live
    
    def column_load(self, slab_thickness_mm: float) -> float:
        """Axial load per column (kN) - service load"""
        total = self.total_load(slab_thickness_mm) * self.slab_area
        return total / 4  # 4 columns
    
    def column_factored_load(self, slab_thickness_mm: float) -> float:
        """Factored axial load per column (kN)"""
        total = self.total_factored_load(slab_thickness_mm) * self.slab_area
        return total / 4
    
    def beam_moment(self, span: float, slab_thickness_mm: float) -> float:
        """
        Maximum beam moment (kN·m)
        Using tributary width method: w = load × (perpendicular span / 2)
        M = wL²/8 for simply supported
        """
        trib_width = (self.length if span == self.width else self.width) / 2
        w = self.total_factored_load(slab_thickness_mm) * trib_width  # kN/m
        return w * span**2 / 8
    
    def max_beam_moment(self, slab_thickness_mm: float) -> float:
        """Maximum beam moment from both directions"""
        mx = self.beam_moment(self.width, slab_thickness_mm)
        my = self.beam_moment(self.length, slab_thickness_mm)
        return max(mx, my)
    
    # ========== CAPACITY CHECKS ==========
    
    def column_capacity(self, size: MemberSize) -> float:
        """
        Column axial capacity (kN) - simplified
        Pu = φ × 0.80 × [0.85 × f'c × (Ag - Ast) + fy × Ast]
        Assuming ρ = 2% reinforcement
        """
        phi = 0.65  # Tied column
        Ag = size.area_mm2()
        rho = 0.02
        Ast = rho * Ag
        capacity = phi * 0.80 * (0.85 * self.material.fc * (Ag - Ast) + self.material.fy * Ast)
        return capacity / 1000  # Convert to kN
    
    def column_stress_ratio(self, size: MemberSize, slab_thickness_mm: float) -> float:
        """Demand/Capacity ratio for column"""
        demand = self.column_factored_load(slab_thickness_mm)
        capacity = self.column_capacity(size)
        return demand / capacity if capacity > 0 else float('inf')
    
    def beam_capacity(self, size: MemberSize) -> float:
        """
        Beam moment capacity (kN·m) - simplified
        Mu = φ × As × fy × (d - a/2)
        Assuming tension steel ratio ρ = 1.2%
        """
        phi = 0.90
        b = size.width
        d = size.depth - 50  # Effective depth (50mm cover)
        rho = 0.012
        As = rho * b * d
        a = (As * self.material.fy) / (0.85 * self.material.fc * b)
        Mn = As * self.material.fy * (d - a/2)
        return phi * Mn / 1e6  # Convert to kN·m
    
    def beam_stress_ratio(self, size: MemberSize, slab_thickness_mm: float) -> float:
        """Demand/Capacity ratio for beam"""
        demand = self.max_beam_moment(slab_thickness_mm)
        capacity = self.beam_capacity(size)
        return demand / capacity if capacity > 0 else float('inf')
    
    def beam_deflection_ratio(self, size: MemberSize) -> float:
        """
        Deflection check: span/d ratio
        NSCP minimum depth for deflection control
        """
        max_span = max(self.width, self.length) * 1000  # mm
        # Simply supported beam: L/16 for beams
        min_depth = max_span / 16
        return min_depth / size.depth  # < 1.0 is OK
    
    def footing_size_required(self, column_load: float) -> float:
        """
        Required square footing size (m)
        A = P / qa
        B = √A
        """
        A_required = column_load / self.soil_bearing
        return math.sqrt(A_required)
    
    def footing_pressure(self, size_m: float, column_load: float) -> float:
        """Actual soil pressure (kPa)"""
        area = size_m * size_m
        return column_load / area if area > 0 else float('inf')
    
    def footing_stress_ratio(self, size: MemberSize, slab_thickness_mm: float) -> float:
        """Soil pressure / Allowable ratio"""
        col_load = self.column_load(slab_thickness_mm)
        size_m = size.width / 1000  # Convert mm to m
        pressure = self.footing_pressure(size_m, col_load)
        return pressure / self.soil_bearing
    
    # ========== VOLUME CALCULATIONS ==========
    
    def slab_volume(self, thickness_mm: float) -> float:
        """Slab concrete volume (m³)"""
        return self.slab_area * (thickness_mm / 1000)
    
    def column_volume(self, size: MemberSize) -> float:
        """Total column volume for 4 columns (m³)"""
        vol_each = size.area_m2() * self.height
        return 4 * vol_each
    
    def beam_volume(self, size: MemberSize, slab_thickness_mm: float) -> float:
        """Total beam volume for 4 beams (m³)"""
        # Beam drops below slab
        beam_depth_below = (size.depth - slab_thickness_mm) / 1000  # m
        beam_width_m = size.width / 1000
        
        # 2 beams span width, 2 beams span length
        length_x = 2 * self.width
        length_y = 2 * self.length
        
        return beam_width_m * beam_depth_below * (length_x + length_y)
    
    def footing_volume(self, size: MemberSize, depth_mm: float = 300) -> float:
        """Total footing volume for 4 footings (m³)"""
        size_m = size.width / 1000
        depth_m = depth_mm / 1000
        return 4 * size_m * size_m * depth_m
    
    def total_concrete_volume(
        self,
        column_size: MemberSize,
        beam_size: MemberSize,
        slab_thickness_mm: float,
        footing_size: MemberSize
    ) -> float:
        """Total concrete volume (m³)"""
        return (
            self.slab_volume(slab_thickness_mm) +
            self.column_volume(column_size) +
            self.beam_volume(beam_size, slab_thickness_mm) +
            self.footing_volume(footing_size)
        )
    
    # ========== WEIGHT/COST CALCULATIONS ==========
    
    def member_weight(self, volume_m3: float) -> float:
        """Weight of concrete member (kN)"""
        return volume_m3 * self.material.concrete_density
    
    def total_weight(
        self,
        column_size: MemberSize,
        beam_size: MemberSize,
        slab_thickness_mm: float,
        footing_size: MemberSize
    ) -> float:
        """Total concrete weight (kN)"""
        vol = self.total_concrete_volume(
            column_size, beam_size, slab_thickness_mm, footing_size
        )
        return self.member_weight(vol)


def get_member_options() -> Dict:
    """Get all available member size options"""
    return {
        'columns': COLUMN_SIZES,
        'beams': BEAM_SIZES,
        'slabs': SLAB_THICKNESSES,
        'footings': FOOTING_SIZES,
    }


if __name__ == "__main__":
    # Quick test
    analysis = StructuralAnalysis(
        width=4.0,
        length=5.0,
        height=3.0,
        soil_bearing=100.0
    )
    
    print(f"Slab Area: {analysis.slab_area} m²")
    print(f"Column Load (service): {analysis.column_load(150):.1f} kN")
    print(f"Column Load (factored): {analysis.column_factored_load(150):.1f} kN")
    print(f"Max Beam Moment: {analysis.max_beam_moment(150):.1f} kN·m")
    
    col = COLUMN_SIZES[1]  # 300x300
    print(f"\nColumn {col.width}×{col.depth} capacity: {analysis.column_capacity(col):.1f} kN")
    print(f"Column stress ratio: {analysis.column_stress_ratio(col, 150):.2f}")
    
    beam = BEAM_SIZES[2]  # 300x450
    print(f"\nBeam {beam.width}×{beam.depth} capacity: {analysis.beam_capacity(beam):.1f} kN·m")
    print(f"Beam stress ratio: {analysis.beam_stress_ratio(beam, 150):.2f}")
