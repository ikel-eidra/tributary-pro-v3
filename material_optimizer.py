"""
Material Optimization Module (Phase 2)
Optimizes concrete strength (f'c) and rebar percentage when member sizes are FIXED.
Use case: Columns flush with CHB walls, retrofit projects, etc.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple
import numpy as np


@dataclass
class FixedMember:
    """Fixed member size (locked by architectural constraints)"""
    width: float    # mm
    depth: float    # mm
    name: str = ""


@dataclass  
class MaterialOption:
    """Material combination option"""
    fc: float       # Concrete strength (MPa)
    rho: float      # Steel ratio (decimal, e.g., 0.02 = 2%)
    cost_factor: float = 1.0  # Relative cost multiplier


# Concrete strength options (MPa)
CONCRETE_STRENGTHS = [21, 24, 28, 32, 35, 40, 45]

# Rebar percentage options (%)
REBAR_PERCENTAGES = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

# Approximate costs (PHP per unit)
CONCRETE_COSTS = {  # per m³
    21: 4000,
    24: 4200, 
    28: 4500,
    32: 5000,
    35: 5500,
    40: 6200,
    45: 7000,
}

STEEL_COST_PER_KG = 65  # PHP per kg
STEEL_DENSITY = 7850    # kg/m³


class MaterialAnalysis:
    """
    Structural analysis for FIXED member sizes.
    Optimizes material properties instead of dimensions.
    """
    
    def __init__(
        self,
        column: FixedMember,
        beam: FixedMember,
        slab_thickness: float,  # mm (fixed)
        width: float,   # Structure width (m)
        length: float,  # Structure length (m)
        height: float,  # Story height (m)
        dead_load: float = 5.0,   # kPa
        live_load: float = 2.0,   # kPa
        soil_bearing: float = 100.0,  # kPa
    ):
        self.column = column
        self.beam = beam
        self.slab_thickness = slab_thickness
        self.width = width
        self.length = length
        self.height = height
        self.dead_load = dead_load
        self.live_load = live_load
        self.soil_bearing = soil_bearing
        
        # Calculated properties
        self.slab_area = width * length
        self.fy = 415.0  # Steel yield strength (MPa)
    
    def slab_self_weight(self) -> float:
        """Slab self-weight (kPa)"""
        return (self.slab_thickness / 1000) * 24.0
    
    def total_factored_load(self) -> float:
        """Total factored load (kPa)"""
        slab_weight = self.slab_self_weight()
        return 1.2 * (self.dead_load + slab_weight) + 1.6 * self.live_load
    
    def column_factored_load(self) -> float:
        """Factored axial load per column (kN)"""
        return self.total_factored_load() * self.slab_area / 4
    
    def max_beam_moment(self) -> float:
        """Maximum beam moment (kN·m)"""
        trib_width = max(self.width, self.length) / 2
        w = self.total_factored_load() * trib_width
        span = max(self.width, self.length)
        return w * span**2 / 8
    
    # ========== CAPACITY CALCULATIONS ==========
    
    def column_capacity(self, fc: float, rho: float) -> float:
        """
        Column axial capacity (kN) with given material properties.
        Pu = φ × 0.80 × [0.85 × f'c × (Ag - Ast) + fy × Ast]
        """
        phi = 0.65  # Tied column
        Ag = self.column.width * self.column.depth  # mm²
        Ast = rho * Ag
        capacity = phi * 0.80 * (0.85 * fc * (Ag - Ast) + self.fy * Ast)
        return capacity / 1000  # kN
    
    def column_stress_ratio(self, fc: float, rho: float) -> float:
        """Demand/Capacity ratio for column"""
        demand = self.column_factored_load()
        capacity = self.column_capacity(fc, rho)
        return demand / capacity if capacity > 0 else float('inf')
    
    def beam_capacity(self, fc: float, rho: float) -> float:
        """
        Beam moment capacity (kN·m) with given material properties.
        Mu = φ × As × fy × (d - a/2)
        """
        phi = 0.90
        b = self.beam.width
        d = self.beam.depth - 50  # Effective depth
        As = rho * b * d
        a = (As * self.fy) / (0.85 * fc * b)
        Mn = As * self.fy * (d - a/2)
        return phi * Mn / 1e6  # kN·m
    
    def beam_stress_ratio(self, fc: float, rho: float) -> float:
        """Demand/Capacity ratio for beam"""
        demand = self.max_beam_moment()
        capacity = self.beam_capacity(fc, rho)
        return demand / capacity if capacity > 0 else float('inf')
    
    def beam_deflection_check(self) -> bool:
        """Deflection check based on span/depth ratio"""
        max_span = max(self.width, self.length) * 1000  # mm
        min_depth = max_span / 16  # Simply supported
        return self.beam.depth >= min_depth
    
    # ========== COST CALCULATIONS ==========
    
    def concrete_volume(self) -> float:
        """Total concrete volume (m³)"""
        # Slab
        slab_vol = self.slab_area * (self.slab_thickness / 1000)
        
        # Columns (4)
        col_vol = 4 * (self.column.width/1000) * (self.column.depth/1000) * self.height
        
        # Beams (4)
        beam_drop = (self.beam.depth - self.slab_thickness) / 1000
        beam_width_m = self.beam.width / 1000
        beam_vol = beam_width_m * beam_drop * (2*self.width + 2*self.length)
        
        return slab_vol + col_vol + beam_vol
    
    def steel_weight(self, col_rho: float, beam_rho: float, slab_rho: float = 0.003) -> float:
        """Total steel weight (kg)"""
        # Column steel
        col_vol = 4 * (self.column.width/1000) * (self.column.depth/1000) * self.height
        col_steel = col_rho * col_vol * STEEL_DENSITY
        
        # Beam steel  
        beam_drop = (self.beam.depth - self.slab_thickness) / 1000
        beam_width_m = self.beam.width / 1000
        beam_vol = beam_width_m * beam_drop * (2*self.width + 2*self.length)
        beam_steel = beam_rho * beam_vol * STEEL_DENSITY
        
        # Slab steel (mesh)
        slab_vol = self.slab_area * (self.slab_thickness / 1000)
        slab_steel = slab_rho * slab_vol * STEEL_DENSITY
        
        return col_steel + beam_steel + slab_steel
    
    def total_cost(self, fc: float, col_rho: float, beam_rho: float) -> float:
        """Total material cost (PHP)"""
        concrete_vol = self.concrete_volume()
        concrete_cost = concrete_vol * CONCRETE_COSTS.get(fc, 4500)
        
        steel_wt = self.steel_weight(col_rho, beam_rho)
        steel_cost = steel_wt * STEEL_COST_PER_KG
        
        return concrete_cost + steel_cost


class MaterialQUBOEncoder:
    """
    QUBO encoder for material optimization.
    Variables: f'c options × rho options for each member
    """
    
    def __init__(self, analysis: MaterialAnalysis):
        self.analysis = analysis
        
        # Material options
        self.fc_options = CONCRETE_STRENGTHS
        self.rho_options = REBAR_PERCENTAGES
        
        # Number of options
        self.n_fc = len(self.fc_options)
        self.n_rho = len(self.rho_options)
        
        # Variables: fc + col_rho + beam_rho = 7 + 7 + 7 = 21 qubits
        self.n_vars = self.n_fc + 2 * self.n_rho
        
        # Variable indices
        self.fc_start = 0
        self.col_rho_start = self.n_fc
        self.beam_rho_start = self.n_fc + self.n_rho
        
        # Penalty weights
        self.lambda_onehot = 5000
        self.lambda_stress = 2000
        self.lambda_ductility = 1000
    
    def encode(self) -> Tuple[np.ndarray, Dict]:
        """Encode the material optimization problem as QUBO"""
        Q = np.zeros((self.n_vars, self.n_vars))
        
        # 1. Objective: Minimize cost
        self._add_cost_objective(Q)
        
        # 2. One-hot constraints (exactly one option per variable)
        self._add_onehot_constraints(Q)
        
        # 3. Structural constraints
        self._add_stress_constraints(Q)
        
        # 4. Ductility constraints (rho limits)
        self._add_ductility_constraints(Q)
        
        metadata = {
            'n_vars': self.n_vars,
            'n_fc': self.n_fc,
            'n_rho': self.n_rho,
            'fc_options': self.fc_options,
            'rho_options': self.rho_options,
        }
        
        return Q, metadata
    
    def _add_cost_objective(self, Q: np.ndarray):
        """Add cost minimization objective"""
        # Cost depends on f'c and steel percentages
        for i, fc in enumerate(self.fc_options):
            idx = self.fc_start + i
            # Linear cost term for concrete
            concrete_vol = self.analysis.concrete_volume()
            Q[idx, idx] += CONCRETE_COSTS.get(fc, 4500) * concrete_vol / 10000
        
        for j, rho in enumerate(self.rho_options):
            # Column rebar cost
            col_idx = self.col_rho_start + j
            col_steel = (rho/100) * self.analysis.concrete_volume() / 2 * STEEL_DENSITY
            Q[col_idx, col_idx] += col_steel * STEEL_COST_PER_KG / 1000
            
            # Beam rebar cost
            beam_idx = self.beam_rho_start + j
            beam_steel = (rho/100) * self.analysis.concrete_volume() / 2 * STEEL_DENSITY
            Q[beam_idx, beam_idx] += beam_steel * STEEL_COST_PER_KG / 1000
    
    def _add_onehot_constraints(self, Q: np.ndarray):
        """Add one-hot selection constraints"""
        # f'c: exactly one
        for i in range(self.n_fc):
            Q[self.fc_start + i, self.fc_start + i] -= self.lambda_onehot
            for j in range(i + 1, self.n_fc):
                Q[self.fc_start + i, self.fc_start + j] += 2 * self.lambda_onehot
        
        # Column rho: exactly one
        for i in range(self.n_rho):
            Q[self.col_rho_start + i, self.col_rho_start + i] -= self.lambda_onehot
            for j in range(i + 1, self.n_rho):
                Q[self.col_rho_start + i, self.col_rho_start + j] += 2 * self.lambda_onehot
        
        # Beam rho: exactly one
        for i in range(self.n_rho):
            Q[self.beam_rho_start + i, self.beam_rho_start + i] -= self.lambda_onehot
            for j in range(i + 1, self.n_rho):
                Q[self.beam_rho_start + i, self.beam_rho_start + j] += 2 * self.lambda_onehot
    
    def _add_stress_constraints(self, Q: np.ndarray):
        """Add stress ratio penalty constraints"""
        # For each combination of f'c and rho, add penalty if stress ratio > 0.95
        for i, fc in enumerate(self.fc_options):
            for j, rho in enumerate(self.rho_options):
                # Column check
                col_ratio = self.analysis.column_stress_ratio(fc, rho/100)
                if col_ratio > 0.95:
                    penalty = self.lambda_stress * (col_ratio - 0.95)**2
                    # Penalty applies when both fc[i] and col_rho[j] are selected
                    fc_idx = self.fc_start + i
                    rho_idx = self.col_rho_start + j
                    Q[fc_idx, rho_idx] += penalty
                
                # Beam check
                beam_ratio = self.analysis.beam_stress_ratio(fc, rho/100)
                if beam_ratio > 0.95:
                    penalty = self.lambda_stress * (beam_ratio - 0.95)**2
                    fc_idx = self.fc_start + i
                    rho_idx = self.beam_rho_start + j
                    Q[fc_idx, rho_idx] += penalty
    
    def _add_ductility_constraints(self, Q: np.ndarray):
        """Add ductility constraints (min/max rho per NSCP)"""
        # NSCP: ρ_min = 1%, ρ_max = 4%
        # These are already within our options, so just penalize edge cases
        for j, rho in enumerate(self.rho_options):
            if rho < 1.0 or rho > 4.0:
                Q[self.col_rho_start + j, self.col_rho_start + j] += self.lambda_ductility
                Q[self.beam_rho_start + j, self.beam_rho_start + j] += self.lambda_ductility
    
    def decode_solution(self, x: np.ndarray) -> Dict:
        """Decode binary solution to material properties"""
        # Find selected options
        fc_idx = np.argmax(x[self.fc_start:self.fc_start + self.n_fc])
        col_rho_idx = np.argmax(x[self.col_rho_start:self.col_rho_start + self.n_rho])
        beam_rho_idx = np.argmax(x[self.beam_rho_start:self.beam_rho_start + self.n_rho])
        
        fc = self.fc_options[fc_idx]
        col_rho = self.rho_options[col_rho_idx] / 100
        beam_rho = self.rho_options[beam_rho_idx] / 100
        
        # Calculate results
        col_ratio = self.analysis.column_stress_ratio(fc, col_rho)
        beam_ratio = self.analysis.beam_stress_ratio(fc, beam_rho)
        total_cost = self.analysis.total_cost(fc, col_rho, beam_rho)
        
        return {
            'fc': fc,
            'col_rho_percent': col_rho * 100,
            'beam_rho_percent': beam_rho * 100,
            'column_stress_ratio': col_ratio,
            'beam_stress_ratio': beam_ratio,
            'total_cost_php': total_cost,
            'concrete_volume_m3': self.analysis.concrete_volume(),
            'steel_weight_kg': self.analysis.steel_weight(col_rho, beam_rho),
            'all_checks_pass': col_ratio <= 0.95 and beam_ratio <= 0.95,
        }


# Convenience function
def optimize_materials(
    column_width: float,
    column_depth: float,
    beam_width: float,
    beam_depth: float,
    slab_thickness: float,
    width: float,
    length: float,
    height: float,
    use_quantum: bool = False
) -> Dict:
    """
    Optimize material properties for fixed member sizes.
    
    Args:
        column_width, column_depth: Column dimensions (mm)
        beam_width, beam_depth: Beam dimensions (mm)
        slab_thickness: Slab thickness (mm)
        width, length, height: Structure dimensions (m)
        use_quantum: Use BlueQubit quantum solver
    
    Returns:
        Optimized material properties and costs
    """
    column = FixedMember(column_width, column_depth, "Column")
    beam = FixedMember(beam_width, beam_depth, "Beam")
    
    analysis = MaterialAnalysis(
        column=column,
        beam=beam,
        slab_thickness=slab_thickness,
        width=width,
        length=length,
        height=height,
    )
    
    encoder = MaterialQUBOEncoder(analysis)
    Q, metadata = encoder.encode()
    
    print("\n" + "="*60)
    print("🔮 Material Optimizer (Phase 2)")
    print("="*60)
    print(f"\n📐 Fixed Sizes:")
    print(f"   Column: {column_width}×{column_depth}mm")
    print(f"   Beam: {beam_width}×{beam_depth}mm")
    print(f"   Slab: {slab_thickness}mm")
    print(f"\n⚛️ QUBO Variables: {metadata['n_vars']} (f'c + col_ρ + beam_ρ)")
    
    # Solve (classical for now)
    from optimizer import QuantumOptimizer
    temp_optimizer = QuantumOptimizer.__new__(QuantumOptimizer)
    temp_optimizer.config = type('obj', (object,), {'num_reads': 100})()
    solution = temp_optimizer._solve_classical(Q, 100)
    
    result = encoder.decode_solution(solution)
    
    print(f"\n✅ OPTIMAL MATERIALS:")
    print(f"   Concrete: f'c = {result['fc']} MPa")
    print(f"   Column ρ = {result['col_rho_percent']:.1f}%")
    print(f"   Beam ρ = {result['beam_rho_percent']:.1f}%")
    print(f"\n💰 COST ESTIMATE: ₱{result['total_cost_php']:,.0f}")
    print(f"   Concrete: {result['concrete_volume_m3']:.2f} m³")
    print(f"   Steel: {result['steel_weight_kg']:.1f} kg")
    
    return result


if __name__ == "__main__":
    # Example: 200×200mm column flush with 20cm CHB
    result = optimize_materials(
        column_width=200,
        column_depth=200,
        beam_width=200,
        beam_depth=350,
        slab_thickness=125,
        width=4.0,
        length=5.0,
        height=3.0,
    )
