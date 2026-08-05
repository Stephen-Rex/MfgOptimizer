# library_loader.py
import csv
import io

def get_default_machinery():
    """Returns baseline machinery library from the SRS."""
    return [
        {
            "Make": "Mazak",
            "Model": "Integrex i-200",
            "Type": "Multi axis CNC",
            "Width": 12.0,
            "Height": 10.0,
            "Standoff": 5.0,
            "VaporPort": "VP-A1",
            "WaterHookup": True,
            "Amperage": 45.0,
            "Wattage": 18000.0,
            "ToolHeads": 4,
            "Volume": 45,
            "Yield": 98.0,
            "CraneRequired": True,
            "Decibel": 75
        },
        {
            "Make": "Arburg",
            "Model": "Allrounder 370",
            "Type": "Injection Molding",
            "Width": 15.0,
            "Height": 8.0,
            "Standoff": 4.0,
            "VaporPort": "VP-B2",
            "WaterHookup": True,
            "Amperage": 30.0,
            "Wattage": 15000.0,
            "ToolHeads": 1,
            "Volume": 60,
            "Yield": 95.0,
            "CraneRequired": False,
            "Decibel": 65
        },
        {
            "Make": "Timesavers",
            "Model": "Model 2200",
            "Type": "Sanding/Grinding",
            "Width": 10.0,
            "Height": 7.0,
            "Standoff": 6.0,
            "VaporPort": "VP-C3",
            "WaterHookup": False,
            "Amperage": 25.0,
            "Wattage": 12000.0,
            "ToolHeads": 2,
            "Volume": 35,
            "Yield": 92.0,
            "CraneRequired": False,
            "Decibel": 85
        }
    ]

def get_default_lighting():
    """Returns standard lighting fixtures library."""
    return [
        {
            "Make": "Lithonia",
            "Brand": "I-Beam",
            "Type": "LED",
            "Wattage": 150.0,
            "Kelvin": 5000,
            "Dimmable": True,
            "Lumens": 18000,
            "Lux": 500
        },
        {
            "Make": "Philips",
            "Brand": "Halogen Pro",
            "Type": "Halogen",
            "Wattage": 250.0,
            "Kelvin": 3000,
            "Dimmable": True,
            "Lumens": 12000,
            "Lux": 350
        }
    ]
