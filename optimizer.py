"""
BlueQubit Structural Optimizer
Main orchestrator that connects structural analysis, QUBO encoding, and quantum solving
"""

import os
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

from structural_analysis import StructuralAnalysis, Material, Load
from qubo_encoder import QUBOEncoder, QUBOConfig, qubo_to_ising


# Load environment variables
load_dotenv()


@dataclass
class OptimizerConfig:
    """Configuration for the quantum optimizer"""
    # Structure parameters
    width: float = 4.0        # m
    length: float = 5.0       # m
    height: float = 3.0       # m
    
    # Material properties
    fc: float = 28.0          # MPa
    fy: float = 415.0         # MPa
    
    # Loads
    dead_load: float = 5.0    # kPa
    live_load: float = 2.0    # kPa
    
    # Soil
    soil_bearing: float = 100.0  # kPa
    
    # Solver settings
    use_quantum: bool = True
    num_reads: int = 100      # Number of samples (for annealing)
    device: str = "cpu"       # BlueQubit device


class QuantumOptimizer:
    """
    Quantum-powered structural member optimizer.
    Uses BlueQubit API for quantum annealing or simulation.
    Falls back to classical simulated annealing if quantum unavailable.
    """
    
    def __init__(self, config: OptimizerConfig = None):
        self.config = config or OptimizerConfig()
        self.api_token = os.getenv("BLUEQUBIT_API_TOKEN")
        self._bq_client = None
        
        # Set up structural analysis
        material = Material(fc=self.config.fc, fy=self.config.fy)
        load = Load(dead=self.config.dead_load, live=self.config.live_load)
        
        self.analysis = StructuralAnalysis(
            width=self.config.width,
            length=self.config.length,
            height=self.config.height,
            material=material,
            load=load,
            soil_bearing=self.config.soil_bearing
        )
        
        # QUBO encoder
        self.encoder = QUBOEncoder(self.analysis)
    
    @property
    def bq_client(self):
        """Lazy initialization of BlueQubit client"""
        if self._bq_client is None and self.api_token:
            try:
                import bluequbit
                self._bq_client = bluequbit.init(self.api_token)
                print("✅ BlueQubit client initialized")
            except ImportError:
                print("⚠️ BlueQubit SDK not installed. Using classical simulation.")
            except Exception as e:
                print(f"⚠️ Failed to initialize BlueQubit: {e}")
        return self._bq_client
    
    def _solve_classical(self, Q: np.ndarray, num_reads: int = 100) -> np.ndarray:
        """
        Classical simulated annealing solver.
        Used as fallback when quantum is unavailable.
        """
        n = Q.shape[0]
        best_x = None
        best_energy = float('inf')
        
        for _ in range(num_reads):
            # Random initial state
            x = np.random.randint(0, 2, n)
            
            # Simple simulated annealing
            T = 100.0  # Initial temperature
            T_min = 0.01
            alpha = 0.95  # Cooling rate
            
            while T > T_min:
                # Calculate current energy
                current_energy = x @ Q @ x
                
                # Try flipping a random bit
                i = np.random.randint(n)
                x_new = x.copy()
                x_new[i] = 1 - x_new[i]
                new_energy = x_new @ Q @ x_new
                
                # Accept or reject
                delta = new_energy - current_energy
                if delta < 0 or np.random.random() < np.exp(-delta / T):
                    x = x_new
                
                T *= alpha
            
            # Check if this is best solution
            final_energy = x @ Q @ x
            if final_energy < best_energy:
                best_energy = final_energy
                best_x = x.copy()
        
        return best_x
    
    def _solve_quantum(self, Q: np.ndarray) -> np.ndarray:
        """
        Solve using BlueQubit quantum annealer/simulator.
        Converts QUBO to quantum circuit for variational solving.
        """
        if self.bq_client is None:
            print("⚠️ BlueQubit not available, falling back to classical")
            return self._solve_classical(Q, self.config.num_reads)
        
        try:
            import qiskit
            from qiskit.circuit.library import QAOAAnsatz
            from qiskit.quantum_info import SparsePauliOp
            
            # Convert QUBO to Ising Hamiltonian
            h, J, offset = qubo_to_ising(Q)
            n = len(h)
            
            # Build Pauli operator for the cost Hamiltonian
            pauli_list = []
            
            # Single-qubit terms (Z)
            for i in range(n):
                if abs(h[i]) > 1e-10:
                    pauli_str = 'I' * i + 'Z' + 'I' * (n - i - 1)
                    pauli_list.append((pauli_str, h[i]))
            
            # Two-qubit terms (ZZ)
            for i in range(n):
                for j in range(i + 1, n):
                    if abs(J[i, j]) > 1e-10:
                        pauli_str = list('I' * n)
                        pauli_str[i] = 'Z'
                        pauli_str[j] = 'Z'
                        pauli_list.append((''.join(pauli_str), J[i, j]))
            
            if not pauli_list:
                # Fallback if no terms
                pauli_list = [('I' * n, 1.0)]
            
            # Create Hamiltonian operator
            cost_op = SparsePauliOp.from_list(pauli_list)
            
            # Create QAOA circuit with 2 repetitions
            qaoa = QAOAAnsatz(cost_op, reps=2)
            
            # IMPORTANT: Bind parameters with optimized values
            # Using pre-computed angles that work well for most QUBO problems
            num_params = qaoa.num_parameters
            # Alternate between gamma (cost) and beta (mixer) angles
            param_values = []
            for i in range(num_params):
                if i % 2 == 0:
                    # Gamma angles (typically smaller)
                    param_values.append(0.5 + 0.1 * (i // 2))
                else:
                    # Beta angles
                    param_values.append(0.3 + 0.1 * (i // 2))
            
            # Bind parameters to circuit
            bound_circuit = qaoa.assign_parameters(param_values)
            
            # Prepare for measurement
            qc = qiskit.QuantumCircuit(n)
            qc.compose(bound_circuit, inplace=True)
            qc.measure_all()
            
            # Decompose to basic gates for BlueQubit
            decomposed = qc.decompose().decompose()
            
            print(f"   Sending {n}-qubit circuit to BlueQubit...")
            
            # Run on BlueQubit
            result = self.bq_client.run(
                decomposed,
                job_name="struct_opt",
                device=self.config.device
            )
            
            # Get most probable state
            counts = result.get_counts()
            best_bitstring = max(counts, key=counts.get)
            
            print(f"   ✅ BlueQubit returned: {best_bitstring}")
            
            # Convert to numpy array (reverse for qiskit convention)
            x = np.array([int(b) for b in best_bitstring[::-1]])
            
            return x
            
        except Exception as e:
            print(f"⚠️ Quantum solving failed: {e}")
            print("   Falling back to classical simulation")
            return self._solve_classical(Q, self.config.num_reads)
    
    def optimize(self) -> Dict:
        """
        Run the full optimization pipeline.
        
        Returns:
            Dictionary with optimized member sizes and analysis results
        """
        print("\n" + "="*60)
        print("🔮 BlueQubit Structural Member Optimizer")
        print("="*60)
        
        print(f"\n📐 Structure: {self.config.width}m × {self.config.length}m × {self.config.height}m")
        print(f"📊 Loads: DL={self.config.dead_load} kPa, LL={self.config.live_load} kPa")
        print(f"🏗️ Materials: f'c={self.config.fc} MPa, fy={self.config.fy} MPa")
        print(f"🌍 Soil: qa={self.config.soil_bearing} kPa")
        
        # Encode QUBO
        print("\n⚙️ Encoding optimization problem as QUBO...")
        Q, metadata = self.encoder.encode()
        print(f"   Variables: {metadata['n_vars']}")
        print(f"   - Columns: {len(metadata['column_options'])} options")
        print(f"   - Beams: {len(metadata['beam_options'])} options")
        print(f"   - Slabs: {len(metadata['slab_options'])} options")
        print(f"   - Footings: {len(metadata['footing_options'])} options")
        
        # Solve
        if self.config.use_quantum and self.api_token:
            print("\n⚛️ Solving with BlueQubit quantum optimizer...")
            solution = self._solve_quantum(Q)
        else:
            print("\n🖥️ Solving with classical simulated annealing...")
            solution = self._solve_classical(Q, self.config.num_reads)
        
        # Decode solution
        print("\n📋 Decoding optimized design...")
        result = self.encoder.decode_solution(solution)
        
        # Print results
        print("\n" + "="*60)
        print("✅ OPTIMIZATION COMPLETE")
        print("="*60)
        
        print(f"\n🏛️ COLUMNS: {result['column']['width']}mm × {result['column']['depth']}mm")
        print(f"📏 BEAMS: {result['beam']['width']}mm × {result['beam']['depth']}mm")
        print(f"📦 SLAB: {result['slab_thickness']}mm thick")
        print(f"🧱 FOOTINGS: {result['footing']['width']}mm × {result['footing']['depth']}mm")
        
        print(f"\n📊 Total Concrete: {result['total_volume_m3']:.2f} m³")
        print(f"⚖️ Total Weight: {result['total_weight_kN']:.1f} kN")
        
        print("\n🔍 CONSTRAINT CHECKS:")
        checks = result['checks']
        print(f"   Column stress ratio: {checks['column_stress_ratio']:.2f} {'✓' if checks['column_stress_ratio'] <= 0.95 else '✗'}")
        print(f"   Beam stress ratio: {checks['beam_stress_ratio']:.2f} {'✓' if checks['beam_stress_ratio'] <= 0.95 else '✗'}")
        print(f"   Footing bearing ratio: {checks['footing_bearing_ratio']:.2f} {'✓' if checks['footing_bearing_ratio'] <= 1.0 else '✗'}")
        print(f"   Beam deflection ratio: {checks['beam_deflection_ratio']:.2f} {'✓' if checks['beam_deflection_ratio'] <= 1.0 else '✗'}")
        
        status = "✅ ALL CONSTRAINTS SATISFIED" if checks['all_satisfied'] else "⚠️ SOME CONSTRAINTS VIOLATED"
        print(f"\n{status}")
        
        return result
    
    def compare_with_defaults(self) -> Dict:
        """
        Compare optimized design with default/typical sizes.
        """
        from structural_analysis import COLUMN_SIZES, BEAM_SIZES, SLAB_THICKNESSES, FOOTING_SIZES
        
        # Default: use mid-range sizes
        default_col = COLUMN_SIZES[2]  # 350x350
        default_beam = BEAM_SIZES[2]   # 300x450
        default_slab = SLAB_THICKNESSES[2]  # 150mm
        default_ftg = FOOTING_SIZES[2]      # 1200x1200
        
        default_vol = self.analysis.total_concrete_volume(
            default_col, default_beam, default_slab, default_ftg
        )
        
        # Run optimization
        optimized = self.optimize()
        
        savings = default_vol - optimized['total_volume_m3']
        savings_pct = (savings / default_vol) * 100 if default_vol > 0 else 0
        
        print(f"\n📊 COMPARISON:")
        print(f"   Default design: {default_vol:.2f} m³")
        print(f"   Optimized design: {optimized['total_volume_m3']:.2f} m³")
        print(f"   Savings: {savings:.2f} m³ ({savings_pct:.1f}%)")
        
        return {
            'default_volume': default_vol,
            'optimized_volume': optimized['total_volume_m3'],
            'savings_m3': savings,
            'savings_percent': savings_pct,
            'optimized_design': optimized,
        }


def run_optimization(
    width: float = 4.0,
    length: float = 5.0,
    height: float = 3.0,
    dead_load: float = 5.0,
    live_load: float = 2.0,
    fc: float = 28.0,
    soil_bearing: float = 100.0,
    use_quantum: bool = False
) -> Dict:
    """
    Convenience function to run optimization with specified parameters.
    """
    config = OptimizerConfig(
        width=width,
        length=length,
        height=height,
        dead_load=dead_load,
        live_load=live_load,
        fc=fc,
        soil_bearing=soil_bearing,
        use_quantum=use_quantum,
    )
    
    optimizer = QuantumOptimizer(config)
    return optimizer.compare_with_defaults()


if __name__ == "__main__":
    # Example usage
    result = run_optimization(
        width=4.0,
        length=5.0,
        height=3.0,
        dead_load=5.0,
        live_load=2.0,
        use_quantum=False  # Set to True if you have BlueQubit API token
    )
