"""
Philippine Suppliers Database for Construction Materials
Fly Ash, Rice Hull Ash, Volcanic Pumice, and other composites

Last Updated: December 2024
"""

# ========== FLY ASH SUPPLIERS ==========

FLY_ASH_SUPPLIERS = {
    "pozzolanic_philippines": {
        "name": "Pozzolanic Philippines, Inc. (PPI)",
        "type": "Major Supplier",
        "description": "Largest independent fly ash supplier in PH",
        "products": ["ASTM C618 Class F Fly Ash"],
        "source": "Calaca/Mauban Coal Power Plants",
        "locations": {
            "head_office": "Makati City",
            "plant": "Calaca, Batangas",
        },
        "contact": {
            "website": "www.pozzolanic.ph",
            "note": "Industrial quantities only",
        },
        "estimated_price": "₱1,500-2,000/ton",
    },
    
    "fahrenheit_fcl": {
        "name": "Fahrenheit Company Limited (FCL)",
        "type": "Importer/Supplier",
        "description": "Supplies fly ash from Vietnam/Australia/India",
        "products": ["ASTM C618 Class F Fly Ash"],
        "locations": {
            "office": "Subic Bay Freeport Zone",
        },
        "contact": {
            "website": "www.fclsubic.com",
        },
        "estimated_price": "₱1,800-2,500/ton (imported)",
    },
    
    "ilhan_trading": {
        "name": "ILHAN Trading",
        "type": "Supplier",
        "description": "Supplies dry and wet fly ash",
        "products": ["ASTM C618 Class F Fly Ash - Dry", "Wet Fly Ash"],
        "contact": {
            "website": "www.ilhantrading.com",
        },
        "estimated_price": "₱1,200-1,800/ton",
    },
    
    "coal_plants_direct": {
        "name": "Direct from Coal Power Plants",
        "type": "Source",
        "description": "Contact plants directly for bulk purchase",
        "plants": [
            {"name": "Calaca Power Plant", "location": "Calaca, Batangas"},
            {"name": "Pagbilao Power Plant", "location": "Mauban, Quezon"},
            {"name": "GNPower Mariveles", "location": "Mariveles, Bataan"},
            {"name": "GBP Iloilo", "location": "Iloilo City"},
            {"name": "KEPCO Cebu", "location": "Naga, Cebu"},
            {"name": "Toledo Power", "location": "Toledo, Cebu"},
        ],
        "note": "Often FREE or very cheap, just pay for hauling!",
        "estimated_price": "₱500-1,000/ton (hauling cost only)",
    },
}


# ========== RICE HULL ASH (RHA) SUPPLIERS ==========

RHA_SUPPLIERS = {
    "mhyggz_trading": {
        "name": "MHYGGZ Trading",
        "type": "Supplier/Exporter",
        "location": "Bulacan",
        "products": ["Rice Husk Ash for Construction"],
        "contact": {
            "platform": "ExportersIndia.com",
        },
        "estimated_price": "₱800-1,200/ton",
    },
    
    "ngosiok_marketing": {
        "name": "NGOSIOK Marketing",
        "type": "Major Supplier",
        "description": "Leading RHA supplier in Philippines",
        "products": ["Construction-grade RHA"],
        "estimated_price": "₱1,000-1,500/ton",
    },
    
    "rice_mills_direct": {
        "name": "Direct from Rice Mills",
        "type": "Source - CHEAPEST!",
        "description": "Contact rice mills with biomass/cogen plants",
        "regions": [
            {"region": "Central Luzon", "provinces": ["Bulacan", "Nueva Ecija", "Pampanga", "Tarlac"]},
            {"region": "Cagayan Valley", "provinces": ["Isabela", "Cagayan"]},
            {"region": "Ilocos Region", "provinces": ["Pangasinan"]},
            {"region": "Western Visayas", "provinces": ["Iloilo", "Negros Occidental"]},
        ],
        "how_to_find": [
            "Contact NFA (National Food Authority) for mill listings",
            "Search 'rice mill' + province name",
            "Visit rice milling clusters in Nueva Ecija/Isabela",
        ],
        "note": "Often FREE - they pay to dispose of it!",
        "estimated_price": "₱0-500/ton (free if you haul)",
        "processing": "Need to burn (controlled 600-700°C) and grind",
    },
    
    "international_rice_research": {
        "name": "International Rice Research Institute (IRRI)",
        "type": "Research/Reference",
        "location": "Los Baños, Laguna",
        "description": "Can provide technical guidance on RHA for construction",
        "contact": {
            "website": "www.irri.org",
        },
    },
}


