"""
Precast Wall Panel System
Instead of small blocks, precast entire wall panels

Advantages:
1. Fewer joints = stronger, more waterproof
2. No mortar on site
3. Factory quality control
4. Faster installation (crane/forklift)
5. Easier molds (rectangular, no complex taper)
6. Integrated rebar cages
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math
import numpy as np


@dataclass
class PrecastPanel:
    """
    Precast wall panel with hollow cores.
    
    Standard sizes based on:
    - Transport limits (truck width ~2.4m max)
    - Crane capacity (typical 5-10 ton mobile)
    - Handling on site
    """
    # Dimensions (mm)
    width: float = 1000       # Along wall (1m module)
    height: float = 3000      # Floor-to-ceiling (3m story)
    thickness: float = 100    # Wall thickness
    
    # Hollow cores (vertical)
    n_cores: int = 4          # Number of cores
    core_diameter: float = 50 # mm
    
    # Edge connections
    connection_type: str = "tongue_groove"  # or "bolted", "grouted"
    
    # Material (HYBRID composite)
    density_kg_m3: float = 1350
    strength_mpa: float = 13
    
    # Reinforcement
    rebar_vertical: str = "4-12mm"     # 4 pcs of 12mm bars
    rebar_horizontal: str = "10mm@200" # 10mm bars every 200mm
    mesh_type: str = "6mm@150×150"     # Welded wire mesh
    
    def gross_volume(self) -> float:
        """Gross volume (mm³)"""
        return self.width * self.height * self.thickness
    
    def core_volume(self) -> float:
        """Volume of hollow cores (mm³)"""
        core_area = math.pi * (self.core_diameter / 2) ** 2
        return self.n_cores * core_area * self.height
    
    def net_volume(self) -> float:
        """Net concrete volume (mm³)"""
        return self.gross_volume() - self.core_volume()
    
    def solid_ratio(self) -> float:
        """Solid percentage"""
        return self.net_volume() / self.gross_volume()
    
    def weight_kg(self) -> float:
        """Panel weight in kg"""
        # Concrete + rebar
        concrete_weight = self.net_volume() / 1e9 * self.density_kg_m3
        # Estimate rebar at ~2% of concrete weight
        rebar_weight = concrete_weight * 0.02
        return concrete_weight + rebar_weight
    
    def weight_per_sqm(self) -> float:
        """Weight per m² of wall (kg/m²)"""
        area_sqm = (self.width / 1000) * (self.height / 1000)
        return self.weight_kg() / area_sqm
    
    def can_crane_lift(self, crane_capacity_kg: float = 5000) -> bool:
        """Check if standard crane can lift"""
        return self.weight_kg() <= crane_capacity_kg
    
    def truck_transport(self, truck_width_m: float = 2.4) -> Dict:
        """Check truck transport limits"""
        panel_width_m = self.width / 1000
        panels_per_row = int(truck_width_m / panel_width_m)
        
        return {
            "fits_width": panel_width_m <= truck_width_m,
            "panels_per_row": panels_per_row,
            "needs_escort": self.height / 1000 > 3.5,  # Over 3.5m needs escort
        }


# Standard panel sizes
STANDARD_PANELS = {
    "small_1x2.4": PrecastPanel(
        width=1000, height=2400, thickness=100,
        n_cores=3, core_diameter=50,
    ),
    "standard_1x3": PrecastPanel(
        width=1000, height=3000, thickness=100,
        n_cores=4, core_diameter=50,
    ),
    "wide_1.2x3": PrecastPanel(
        width=1200, height=3000, thickness=100,
        n_cores=5, core_diameter=50,
    ),
    "structural_1x3": PrecastPanel(
        width=1000, height=3000, thickness=150,
        n_cores=5, core_diameter=60,
    ),
}


@dataclass
class PanelConnection:
    """Connection details between panels"""
    name: str
    description: str
    strength_kn: float      # Shear capacity kN/m
    install_time_min: float # Minutes per joint
    waterproof: bool
    cost_per_m: float       # PHP per linear meter


CONNECTIONS = {
    "tongue_groove": PanelConnection(
        name="Tongue & Groove + Sealant",
        description="Interlocking edges with silicone sealant",
        strength_kn=15,
        install_time_min=5,
        waterproof=True,
        cost_per_m=150,
    ),
    "grouted": PanelConnection(
        name="Grouted Joint",
        description="25mm gap filled with non-shrink grout",
        strength_kn=40,
        install_time_min=15,
        waterproof=True,
        cost_per_m=280,
    ),
    "bolted": PanelConnection(
        name="Steel Angle + Bolts",
        description="L-angle with expansion bolts both sides",
        strength_kn=60,
        install_time_min=20,
        waterproof=False,  # Needs sealant
        cost_per_m=450,
    ),
    "welded_plate": PanelConnection(
        name="Weld Plates",
        description="Embedded steel plates welded on site",
        strength_kn=80,
        install_time_min=30,
        waterproof=False,
        cost_per_m=600,
    ),
}


class PrecastWallDesigner:
    """
    Design precast wall system for a building.
    """
    
    def __init__(
        self,
        wall_length: float,      # m
        wall_height: float,      # m
        is_structural: bool = False,
        seismic_zone: int = 4,   # Philippines is Zone 4
    ):
        self.wall_length = wall_length
        self.wall_height = wall_height
        self.is_structural = is_structural
        self.seismic_zone = seismic_zone
    
    def select_panel(self) -> PrecastPanel:
        """Select appropriate panel size"""
        if self.is_structural:
            return STANDARD_PANELS["structural_1x3"]
        elif self.wall_height <= 2.5:
            return STANDARD_PANELS["small_1x2.4"]
        else:
            return STANDARD_PANELS["standard_1x3"]
    
    def panel_layout(self, panel: PrecastPanel) -> Dict:
        """Calculate panel layout"""
        panel_width_m = panel.width / 1000
        panel_height_m = panel.height / 1000
        
        n_horizontal = math.ceil(self.wall_length / panel_width_m)
        n_vertical = math.ceil(self.wall_height / panel_height_m)
        
        total_panels = n_horizontal * n_vertical
        
        # Joints
        vertical_joints = (n_horizontal - 1) * self.wall_height
        horizontal_joints = n_horizontal * (n_vertical - 1) * panel_width_m
        total_joint_length = vertical_joints + horizontal_joints
        
        return {
            "panels_horizontal": n_horizontal,
            "panels_vertical": n_vertical,
            "total_panels": total_panels,
            "vertical_joint_length_m": vertical_joints,
            "horizontal_joint_length_m": horizontal_joints,
            "total_joint_length_m": total_joint_length,
        }
    
    def select_connection(self) -> PanelConnection:
        """Select appropriate connection type"""
        if self.seismic_zone >= 4 and self.is_structural:
            return CONNECTIONS["grouted"]
        elif self.is_structural:
            return CONNECTIONS["bolted"]
        else:
            return CONNECTIONS["tongue_groove"]
    
    def full_design(self) -> Dict:
        """Complete wall design"""
        panel = self.select_panel()
        layout = self.panel_layout(panel)
        connection = self.select_connection()
        
        # Costs
        panel_cost = 2500  # PHP per panel estimate
        total_panel_cost = layout["total_panels"] * panel_cost
        joint_cost = layout["total_joint_length_m"] * connection.cost_per_m
        
        # Weight
        total_weight = layout["total_panels"] * panel.weight_kg()
        
        # Installation time
        erection_time = layout["total_panels"] * 15  # 15 min per panel
        joint_time = layout["total_joint_length_m"] * connection.install_time_min
        total_time = erection_time + joint_time
        
        return {
            "panel": panel,
            "layout": layout,
            "connection": connection,
            "cost": {
                "panels": total_panel_cost,
                "joints": joint_cost,
                "total": total_panel_cost + joint_cost,
            },
            "weight": {
                "per_panel_kg": panel.weight_kg(),
                "total_kg": total_weight,
                "per_sqm": total_weight / (self.wall_length * self.wall_height),
            },
            "installation": {
                "erection_minutes": erection_time,
                "joints_minutes": joint_time,
                "total_minutes": total_time,
                "total_hours": total_time / 60,
            },
        }


def design_precast_wall(
    wall_length: float = 10.0,
    wall_height: float = 3.0,
    is_structural: bool = False,
) -> Dict:
    """
    Design a precast wall system.
    """
    designer = PrecastWallDesigner(wall_length, wall_height, is_structural)
    result = designer.full_design()
    
    panel = result["panel"]
    layout = result["layout"]
    conn = result["connection"]
    
    print("\n" + "="*60)
    print("🏗️ PRECAST WALL PANEL SYSTEM")
    print("="*60)
    print(f"\n📐 Wall: {wall_length}m × {wall_height}m")
    print(f"   Type: {'Structural' if is_structural else 'Non-structural'}")
    
    print(f"\n📦 PANEL SELECTED:")
    print(f"   Size: {panel.width}mm × {panel.height}mm × {panel.thickness}mm")
    print(f"   Weight: {panel.weight_kg():.0f}kg per panel")
    print(f"   Cores: {panel.n_cores} × Ø{panel.core_diameter}mm")
    print(f"   Crane lift: {'✓ OK' if panel.can_crane_lift() else '✗ Too heavy'}")
    
    print(f"\n📊 LAYOUT:")
    print(f"   Panels: {layout['total_panels']} ({layout['panels_horizontal']} × {layout['panels_vertical']})")
    print(f"   Vertical joints: {layout['vertical_joint_length_m']:.1f}m")
    print(f"   Horizontal joints: {layout['horizontal_joint_length_m']:.1f}m")
    
    print(f"\n🔗 CONNECTION:")
    print(f"   Type: {conn.name}")
    print(f"   Strength: {conn.strength_kn} kN/m")
    print(f"   Waterproof: {'Yes' if conn.waterproof else 'No'}")
    
    print(f"\n💰 COST ESTIMATE:")
    print(f"   Panels: ₱{result['cost']['panels']:,.0f}")
    print(f"   Joints: ₱{result['cost']['joints']:,.0f}")
    print(f"   Total: ₱{result['cost']['total']:,.0f}")
    print(f"   Per m²: ₱{result['cost']['total'] / (wall_length * wall_height):.0f}/m²")
    
    print(f"\n⏱️ INSTALLATION:")
    print(f"   Total: {result['installation']['total_hours']:.1f} hours")
    print(f"   ({result['installation']['total_minutes']:.0f} minutes)")
    
    # Compare to CHB
    chb_install_hours = wall_length * wall_height * 0.5  # ~0.5 hr/m²
    time_savings = (chb_install_hours - result['installation']['total_hours']) / chb_install_hours * 100
    print(f"\n📈 VS CHB CONSTRUCTION:")
    print(f"   Time savings: {time_savings:.0f}%")
    
    return result


if __name__ == "__main__":
    print("\n" + "="*60)
    print("EXAMPLE 1: Non-structural partition (10m × 3m)")
    print("="*60)
    design_precast_wall(10, 3, is_structural=False)
    
    print("\n" + "="*60)
    print("EXAMPLE 2: Structural wall (8m × 3m)")
    print("="*60)
    design_precast_wall(8, 3, is_structural=True)
