"""
Flask API Backend for Quantum Structural Optimizer
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

from optimizer import QuantumOptimizer, OptimizerConfig
from structural_analysis import (
    StructuralAnalysis, Material, Load,
    COLUMN_SIZES, BEAM_SIZES, SLAB_THICKNESSES, FOOTING_SIZES
)

# Load environment
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    has_token = bool(os.getenv("BLUEQUBIT_API_TOKEN"))
    return jsonify({
        'status': 'ok',
        'bluequbit_configured': has_token,
        'message': 'Quantum Structural Optimizer API is running'
    })


@app.route('/api/options', methods=['GET'])
def get_options():
    """Get available member size options"""
    return jsonify({
        'columns': [{'width': s.width, 'depth': s.depth} for s in COLUMN_SIZES],
        'beams': [{'width': s.width, 'depth': s.depth} for s in BEAM_SIZES],
        'slabs': SLAB_THICKNESSES,
        'footings': [{'width': s.width, 'depth': s.depth} for s in FOOTING_SIZES],
    })


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Analyze structure with given member sizes (no optimization).
    Returns volumes, stresses, and constraint checks.
    """
    data = request.get_json()
    
    # Parse structure parameters
    width = float(data.get('width', 4.0))
    length = float(data.get('length', 5.0))
    height = float(data.get('height', 3.0))
    fc = float(data.get('fc', 28.0))
    fy = float(data.get('fy', 415.0))
    dead_load = float(data.get('dead_load', 5.0))
    live_load = float(data.get('live_load', 2.0))
    soil_bearing = float(data.get('soil_bearing', 100.0))
    
    # Parse member sizes
    col_size = data.get('column', {'width': 300, 'depth': 300})
    beam_size = data.get('beam', {'width': 250, 'depth': 400})
    slab_t = float(data.get('slab', 150))
    ftg_size = data.get('footing', {'width': 1000, 'depth': 1000})
    
    # Create analysis
    from structural_analysis import MemberSize
    material = Material(fc=fc, fy=fy)
    load = Load(dead=dead_load, live=live_load)
    
    analysis = StructuralAnalysis(
        width=width, length=length, height=height,
        material=material, load=load, soil_bearing=soil_bearing
    )
    
    column = MemberSize(col_size['width'], col_size['depth'])
    beam = MemberSize(beam_size['width'], beam_size['depth'])
    footing = MemberSize(ftg_size['width'], ftg_size['depth'])
    
    # Calculate results
    total_vol = analysis.total_concrete_volume(column, beam, slab_t, footing)
    col_ratio = analysis.column_stress_ratio(column, slab_t)
    beam_ratio = analysis.beam_stress_ratio(beam, slab_t)
    ftg_ratio = analysis.footing_stress_ratio(footing, slab_t)
    defl_ratio = analysis.beam_deflection_ratio(beam)
    
    return jsonify({
        'structure': {
            'width': width,
            'length': length,
            'height': height,
            'slab_area': analysis.slab_area,
        },
        'loads': {
            'column_service': analysis.column_load(slab_t),
            'column_factored': analysis.column_factored_load(slab_t),
            'max_beam_moment': analysis.max_beam_moment(slab_t),
        },
        'volumes': {
            'slab': analysis.slab_volume(slab_t),
            'columns': analysis.column_volume(column),
            'beams': analysis.beam_volume(beam, slab_t),
            'footings': analysis.footing_volume(footing),
            'total': total_vol,
        },
        'weight_kN': total_vol * 24.0,
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
    })


@app.route('/api/optimize', methods=['POST'])
def optimize():
    """
    Run quantum/classical optimization to find optimal member sizes.
    """
    data = request.get_json()
    
    # Parse parameters
    config = OptimizerConfig(
        width=float(data.get('width', 4.0)),
        length=float(data.get('length', 5.0)),
        height=float(data.get('height', 3.0)),
        fc=float(data.get('fc', 28.0)),
        fy=float(data.get('fy', 415.0)),
        dead_load=float(data.get('dead_load', 5.0)),
        live_load=float(data.get('live_load', 2.0)),
        soil_bearing=float(data.get('soil_bearing', 100.0)),
        use_quantum=bool(data.get('use_quantum', False)),
        num_reads=int(data.get('num_reads', 100)),
    )
    
    # Run optimizer
    optimizer = QuantumOptimizer(config)
    result = optimizer.compare_with_defaults()
    
    return jsonify({
        'success': True,
        'quantum_used': config.use_quantum and bool(os.getenv("BLUEQUBIT_API_TOKEN")),
        'default_volume': result['default_volume'],
        'optimized': result['optimized_design'],
        'savings': {
            'volume_m3': result['savings_m3'],
            'percent': result['savings_percent'],
            'cost_estimate_php': result['savings_m3'] * 5000,  # Rough estimate ₱5000/m³
        }
    })


