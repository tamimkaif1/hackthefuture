from typing import List
from perception.models import ERPInventorySnapshot

class ERPMockConnector:
    def __init__(self):
        # Simulated ERP Data matching the geographical context of our news
        self.inventory_database = [
            ERPInventorySnapshot(
                part_id="IC-7NM-001",
                description="Advanced Logic Microcontroller",
                current_stock=1500,
                buffer_min=2000, # Sub-optimal stock!
                primary_supplier="Hsinchu Semi Corp",
                supplier_location="Hsinchu, Taiwan",
                lead_time_days=45
            ),
            ERPInventorySnapshot(
                part_id="MECH-VALVE-202",
                description="Industrial Fluid Valve",
                current_stock=5000,
                buffer_min=1000,
                primary_supplier="Shenzhen Precision",
                supplier_location="Shenzhen, China",
                lead_time_days=60 # Ocean freight
            ),
             ERPInventorySnapshot(
                part_id="AUTO-HARNESS-X",
                description="Automotive Wiring Harness",
                current_stock=10000,
                buffer_min=8000,
                primary_supplier="Mexico Auto Parts",
                supplier_location="Monterrey, Mexico",
                lead_time_days=7 # Nearshored
            )
        ]

    def get_inventory_snapshot(self) -> List[ERPInventorySnapshot]:
        """Fetches the current inventory state for all monitored critical parts."""
        return self.inventory_database
        
    def get_parts_by_location(self, location_keyword: str) -> List[ERPInventorySnapshot]:
        """Query ERP for parts sourced from a potentially affected region."""
        affected = []
        for item in self.inventory_database:
            if location_keyword.lower() in item.supplier_location.lower():
                affected.append(item)
        return affected