# ========== VOLCANIC PUMICE SUPPLIERS ==========

PUMICE_SUPPLIERS = {
    "cypress_bomanite": {
        "name": "Cypress Bomanite, Inc.",
        "type": "Supplier",
        "location": "Quezon City",
        "products": [
            "Volcanic Pumice Stone 1-3mm",
            "Volcanic Pumice Stone 5-8mm",
            "Volcanic Pumice Stone 10-15mm",
            "Volcanic Pumice Stone 15-20mm",
            "Volcanic Pumice Stone 20-25mm",
        ],
        "uses": ["Lightweight concrete", "Landscaping", "Construction"],
        "contact": {
            "platform": "all.biz",
        },
        "estimated_price": "₱1,000-1,500/ton",
    },
    
    "norther_eistar": {
        "name": "Norther Eistar Minerals Company",
        "type": "Supplier",
        "location": "Candelaria, Quezon",
        "products": ["Pumice Volcanic Stone", "Aggregates"],
        "estimated_price": "₱800-1,200/ton",
    },
    
    "rlkaur_import_export": {
        "name": "Rlkaur Import-Export Corp.",
        "type": "Supplier",
        "products": ["Pumice Stone", "Crushed Aggregates"],
        "estimated_price": "₱1,000-1,500/ton",
    },
    
    "pumice_unlimited": {
        "name": "Pumice Unlimited Ventures",
        "type": "Supplier",
        "description": "Uses Mt. Pinatubo pumice",
        "source": "Mt. Pinatubo lahar deposits",
        "location": "Pampanga/Zambales area",
        "estimated_price": "₱600-1,000/ton (near source)",
    },
    
    "seintrad_corp": {
        "name": "Seintrad, Corp.",
        "type": "Exporter",
        "location": "Makati City",
        "description": "Exporting PH pumice since 1999",
        "contact": {
            "platform": "all.biz",
        },
        "estimated_price": "₱1,200-1,800/ton",
    },
    
    "lahar_areas_direct": {
        "name": "Direct from Lahar/Volcanic Areas",
        "type": "Source - CHEAPEST!",
        "locations": [
            {"volcano": "Mt. Pinatubo", "provinces": ["Zambales", "Pampanga", "Tarlac"], "status": "Abundant!"},
            {"volcano": "Taal Volcano", "provinces": ["Batangas"], "status": "Available"},
            {"volcano": "Mayon Volcano", "provinces": ["Albay"], "status": "Available"},
            {"volcano": "Mt. Bulusan", "provinces": ["Sorsogon"], "status": "Available"},
        ],
        "how_to_find": [
            "Contact quarry operators in lahar areas",
            "Visit Pampanga/Zambales for Pinatubo deposits",
            "Contact DENR for licensed quarries",
        ],
        "note": "Very cheap near source - mainly pay for hauling",
        "estimated_price": "₱300-600/ton (at source)",
    },
}


# ========== COCONUT COIR SUPPLIERS ==========