@app.route('/api/optimize-materials', methods=['POST'])
def optimize_materials():
    """
    Phase 2: Optimize materials (f'c and rebar %) for FIXED member sizes.
    Use when architectural constraints lock member dimensions (e.g., flush with CHB).
    """
    from material_optimizer import (
        MaterialAnalysis, MaterialQUBOEncoder, FixedMember,
        CONCRETE_STRENGTHS, REBAR_PERCENTAGES
    )
    
    data = request.get_json()
    
    # Parse fixed member sizes
    column = FixedMember(
        width=float(data.get('column_width', 200)),
        depth=float(data.get('column_depth', 200)),
        name="Column"
    )
    beam = FixedMember(
        width=float(data.get('beam_width', 200)),
        depth=float(data.get('beam_depth', 350)),
        name="Beam"
    )
    slab_thickness = float(data.get('slab_thickness', 125))
    
    # Structure dimensions
    width = float(data.get('width', 4.0))
    length = float(data.get('length', 5.0))
    height = float(data.get('height', 3.0))
    
    # Create analysis
    analysis = MaterialAnalysis(
        column=column,
        beam=beam,
        slab_thickness=slab_thickness,
        width=width,
        length=length,
        height=height,
        dead_load=float(data.get('dead_load', 5.0)),
        live_load=float(data.get('live_load', 2.0)),
        soil_bearing=float(data.get('soil_bearing', 100.0)),
    )
    
    # Encode and solve
    encoder = MaterialQUBOEncoder(analysis)
    Q, metadata = encoder.encode()
    
    # Use quantum or classical solver
    use_quantum = bool(data.get('use_quantum', False))
    
    if use_quantum and os.getenv("BLUEQUBIT_API_TOKEN"):
        # Use BlueQubit
        from optimizer import QuantumOptimizer, OptimizerConfig
        temp_config = OptimizerConfig(use_quantum=True)
        temp_opt = QuantumOptimizer(temp_config)
        solution = temp_opt._solve_quantum(Q)
    else:
        # Classical fallback
        from optimizer import QuantumOptimizer, OptimizerConfig
        temp_config = OptimizerConfig()
        temp_opt = QuantumOptimizer.__new__(QuantumOptimizer)
        temp_opt.config = temp_config
        solution = temp_opt._solve_classical(Q, 100)
    
    result = encoder.decode_solution(solution)
    
    # Calculate baseline cost (using f'c=28, rho=2%)
    baseline_cost = analysis.total_cost(28, 0.02, 0.02)
    savings = baseline_cost - result['total_cost_php']
    
    return jsonify({
        'success': True,
        'mode': 'material_optimization',
        'quantum_used': use_quantum and bool(os.getenv("BLUEQUBIT_API_TOKEN")),
        'fixed_sizes': {
            'column': {'width': column.width, 'depth': column.depth},
            'beam': {'width': beam.width, 'depth': beam.depth},
            'slab_thickness': slab_thickness,
        },
        'optimal_materials': {
            'fc_mpa': result['fc'],
            'column_rho_percent': result['col_rho_percent'],
            'beam_rho_percent': result['beam_rho_percent'],
        },
        'checks': {
            'column_stress_ratio': result['column_stress_ratio'],
            'beam_stress_ratio': result['beam_stress_ratio'],
            'all_pass': result['all_checks_pass'],
        },
        'cost': {
            'total_php': result['total_cost_php'],
            'concrete_volume_m3': result['concrete_volume_m3'],
            'steel_weight_kg': result['steel_weight_kg'],
            'baseline_php': baseline_cost,
            'savings_php': max(0, savings),
        },
        'options_available': {
            'fc_options': CONCRETE_STRENGTHS,
            'rho_options': REBAR_PERCENTAGES,
        }
    })


# Serve static files in production (the HTML UI)
@app.route('/')
def index():
    """Serve the main UI"""
    return app.send_static_file('quantum_optimizer.html')


if __name__ == '__main__':
    print("\n🚀 Starting Quantum Structural Optimizer API...")
    print("   Open http://localhost:5000 in your browser")
    print("   API docs: http://localhost:5000/api/health\n")
    
    app.run(debug=True, port=5000)
