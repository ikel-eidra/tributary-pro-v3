"""
QUBO Encoder for Structural Optimization
Converts structural member sizing problem to Quadratic Unconstrained Binary Optimization format
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from structural_analysis import (
    StructuralAnalysis, MemberSize,
    COLUMN_SIZES, BEAM_SIZES, SLAB_THICKNESSES, FOOTING_SIZES
)


@dataclass
class QUBOConfig:
    """Configuration for QUBO problem"""
    # Penalty multipliers for constraint violations
    penalty_stress: float = 1000.0      # Stress constraint violation
    penalty_deflection: float = 500.0   # Deflection constraint violation
    penalty_one_hot: float = 2000.0     # One-hot encoding violation
    penalty_bearing: float = 800.0      # Soil bearing constraint
    
    # Thresholds
    max_stress_ratio: float = 0.95      # Demand/Capacity < 0.95
    max_deflection_ratio: float = 1.0   # Must satisfy minimum depth


class QUBOEncoder:
    """
    Encode structural optimization problem as QUBO matrix.
    
    Variables:
    - Column size: n_col binary variables (one-hot)
    - Beam size: n_beam binary variables (one-hot)
    - Slab thickness: n_slab binary variables (one-hot)
    - Footing size: n_ftg binary variables (one-hot)
    
    Objective: Minimize total concrete volume
    
    Constraints (as penalties):
    1. One-hot: Exactly one size selected per member type
    2. Stress: Demand/Capacity <= max_ratio
    3. Deflection: Minimum depth satisfied
    4. Bearing: Soil pressure <= allowable
    """
    
    def __init__(self, analysis: StructuralAnalysis, config: QUBOConfig = None):
        self.analysis = analysis
        self.config = config or QUBOConfig()
        
        # Member options
        self.column_options = COLUMN_SIZES
        self.beam_options = BEAM_SIZES
        self.slab_options = SLAB_THICKNESSES
        self.footing_options = FOOTING_SIZES
        
        # Variable indices
        self.n_col = len(self.column_options)
        self.n_beam = len(self.beam_options)
        self.n_slab = len(self.slab_options)
        self.n_ftg = len(self.footing_options)
        self.n_vars = self.n_col + self.n_beam + self.n_slab + self.n_ftg
        
        # Variable index ranges
        self.col_start = 0
        self.beam_start = self.n_col
        self.slab_start = self.beam_start + self.n_beam
        self.ftg_start = self.slab_start + self.n_slab
    
    def get_variable_indices(self) -> Dict[str, Tuple[int, int]]:
        """Get start and end indices for each member type"""
        return {
            'columns': (self.col_start, self.col_start + self.n_col),
            'beams': (self.beam_start, self.beam_start + self.n_beam),
            'slabs': (self.slab_start, self.slab_start + self.n_slab),
            'footings': (self.ftg_start, self.ftg_start + self.n_ftg),
        }
    
    def _calculate_volumes(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Calculate concrete volume for each option"""
        # Column volumes (for 4 columns)
        col_vols = np.array([
            self.analysis.column_volume(size) for size in self.column_options
        ])
        
        # Beam volumes (need slab thickness - use average)
        avg_slab = np.mean(self.slab_options)
        beam_vols = np.array([
            self.analysis.beam_volume(size, avg_slab) for size in self.beam_options
        ])
        
        # Slab volumes
        slab_vols = np.array([
            self.analysis.slab_volume(t) for t in self.slab_options
        ])
        
        # Footing volumes
        ftg_vols = np.array([
            self.analysis.footing_volume(size) for size in self.footing_options
        ])
        
        return col_vols, beam_vols, slab_vols, ftg_vols
    
    def _add_one_hot_penalty(self, Q: np.ndarray, start: int, n: int):
        """
        Add one-hot encoding constraint: sum(x_i) = 1
        Penalty: λ × (sum(x_i) - 1)²
               = λ × (sum(x_i)² - 2×sum(x_i) + 1)
               = λ × (sum_i(x_i²) + 2×sum_{i<j}(x_i×x_j) - 2×sum(x_i) + 1)
        
        Since x_i is binary: x_i² = x_i
        Linear terms go on diagonal, quadratic on off-diagonal
        """
        lam = self.config.penalty_one_hot
        
        # Diagonal: λ × (1 - 2) = -λ for each variable
        for i in range(start, start + n):
            Q[i, i] -= lam
        
        # Off-diagonal: 2λ for each pair
        for i in range(start, start + n):
            for j in range(i + 1, start + n):
                Q[i, j] += 2 * lam
    
    def _add_stress_constraints(self, Q: np.ndarray):
        """
        Add stress constraint penalties.
        For each column-slab combination: check stress ratio
        Penalty if stress_ratio > max_ratio
        """
        lam = self.config.penalty_stress
        max_ratio = self.config.max_stress_ratio
        
        # Column stress constraints (depends on column size and slab thickness)
        for ic, col in enumerate(self.column_options):
            for is_, slab_t in enumerate(self.slab_options):
                ratio = self.analysis.column_stress_ratio(col, slab_t)
                
                if ratio > max_ratio:
                    # Penalize this combination
                    violation = ratio - max_ratio
                    penalty = lam * violation ** 2
                    
                    # Add to Q[col_idx, slab_idx]
                    col_idx = self.col_start + ic
                    slab_idx = self.slab_start + is_
                    Q[col_idx, slab_idx] += penalty
        
        # Beam stress constraints (depends on beam size and slab thickness)
        for ib, beam in enumerate(self.beam_options):
            for is_, slab_t in enumerate(self.slab_options):
                ratio = self.analysis.beam_stress_ratio(beam, slab_t)
                
                if ratio > max_ratio:
                    violation = ratio - max_ratio
                    penalty = lam * violation ** 2
                    
                    beam_idx = self.beam_start + ib
                    slab_idx = self.slab_start + is_
                    Q[beam_idx, slab_idx] += penalty
    
    def _add_deflection_constraints(self, Q: np.ndarray):
        """
        Add deflection constraint penalties.
        Beam depth must satisfy minimum depth for span.
        """
        lam = self.config.penalty_deflection
        max_ratio = self.config.max_deflection_ratio
        
        for ib, beam in enumerate(self.beam_options):
            ratio = self.analysis.beam_deflection_ratio(beam)
            
            if ratio > max_ratio:
                violation = ratio - max_ratio
                penalty = lam * violation ** 2
                
                # Add to diagonal (unconditional penalty for this beam size)
                beam_idx = self.beam_start + ib
                Q[beam_idx, beam_idx] += penalty
    
    def _add_bearing_constraints(self, Q: np.ndarray):
        """
        Add footing bearing capacity constraints.
        Soil pressure must not exceed allowable.
        """
        lam = self.config.penalty_bearing
        
        for ift, ftg in enumerate(self.footing_options):
            for is_, slab_t in enumerate(self.slab_options):
                ratio = self.analysis.footing_stress_ratio(ftg, slab_t)
                
                if ratio > 1.0:  # Overstressed
                    violation = ratio - 1.0
                    penalty = lam * violation ** 2
                    
                    ftg_idx = self.ftg_start + ift
                    slab_idx = self.slab_start + is_
                    Q[ftg_idx, slab_idx] += penalty
    
    def encode(self) -> Tuple[np.ndarray, Dict]:
        """
        Encode the full QUBO problem.
        
        Returns:
            Q: QUBO matrix (symmetric)
            metadata: Information about the encoding
        """
        # Initialize QUBO matrix
        Q = np.zeros((self.n_vars, self.n_vars))
        
        # Calculate volumes for objective function
        col_vols, beam_vols, slab_vols, ftg_vols = self._calculate_volumes()
        
        # Objective: Minimize total volume (add to diagonal)
        # Scale volumes to be comparable magnitude
        vol_scale = 10.0  # Scaling factor
        
        for i, vol in enumerate(col_vols):
            Q[self.col_start + i, self.col_start + i] += vol * vol_scale
        
        for i, vol in enumerate(beam_vols):
            Q[self.beam_start + i, self.beam_start + i] += vol * vol_scale
        
        for i, vol in enumerate(slab_vols):
            Q[self.slab_start + i, self.slab_start + i] += vol * vol_scale
        
        for i, vol in enumerate(ftg_vols):
            Q[self.ftg_start + i, self.ftg_start + i] += vol * vol_scale
        
        # Add constraints as penalties
        self._add_one_hot_penalty(Q, self.col_start, self.n_col)
        self._add_one_hot_penalty(Q, self.beam_start, self.n_beam)
        self._add_one_hot_penalty(Q, self.slab_start, self.n_slab)
        self._add_one_hot_penalty(Q, self.ftg_start, self.n_ftg)
        
        self._add_stress_constraints(Q)
        self._add_deflection_constraints(Q)
        self._add_bearing_constraints(Q)
        
        # Make symmetric (QUBO convention: upper triangular, but we store full)
        Q = (Q + Q.T) / 2
        
        # Metadata
        metadata = {
            'n_vars': self.n_vars,
            'variable_indices': self.get_variable_indices(),
            'column_options': [(s.width, s.depth) for s in self.column_options],
            'beam_options': [(s.width, s.depth) for s in self.beam_options],
            'slab_options': self.slab_options,
            'footing_options': [(s.width, s.depth) for s in self.footing_options],
            'volumes': {
                'columns': col_vols.tolist(),
                'beams': beam_vols.tolist(),
                'slabs': slab_vols.tolist(),
                'footings': ftg_vols.tolist(),
            }
        }
        
        return Q, metadata
    
    def decode_solution(self, x: np.ndarray) -> Dict:
        """
        Decode binary solution vector to member sizes.
        
        Args:
            x: Binary solution vector of length n_vars
            
        Returns:
            Dictionary with selected member sizes
        """
        indices = self.get_variable_indices()
        
        # Find selected options (index of 1 in each segment)
        col_idx = np.argmax(x[indices['columns'][0]:indices['columns'][1]])
        beam_idx = np.argmax(x[indices['beams'][0]:indices['beams'][1]])
        slab_idx = np.argmax(x[indices['slabs'][0]:indices['slabs'][1]])
        ftg_idx = np.argmax(x[indices['footings'][0]:indices['footings'][1]])
        
        column = self.column_options[col_idx]
        beam = self.beam_options[beam_idx]
        slab = self.slab_options[slab_idx]
        footing = self.footing_options[ftg_idx]
        
        # Calculate total volume
        total_vol = self.analysis.total_concrete_volume(column, beam, slab, footing)
        
        # Check constraints
        col_ratio = self.analysis.column_stress_ratio(column, slab)
        beam_ratio = self.analysis.beam_stress_ratio(beam, slab)
        ftg_ratio = self.analysis.footing_stress_ratio(footing, slab)
        defl_ratio = self.analysis.beam_deflection_ratio(beam)
        
        return {
            'column': {'width': column.width, 'depth': column.depth},
            'beam': {'width': beam.width, 'depth': beam.depth},
            'slab_thickness': slab,
            'footing': {'width': footing.width, 'depth': footing.depth},
            'total_volume_m3': total_vol,
            'total_weight_kN': total_vol * 24.0,
            'checks': {
                'column_stress_ratio': col_ratio,
                'beam_stress_ratio': beam_ratio,
                'footing_bearing_ratio': ftg_ratio,
                'beam_deflection_ratio': defl_ratio,
                'all_satisfied': all([
                    col_ratio <= 0.95,
                    beam_ratio <= 0.95,
                    ftg_ratio <= 1.0,
                    defl_ratio <= 1.0,
                ])
            }
        }