COIR_SUPPLIERS = {
    "coconut_farms_direct": {
        "name": "Direct from Coconut Farms/Copra",
        "type": "Source",
        "regions": [
            {"region": "CALABARZON", "provinces": ["Quezon", "Laguna"]},
            {"region": "Bicol", "provinces": ["Camarines Sur", "Albay"]},
            {"region": "Western Visayas", "provinces": ["Negros Occidental"]},
            {"region": "Mindanao", "provinces": ["Davao", "Zamboanga"]},
        ],
        "estimated_price": "₱2,000-3,000/ton",
    },
    
    "coco_processing_plants": {
        "name": "Coconut Processing Plants",
        "type": "Source",
        "description": "Contact oil mills and desiccated coconut plants",
        "note": "Coir is byproduct - often willing to sell cheap",
        "estimated_price": "₱1,500-2,500/ton",
    },
}


def print_suppliers_summary():
    """Print summary of all suppliers"""
    print("\n" + "="*70)
    print("🏭 PHILIPPINE MATERIAL SUPPLIERS DATABASE")
    print("="*70)
    
    print("\n" + "="*50)
    print("⚡ FLY ASH (Cement replacement - up to 35%)")
    print("="*50)
    for key, supplier in FLY_ASH_SUPPLIERS.items():
        print(f"\n📍 {supplier['name']}")
        print(f"   Type: {supplier['type']}")
        print(f"   Price: {supplier.get('estimated_price', 'Contact for quote')}")
        if 'note' in supplier:
            print(f"   💡 {supplier['note']}")
    
    print("\n" + "="*50)
    print("🌾 RICE HULL ASH (Cement replacement - up to 20%)")
    print("="*50)
    for key, supplier in RHA_SUPPLIERS.items():
        print(f"\n📍 {supplier['name']}")
        print(f"   Type: {supplier['type']}")
        if 'location' in supplier:
            print(f"   Location: {supplier['location']}")
        print(f"   Price: {supplier.get('estimated_price', 'Contact for quote')}")
        if 'note' in supplier:
            print(f"   💡 {supplier['note']}")
    
    print("\n" + "="*50)
    print("🌋 VOLCANIC PUMICE (Lightweight aggregate)")
    print("="*50)
    for key, supplier in PUMICE_SUPPLIERS.items():
        print(f"\n📍 {supplier['name']}")
        print(f"   Type: {supplier['type']}")
        if 'location' in supplier:
            print(f"   Location: {supplier['location']}")
        print(f"   Price: {supplier.get('estimated_price', 'Contact for quote')}")
        if 'note' in supplier:
            print(f"   💡 {supplier['note']}")


def print_cheapest_options():
    """Print the cheapest sourcing options"""
    print("\n" + "="*70)
    print("💰 CHEAPEST SOURCING OPTIONS")
    print("="*70)
    
    print("""
    
    ┌─────────────────────────────────────────────────────────────────┐
    │  🥇 FLY ASH - Contact Coal Plants Directly!                     │
    │     • Calaca Power Plant (Batangas) - ₱500/ton + hauling       │
    │     • GBP Iloilo - they pay contractors to haul!               │
    │     • KEPCO Naga, Cebu - cement companies buy from here        │
    │     💡 TIP: Offer to haul = often FREE material!               │
    └─────────────────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────────────────┐
    │  🥇 RICE HULL ASH - Go to Rice Mills in Nueva Ecija!           │
    │     • Visit San Jose City, Nueva Ecija (rice capital)          │
    │     • Contact mills with biomass power plants                   │
    │     • Price: FREE to ₱500/ton (you haul)                       │
    │     💡 TIP: They usually PAY to dispose it - offer to take!    │
    └─────────────────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────────────────┐
    │  🥇 PUMICE - Go to Pinatubo Lahar Areas!                       │
    │     • Zambales/Pampanga quarries                               │
    │     • Price: ₱300-600/ton at source                            │
    │     • Crushed lahar = ready-to-use aggregate                   │
    │     💡 TIP: Abundant supply - negotiate bulk discounts!        │
    └─────────────────────────────────────────────────────────────────┘
    
    """)


if __name__ == "__main__":
    print_suppliers_summary()
    print_cheapest_options()
