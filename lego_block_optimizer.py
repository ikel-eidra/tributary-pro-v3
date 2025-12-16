"""
Phase 3: Composite Lego-Style Hollow Block System
Modular, interlocking concrete blocks with integrated rebar channels

Design Goals:
1. No mortar needed (dry-stack with interlock)
2. Integrated vertical & horizontal rebar channels
3. Grout-filled cores for structural strength
4. Standardized dimensions for easy replication
5. Quantum-optimized geometry for strength/weight ratio
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import math
import numpy as np


# ========== BLOCK GEOMETRY ==========

@dataclass
class LegoBlock:
    """
    Modular interlocking concrete block unit.
    Dimensions in mm.
    """
    # Overall dimensions
    length: float = 400      # Along wall length
    width: float = 200       # Wall thickness  
    height: float = 200      # Course height
    
    # Core holes (for rebar & grout)
    n_cores: int = 2         # Number of vertical cores
    core_diameter: float = 80  # mm
    
    # Interlock features
    nub_height: float = 25   # Height of top nubs (like lego)
    nub_diameter: float = 60  # Diameter of interlocking nubs
    n_nubs: int = 2          # Number of nubs on top
    
    # Shell thickness
    shell_thickness: float = 30  # Minimum wall thickness
    
    # Material
    fc: float = 17.5         # Typical CHB strength (MPa)
    
    def gross_area(self) -> float:
        """Gross cross-sectional area (mm²)"""
        return self.length * self.width
    
    def net_area(self) -> float:
        """Net area excluding cores (mm²)"""
        core_area = self.n_cores * math.pi * (self.core_diameter/2)**2
        return self.gross_area() - core_area
    
    def solid_ratio(self) -> float:
        """Solid percentage (higher = stronger but heavier)"""
        return self.net_area() / self.gross_area()
    
    def volume_solid(self) -> float:
        """Volume of solid concrete per block (mm³)"""
        # Main body (excluding cores)
        body_vol = self.net_area() * (self.height - self.nub_height)
        # Nubs on top
        nub_vol = self.n_nubs * math.pi * (self.nub_diameter/2)**2 * self.nub_height
        return body_vol + nub_vol
    
    def weight_kg(self, density: float = 2200) -> float:
        """Weight per block (kg), assuming 2200 kg/m³ lightweight concrete"""
        return self.volume_solid() / 1e9 * density
    
    def blocks_per_sqm(self) -> float:
        """Number of blocks per square meter of wall"""
        block_face = (self.length / 1000) * (self.height / 1000)
        return 1.0 / block_face
    
    def rebar_capacity(self) -> Dict:
        """Rebar that can fit in cores"""
        # Typical: 12mm or 16mm bars in each core
        max_bar = self.core_diameter - 20  # 10mm cover each side
        return {
            'max_bar_diameter_mm': max_bar,
            'bars_per_core': 1 if max_bar < 20 else 2,
            'total_bars': self.n_cores * (1 if max_bar < 20 else 2),
        }


@dataclass
class WallSystem:
    """
    Complete wall system using lego blocks.
    """
    block: LegoBlock
    wall_length: float  # m
    wall_height: float  # m
    
    # Rebar configuration
    vertical_spacing: float = 0.6   # m between vertical bars
    horizontal_spacing: float = 0.6  # m between horizontal bond beams
    
    def total_blocks(self) -> int:
        """Total blocks needed"""
        return math.ceil(self.block.blocks_per_sqm() * self.wall_length * self.wall_height)
    
    def total_weight_kg(self) -> float:
        """Total block weight (before grout)"""
        return self.total_blocks() * self.block.weight_kg()
    
    def grout_volume_m3(self) -> float:
        """Volume of grout needed for cores"""
        core_area = self.block.n_cores * math.pi * (self.block.core_diameter/2)**2
        wall_area_mm2 = self.wall_length * 1000 * self.wall_height * 1000
        n_cores_total = (wall_area_mm2 / self.block.gross_area()) * self.block.n_cores
        grout_vol = n_cores_total * core_area * self.block.height
        return grout_vol / 1e9  # Convert to m³
    
    def rebar_length_m(self) -> float:
        """Total rebar length needed"""
        # Vertical bars
        n_vertical = math.ceil(self.wall_length / self.vertical_spacing) + 1
        vertical_length = n_vertical * self.wall_height
        
        # Horizontal bars (in bond beams)
        n_horizontal_courses = math.ceil(self.wall_height / self.horizontal_spacing)
        horizontal_length = n_horizontal_courses * self.wall_length
        
        return vertical_length + horizontal_length


# ========== BLOCK DESIGN OPTIONS ==========

# Standard sizes to optimize
BLOCK_LENGTHS = [300, 350, 400, 450, 500]  # mm
BLOCK_WIDTHS = [100, 150, 200, 250]  # mm (wall thickness)
BLOCK_HEIGHTS = [150, 175, 200, 225]  # mm
CORE_DIAMETERS = [60, 70, 80, 90, 100]  # mm
NUB_CONFIGS = [
    (2, 50, 20),  # (n_nubs, diameter, height)
    (2, 60, 25),
    (3, 40, 20),
    (3, 50, 25),
    (4, 40, 20),
]


class BlockQUBOEncoder:
    """
    QUBO encoder for optimal block geometry.
    Minimizes material while meeting structural requirements.
    """
    
    def __init__(
        self,
        required_strength_kn_m: float = 50,  # Required wall strength per meter
        max_weight_per_block: float = 15,    # Max weight for manual handling
        min_solid_ratio: float = 0.55,       # Min solid for structural
    ):
        self.required_strength = required_strength_kn_m
        self.max_weight = max_weight_per_block
        self.min_solid = min_solid_ratio
        
        # Variable counts
        self.n_length = len(BLOCK_LENGTHS)
        self.n_width = len(BLOCK_WIDTHS)
        self.n_height = len(BLOCK_HEIGHTS)
        self.n_core = len(CORE_DIAMETERS)
        self.n_nub = len(NUB_CONFIGS)
        
        self.n_vars = self.n_length + self.n_width + self.n_height + self.n_core + self.n_nub
        
        # Variable start indices
        self.idx_length = 0
        self.idx_width = self.n_length
        self.idx_height = self.idx_width + self.n_width
        self.idx_core = self.idx_height + self.n_height
        self.idx_nub = self.idx_core + self.n_core
        
        self.lambda_onehot = 5000
        self.lambda_strength = 2000
        self.lambda_weight = 1500
        self.lambda_solid = 1000
    
    def encode(self) -> Tuple[np.ndarray, Dict]:
        """Encode block optimization as QUBO"""
        Q = np.zeros((self.n_vars, self.n_vars))
        
        # 1. Objective: Minimize material (volume)
        self._add_volume_objective(Q)
        
        # 2. One-hot constraints
        self._add_onehot_constraints(Q)
        
        # 3. Structural strength constraint
        self._add_strength_constraint(Q)
        
        # 4. Weight constraint (handleability)
        self._add_weight_constraint(Q)
        
        # 5. Solid ratio constraint
        self._add_solid_constraint(Q)
        
        metadata = {
            'n_vars': self.n_vars,
            'lengths': BLOCK_LENGTHS,
            'widths': BLOCK_WIDTHS,
            'heights': BLOCK_HEIGHTS,
            'cores': CORE_DIAMETERS,
            'nubs': NUB_CONFIGS,
        }
        
        return Q, metadata
    
    def _add_volume_objective(self, Q: np.ndarray):
        """Minimize block volume (material cost)"""
        # Volume ~ length × width × height (linear approximation)
        for i, L in enumerate(BLOCK_LENGTHS):
            Q[self.idx_length + i, self.idx_length + i] += L / 100  # Normalize
        for i, W in enumerate(BLOCK_WIDTHS):
            Q[self.idx_width + i, self.idx_width + i] += W / 100
        for i, H in enumerate(BLOCK_HEIGHTS):
            Q[self.idx_height + i, self.idx_height + i] += H / 100
        # Larger cores = less material (negative)
        for i, D in enumerate(CORE_DIAMETERS):
            Q[self.idx_core + i, self.idx_core + i] -= D / 100
    
    def _add_onehot_constraints(self, Q: np.ndarray):
        """Exactly one option per variable group"""
        groups = [
            (self.idx_length, self.n_length),
            (self.idx_width, self.n_width),
            (self.idx_height, self.n_height),
            (self.idx_core, self.n_core),
            (self.idx_nub, self.n_nub),
        ]
        for start, count in groups:
            for i in range(count):
                Q[start + i, start + i] -= self.lambda_onehot
                for j in range(i + 1, count):
                    Q[start + i, start + j] += 2 * self.lambda_onehot
    
    def _add_strength_constraint(self, Q: np.ndarray):
        """Penalize weak combinations"""
        # Strength depends on width (thickness) and solid ratio
        for wi, W in enumerate(BLOCK_WIDTHS):
            for ci, D in enumerate(CORE_DIAMETERS):
                # Approximate strength check
                # Thinner walls with large cores = weaker
                if W < 150 and D > 80:
                    penalty = self.lambda_strength
                    Q[self.idx_width + wi, self.idx_core + ci] += penalty
    
    def _add_weight_constraint(self, Q: np.ndarray):
        """Penalize combinations exceeding max weight"""
        for li, L in enumerate(BLOCK_LENGTHS):
            for wi, W in enumerate(BLOCK_WIDTHS):
                for hi, H in enumerate(BLOCK_HEIGHTS):
                    # Rough weight estimate
                    vol = L * W * H * 0.6  # 60% solid
                    weight = vol / 1e9 * 2200
                    if weight > self.max_weight:
                        # Add pairwise penalties
                        Q[self.idx_length + li, self.idx_width + wi] += self.lambda_weight
                        Q[self.idx_width + wi, self.idx_height + hi] += self.lambda_weight
    
    def _add_solid_constraint(self, Q: np.ndarray):
        """Ensure minimum solid ratio"""
        for wi, W in enumerate(BLOCK_WIDTHS):
            for ci, D in enumerate(CORE_DIAMETERS):
                # If core too large relative to width
                if D > W * 0.4:  # Core > 40% of width
                    Q[self.idx_width + wi, self.idx_core + ci] += self.lambda_solid
    
    def decode_solution(self, x: np.ndarray) -> LegoBlock:
        """Decode solution to LegoBlock design"""
        li = np.argmax(x[self.idx_length:self.idx_length + self.n_length])
        wi = np.argmax(x[self.idx_width:self.idx_width + self.n_width])
        hi = np.argmax(x[self.idx_height:self.idx_height + self.n_height])
        ci = np.argmax(x[self.idx_core:self.idx_core + self.n_core])
        ni = np.argmax(x[self.idx_nub:self.idx_nub + self.n_nub])
        
        n_nubs, nub_d, nub_h = NUB_CONFIGS[ni]
        
        return LegoBlock(
            length=BLOCK_LENGTHS[li],
            width=BLOCK_WIDTHS[wi],
            height=BLOCK_HEIGHTS[hi],
            core_diameter=CORE_DIAMETERS[ci],
            n_nubs=n_nubs,
            nub_diameter=nub_d,
            nub_height=nub_h,
        )


def optimize_block_design(
    required_strength: float = 50,
    max_weight: float = 15,
    min_solid: float = 0.55,
    use_quantum: bool = False,
) -> Dict:
    """
    Optimize lego block geometry using quantum/classical solver.
    
    Returns optimal block design with specifications.
    """
    encoder = BlockQUBOEncoder(required_strength, max_weight, min_solid)
    Q, metadata = encoder.encode()
    
    print("\n" + "="*60)
    print("🧱 Lego Block Optimizer (Phase 3)")
    print("="*60)
    print(f"\n⚛️ QUBO Variables: {metadata['n_vars']}")
    print(f"   - Lengths: {len(metadata['lengths'])} options")
    print(f"   - Widths: {len(metadata['widths'])} options")
    print(f"   - Heights: {len(metadata['heights'])} options")
    print(f"   - Core diameters: {len(metadata['cores'])} options")
    print(f"   - Nub configs: {len(metadata['nubs'])} options")
    
    # Solve
    from optimizer import QuantumOptimizer, OptimizerConfig
    config = OptimizerConfig(use_quantum=use_quantum)
    optimizer = QuantumOptimizer.__new__(QuantumOptimizer)
    optimizer.config = config
    solution = optimizer._solve_classical(Q, 100)
    
    block = encoder.decode_solution(solution)
    
    print(f"\n✅ OPTIMAL BLOCK DESIGN:")
    print(f"   📐 Dimensions: {block.length} × {block.width} × {block.height} mm")
    print(f"   🔘 Cores: {block.n_cores} × Ø{block.core_diameter}mm")
    print(f"   🔗 Nubs: {block.n_nubs} × Ø{block.nub_diameter}mm × {block.nub_height}mm")
    print(f"\n📊 SPECIFICATIONS:")
    print(f"   Solid ratio: {block.solid_ratio()*100:.1f}%")
    print(f"   Weight: {block.weight_kg():.2f} kg/block")
    print(f"   Blocks/m²: {block.blocks_per_sqm():.1f}")
    print(f"   Rebar capacity: {block.rebar_capacity()}")
    
    return {
        'block': block,
        'dimensions': {
            'length': block.length,
            'width': block.width,
            'height': block.height,
        },
        'cores': {
            'count': block.n_cores,
            'diameter': block.core_diameter,
        },
        'nubs': {
            'count': block.n_nubs,
            'diameter': block.nub_diameter,
            'height': block.nub_height,
        },
        'specs': {
            'solid_ratio': block.solid_ratio(),
            'weight_kg': block.weight_kg(),
            'blocks_per_sqm': block.blocks_per_sqm(),
            'rebar_capacity': block.rebar_capacity(),
        }
    }


if __name__ == "__main__":
    result = optimize_block_design()
    
    # Also show wall calculation example
    print("\n" + "="*60)
    print("🏗️ Example Wall Calculation")
    print("="*60)
    
    wall = WallSystem(
        block=result['block'],
        wall_length=5.0,
        wall_height=3.0,
    )
    
    print(f"\nWall: {wall.wall_length}m × {wall.wall_height}m")
    print(f"   Total blocks: {wall.total_blocks()}")
    print(f"   Block weight: {wall.total_weight_kg():.0f} kg")
    print(f"   Grout needed: {wall.grout_volume_m3():.3f} m³")
    print(f"   Rebar length: {wall.rebar_length_m():.1f} m")