def qubo_to_ising(Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Convert QUBO matrix to Ising model parameters.
    
    QUBO: x^T Q x  (x ∈ {0, 1})
    Ising: sum_i h_i s_i + sum_{i<j} J_ij s_i s_j + offset  (s ∈ {-1, +1})
    
    Transformation: x = (s + 1) / 2
    """
    n = Q.shape[0]
    
    # Make sure Q is symmetric
    Q = (Q + Q.T) / 2
    
    # Calculate Ising parameters
    h = np.zeros(n)
    J = np.zeros((n, n))
    offset = 0.0
    
    for i in range(n):
        h[i] = Q[i, i] / 2 + np.sum(Q[i, :]) / 4
        offset += Q[i, i] / 4
        
        for j in range(i + 1, n):
            J[i, j] = Q[i, j] / 4
            offset += Q[i, j] / 4
    
    return h, J, offset


if __name__ == "__main__":
    # Test QUBO encoding
    from structural_analysis import StructuralAnalysis
    
    analysis = StructuralAnalysis(width=4.0, length=5.0, height=3.0, soil_bearing=100.0)
    encoder = QUBOEncoder(analysis)
    
    Q, metadata = encoder.encode()
    
    print(f"QUBO matrix shape: {Q.shape}")
    print(f"Total variables: {metadata['n_vars']}")
    print(f"Variable indices: {metadata['variable_indices']}")
    print(f"\nQ matrix sample (first 5x5):")
    print(Q[:5, :5])
