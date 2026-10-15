"""
Philippine Skills & Competencies Taxonomy Knowledge Base
---------------------------------------------------------
Exhaustive, localized Philippine skill ontology covering:
  - Blue-Collar & Service Workers (Food Service, Hospitality, Janitorial, Skilled Trades, Warehouse, Driving, Security)
  - BPO, Customer Service & Administrative (Voice/Non-Voice, Technical Support, Office Management, Remittances)
  - Technical & White-Collar (Software Development, Engineering, Architecture, Healthcare, Education, Finance)
  - Soft Skills & Filipino Workplace Traits ("Pakikisama", "Willing to render overtime", "Can work under pressure")
  - Professional Licenses (PRC, CSC, TESDA, LTO, SOSIA) and Philippine Languages

Provides local gazetteers, alias mappings, and external dataset ingestion hooks for ESCO, O*NET, and TESDA.
"""

import os
import csv
import json
from typing import Dict, Any, List, Optional, Set, Tuple


# ─── 1. Exhaustive Skill Taxonomy Dictionary ──────────────────────────────────
# Format:
# canonical_name: {
#   "type": "Hard Skill" | "Soft Skill" | "Certification / License" | "Language",
#   "domain": str,
#   "is_tool": bool,
#   "aliases": [str, ...]
# }

PHILIPPINE_SKILLS_TAXONOMY: Dict[str, Dict[str, Any]] = {
    # ══════════════════════════════════════════════════════════════════════════
    # 1. SERVICE, F&B & HOSPITALITY
    # ══════════════════════════════════════════════════════════════════════════
    "Food Preparation": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Food preparation", "Food prep", "Meal preparation", "Kitchen prep", "Ingredient preparation", "Food handling", "Paghahanda ng pagkain"]
    },
    "Kitchen Sanitation": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Kitchen sanitation", "Kitchen hygiene", "Food safety & sanitation", "Kitchen cleanliness", "Safe food handling", "Kitchen stewarding"]
    },
    "Food Safety & HACCP": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["HACCP", "Food safety", "Food safety compliance", "ServSafe", "Food hygiene standards", "Sanitation standards"]
    },
    "FIFO Inventory Management": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["FIFO", "First In First Out", "FIFO inventory", "Stock rotation", "Perishable goods rotation"]
    },
    "Grill & Fryer Station Operation": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Grill station", "Fryer station", "Grill and fryer", "Fry station crew", "Grill cook", "Grill operation", "Deep fryer operation", "Kitchen crew"]
    },
    "Dishwashing & Stewarding": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Dishwashing", "Dish washing", "Kitchen stewarding", "Dishwasher operation", "Pot washing", "Utensil sanitation"]
    },
    "Dining Table Bussing": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Table bussing", "Busser", "Bussing tables", "Dining area clearing", "Tray cleaning", "Dining maintenance"]
    },
    "POS Cashiering": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": True,
        "aliases": ["POS cashiering", "POS operation", "Point of Sale", "Point of sale operation", "Cashiering", "Counter cashier", "POS register", "Cash balancing"]
    },
    "Cash Handling": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Cash handling", "Cash counting", "Cash register management", "Daily cash balancing", "Petty cash handling", "Remittance counting"]
    },
    "Customer Order Taking": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Order taking", "Taking customer orders", "Menu assistance", "Food order taking", "Counter service"]
    },
    "Product Upselling": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Upselling", "Suggestive selling", "Cross-selling", "Promoting addon items", "Up-selling"]
    },
    "Barista & Coffee Making": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": True,
        "aliases": ["Barista", "Coffee making", "Espresso machine operation", "Latte art", "Beverage preparation", "Coffee brewing", "Milk steaming"]
    },
    "Bartending & Mixology": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Bartending", "Bar tending", "Mixology", "Cocktail mixing", "Bar service", "Beverage inventory", "Bar setup"]
    },
    "Housekeeping & Room Makeup": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Housekeeping", "Room makeup", "Room cleaning", "Bed making", "Linen changing", "Guestroom servicing", "Hotel housekeeping"]
    },
    "Floor Polishing & Buffing": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": True,
        "aliases": ["Floor polishing", "Floor buffing", "Rotary floor polisher", "Floor waxing", "Floor maintenance", "Floor scrubbing"]
    },
    "Front Desk & Hotel Reception": {
        "type": "Hard Skill",
        "domain": "Service, F&B & Hospitality",
        "is_tool": False,
        "aliases": ["Front desk reception", "Hotel reception", "Guest check-in", "Guest check-out", "Concierge service", "Room reservation"]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 2. JANITORIAL, MAINTENANCE & SKILLED TRADES
    # ══════════════════════════════════════════════════════════════════════════
    "Industrial Cleaning": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Industrial cleaning", "Commercial cleaning", "Deep cleaning", "Building sanitation", "Premises maintenance", "Janitorial service"]
    },
    "Waste Segregation": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Waste segregation", "Trash segregation", "Garbage disposal", "Waste disposal", "Basura segregation", "Recycling segregation"]
    },
    "Restroom Sanitation": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Restroom sanitation", "Comfort room cleaning", "CR cleaning", "Toilet sanitation", "Bathroom disinfection"]
    },
    "Carpet Shampooing & Vacuuming": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": True,
        "aliases": ["Carpet shampooing", "Carpet cleaning", "Vacuuming", "Heavy duty vacuum operation", "Upholstery cleaning"]
    },
    "Chemical Handling & Dilution": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Chemical handling", "Chemical dilution", "Cleaning chemical safety", "Material Safety Data Sheet", "MSDS compliance"]
    },
    "Plumbing Repair & Installation": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Plumbing", "Plumbing repair", "Pipe installation", "Drain declogging", "Faucet repair", "PVC pipe installation", "Water line maintenance"]
    },
    "Carpentry & Woodworking": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Carpentry", "Rough carpentry", "Finish carpentry", "Woodworking", "Furniture assembly", "Drywall installation", "Ceiling installation"]
    },
    "Masonry & Concrete Works": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Masonry", "Mason", "Hollow block laying", "Plastering", "Cement mixing", "Concrete works", "Bricklaying"]
    },
    "Tile Setting": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Tile setting", "Tiling", "Floor tiling", "Wall tiling", "Tile cutting", "Grouting"]
    },
    "Painting & Finishing": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Painting", "Surface preparation", "Epoxy painting", "Wall painting", "Primer application", "Paint spraying", "Varnishing"]
    },
    "Shielded Metal Arc Welding (SMAW)": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": True,
        "aliases": ["SMAW", "Shielded Metal Arc Welding", "Stick welding", "SMAW NC II", "SMAW NC I", "Arc welding", "Electric welding"]
    },
    "TIG & MIG Welding": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": True,
        "aliases": ["TIG welding", "MIG welding", "GTAW", "GMAW", "Gas tungsten arc welding", "Gas metal arc welding", "Argon welding"]
    },
    "Oxy-Acetylene Cutting": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": True,
        "aliases": ["Oxy-acetylene cutting", "Oxy-acetylene welding", "Torch cutting", "Gas cutting", "Metal flame cutting"]
    },
    "HVAC Maintenance & Aircon Repair": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": True,
        "aliases": ["HVAC maintenance", "Aircon repair", "Air conditioning cleaning", "Freon charging", "Refrigeration repair", "RAC servicing", "HVAC troubleshooting"]
    },
    "Electrical Wiring & Troubleshooting": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": True,
        "aliases": ["Electrical wiring", "Electrical installation and maintenance", "EIM", "Electrical troubleshooting", "Circuit breaker installation", "Electrical conduit bending", "Line testing"]
    },
    "Preventive Maintenance": {
        "type": "Hard Skill",
        "domain": "Janitorial, Maintenance & Skilled Trades",
        "is_tool": False,
        "aliases": ["Preventive maintenance", "PM servicing", "Equipment maintenance", "Routine inspection", "Machinery lubrication", "Facility maintenance"]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 3. LOGISTICS, DRIVING, WAREHOUSE & SECURITY
    # ══════════════════════════════════════════════════════════════════════════
    "Forklift Operation": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": True,
        "aliases": ["Forklift operation", "Forklift operator", "Forklift driving", "Reach truck operation", "Counterbalance forklift", "Power industrial truck"]
    },
    "Pallet Jack Operation": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": True,
        "aliases": ["Pallet jack", "Hydraulic pallet jack", "Manual pallet truck", "Electric pallet jack", "Hand pallet truck"]
    },
    "Inventory & Stock Management": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": False,
        "aliases": ["Inventory management", "Stock management", "Stocktaking", "Cycle counting", "Inventory auditing", "Physical count", "Stock inventory"]
    },
    "Picking, Packing & Sorting": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": False,
        "aliases": ["Picking and packing", "Order picking", "Order packing", "Parcel sorting", "Barcode scanning", "Warehouse picker", "Package labeling"]
    },
    "Loading & Unloading": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": False,
        "aliases": ["Loading and unloading", "Cargo loading", "Truck unloading", "Material handling", "Container van unloading"]
    },
    "Defensive Driving": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": False,
        "aliases": ["Defensive driving", "Safe driving practices", "Road safety", "Traffic rules compliance", "Road courtesy"]
    },
    "Professional Driver's License (LTO)": {
        "type": "Certification / License",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": False,
        "aliases": ["Professional Driver's License", "Driver's License", "LTO Driver's License", "Restriction 1, 2", "Restriction 1, 2, 3", "Restriction 2, 3", "Restriction 1,2", "DL Restriction 1, 2", "DL Code A, B", "DL Code B1, B2", "Pro License"]
    },
    "Motorcycle Delivery & Navigation": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": False,
        "aliases": ["Motorcycle delivery", "Motorcycle driving", "Single motorcycle driving", "Lalamove delivery", "Grab delivery", "Foodpanda delivery", "Courier delivery", "GPS navigation", "Waze navigation", "Google Maps navigation"]
    },
    "CCTV Monitoring": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": True,
        "aliases": ["CCTV monitoring", "CCTV surveillance", "Security camera operation", "Video surveillance", "Surveillance monitoring"]
    },
    "Roving Patrol & Access Control": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": False,
        "aliases": ["Roving patrol", "Access control", "Perimeter security", "Guard duty", "Gate pass inspection", "Visitor log management", "Frisking & bag checking"]
    },
    "First Aid & Basic Life Support (BLS)": {
        "type": "Hard Skill",
        "domain": "Logistics, Driving, Warehouse & Security",
        "is_tool": False,
        "aliases": ["First aid", "Basic Life Support", "BLS", "CPR", "Emergency response", "Red Cross First Aid", "First aid treatment"]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 4. BPO, CUSTOMER SERVICE & ADMINISTRATIVE
    # ══════════════════════════════════════════════════════════════════════════
    "Customer Service": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Customer service", "Customer care", "Customer support", "Client service", "CSR", "Cust. Service", "Customer satisfaction"]
    },
    "Technical Support": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Technical support", "Tech support", "TSR", "Hardware troubleshooting", "Software troubleshooting", "Help desk", "IT support specialist", "L1 support", "L2 support"]
    },
    "Inbound & Outbound Calling": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Inbound call handling", "Outbound calling", "Inbound calls", "Outbound calls", "Cold calling", "Telemarketing", "Appointment setting", "Phone etiquette"]
    },
    "Conflict De-escalation": {
        "type": "Soft Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Conflict de-escalation", "De-escalation", "Complaint handling", "Escalation management", "Irrate customer handling", "Call de-escalation"]
    },
    "Active Listening": {
        "type": "Soft Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Active listening", "Attentive listening", "Empathy", "Customer empathy", "Listening comprehension"]
    },
    "Chat & Email Support": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Chat support", "Email support", "Non-voice support", "Email correspondence", "Live chat handling", "Written customer support"]
    },
    "Zendesk": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Zendesk", "Zendesk Support", "Zendesk ticketing"]
    },
    "Freshdesk": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Freshdesk", "Freshservice"]
    },
    "Jira Service Management": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Jira", "Jira Service Desk", "Jira Service Management", "Atlassian Jira"]
    },
    "ServiceNow": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["ServiceNow", "Service Now", "ServiceNow ticketing"]
    },
    "Salesforce CRM": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Salesforce", "Salesforce CRM", "SFDC", "Salesforce Service Cloud"]
    },
    "HubSpot": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["HubSpot", "HubSpot CRM"]
    },
    "Avaya VoIP": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Avaya", "Avaya One-X", "Avaya IP Agent", "Avaya softphone"]
    },
    "Cisco IP Communicator": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Cisco IP Phone", "Cisco IP Communicator", "Cisco Webex", "Cisco Finesse"]
    },
    "Five9": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Five9", "Five 9", "Five9 dialer"]
    },
    "Genesys Cloud": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Genesys", "Genesys Cloud", "Genesys PureCloud"]
    },
    "Data Encoding & Entry": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Data encoding", "Data entry", "Encoder", "Data encoder", "High accuracy typing", "Keyboard encoding"]
    },
    "Typing Speed (WPM)": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Typing speed", "40 WPM", "45 WPM", "50 WPM", "55 WPM", "60 WPM", "65 WPM", "70 WPM", "WPM typing speed", "Touch typing"]
    },
    "Bookkeeping & Accounting": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Bookkeeping", "Book keeper", "General ledger", "Accounts payable", "Accounts receivable", "Journal entries", "Bank reconciliation"]
    },
    "Payroll Processing": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Payroll processing", "Payroll preparation", "Timekeeping", "Bi-monthly payroll", "Salary computation", "Overtime calculation", "DTR computation"]
    },
    "Government Remittances (SSS, PhilHealth, Pag-IBIG, BIR)": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["SSS remittance", "PhilHealth remittance", "Pag-IBIG remittance", "BIR remittance", "Statutory contributions", "SSS, PhilHealth, Pag-IBIG", "Alphalist", "BIR Form 2316"]
    },
    "201 File Management": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["201 file management", "201 files", "Employee records management", "HR filing", "Personnel file maintenance"]
    },
    "Microsoft Office Suite": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Microsoft Office", "MS Office", "MS Office Suite", "Office 365", "Microsoft 365", "MS Word, Excel, PowerPoint", "MS Word/Excel/Powerpoint", "MS Word/Excel/PowerPoint", "Word/Excel/Powerpoint", "MS Word / Excel / PowerPoint"]
    },
    "Microsoft Excel": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Microsoft Excel", "MS Excel", "Excel", "Spreadsheets"]
    },
    "Advanced Excel (VLOOKUP & Pivot Tables)": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["VLOOKUP", "Pivot Tables", "VLOOKUP & Pivot Tables", "XLOOKUP", "INDEX MATCH", "Excel Formulas", "Pivot table analysis", "Advanced Excel"]
    },
    "Microsoft Word": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Microsoft Word", "MS Word", "Word processing", "Document formatting"]
    },
    "Microsoft PowerPoint": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Microsoft PowerPoint", "MS PowerPoint", "PowerPoint", "Powerpoint", "PowerPoint presentation", "Pitch decks", "Slide decks"]
    },
    "Google Workspace": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": True,
        "aliases": ["Google Workspace", "G Suite", "Google Docs", "Google Sheets", "Google Slides", "Google Drive", "Google Calendar"]
    },
    "Virtual Assistance": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Virtual assistance", "Virtual Assistant", "VA", "Executive assistance", "Email management", "Calendar management", "Travel booking"]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 5. SOFTWARE DEVELOPMENT & IT
    # ══════════════════════════════════════════════════════════════════════════
    "Python": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Python", "Python 3", "Python programming"]
    },
    "Java": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Java", "Java 8", "Java 11", "Java 17", "Java 21", "Core Java"]
    },
    "C#": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["C#", "C-Sharp", "CSharp", ".NET C#"]
    },
    "TypeScript": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["TypeScript", "TS"]
    },
    "JavaScript": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["JavaScript", "JS", "ES6", "Vanilla JS"]
    },
    "PHP": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["PHP", "PHP 8", "PHP 7"]
    },
    "C++": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["C++", "CPP"]
    },
    "SQL": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["SQL", "Structured Query Language", "Relational Database", "RDBMS"]
    },
    "HTML5 & CSS3": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["HTML", "HTML5", "CSS", "CSS3", "HTML5/CSS3", "HTML/CSS"]
    },
    "React.js": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["React", "React.js", "ReactJS"]
    },
    "Next.js": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Next.js", "NextJS", "Next"]
    },
    "Node.js": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Node", "Node.js", "NodeJS"]
    },
    "NestJS": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["NestJS", "Nest.js", "Nest"]
    },
    "Express.js": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Express", "Express.js", "ExpressJS"]
    },
    "Spring Boot": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Spring Boot", "Spring Framework", "Spring"]
    },
    ".NET Core": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": [".NET Core", "ASP.NET Core", ".NET", "ASP.NET", "Dotnet"]
    },
    "Laravel": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Laravel", "Laravel Framework"]
    },
    "Django": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Django", "Django REST Framework", "DRF"]
    },
    "FastAPI": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["FastAPI", "Fast API"]
    },
    "Tailwind CSS": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Tailwind CSS", "Tailwind", "TailwindCSS"]
    },
    "PostgreSQL": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["PostgreSQL", "Postgres", "PSQL"]
    },
    "MySQL": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["MySQL", "MariaDB"]
    },
    "MongoDB Atlas": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["MongoDB", "Mongo", "MongoDB Atlas", "NoSQL"]
    },
    "Supabase": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Supabase", "Supabase DB"]
    },
    "Firebase": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Firebase", "Firestore", "Firebase Auth"]
    },
    "Redis": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Redis", "Redis Cache"]
    },
    "Docker": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Docker", "Docker Compose", "Containerization"]
    },
    "Kubernetes": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Kubernetes", "K8s"]
    },
    "Amazon Web Services (AWS)": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["AWS", "Amazon Web Services", "AWS S3", "AWS EC2", "AWS Lambda"]
    },
    "Git & Version Control": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Git", "GitHub", "GitLab", "Bitbucket", "Version Control", "GitHub Actions"]
    },
    "CI/CD Pipelines": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["CI/CD", "CICD", "Continuous Integration", "Continuous Deployment", "Jenkins"]
    },
    "RESTful API Development": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": False,
        "aliases": ["RESTful API", "REST API", "REST APIs", "API integration", "Backend API", "JSON API"]
    },
    "GraphQL": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["GraphQL", "Apollo GraphQL"]
    },
    "Postman": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Postman", "Postman API testing", "API testing"]
    },
    "Manual Testing": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": False,
        "aliases": ["Manual testing", "Manual QA", "Test case creation", "Bug reporting", "UAT", "User acceptance testing"]
    },
    "Regression Testing": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": False,
        "aliases": ["Regression testing", "Manual regression testing", "Automated regression testing", "Smoke testing", "Sanity testing"]
    },
    "Jest & Cypress": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Jest", "Cypress", "Selenium", "Playwright", "Mocha", "Unit testing"]
    },
    "Agile Scrum": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": False,
        "aliases": ["Agile", "Scrum", "Agile Scrum", "Sprint planning", "Daily standups", "Kanban", "Retrospectives"]
    },
    "Linux Administration": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["Linux", "Ubuntu", "CentOS", "Debian", "Bash scripting", "Shell scripting", "Linux server"]
    },
    "PC Troubleshooting & Hardware Repair": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["PC troubleshooting", "Computer repair", "Hardware troubleshooting", "PC assembly", "OS reformatting", "Printer setup", "Computer Systems Servicing"]
    },
    "LAN/WAN Networking": {
        "type": "Hard Skill",
        "domain": "Software Development & IT",
        "is_tool": True,
        "aliases": ["LAN/WAN", "Networking", "Network configuration", "Router configuration", "RJ45 crimping", "Network cabling", "IP subnetting", "DNS/DHCP"]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 6. ENGINEERING, CONSTRUCTION & ARCHITECTURE
    # ══════════════════════════════════════════════════════════════════════════
    "AutoCAD (2D & 3D)": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": True,
        "aliases": ["AutoCAD", "Auto CAD", "AutoCAD 2D", "AutoCAD 3D", "CAD", "2D Drafting", "Computer-Aided Design"]
    },
    "STAAD.Pro": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": True,
        "aliases": ["STAAD.Pro", "STAAD Pro", "STAAD", "Structural analysis software"]
    },
    "ETABS": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": True,
        "aliases": ["ETABS", "CSI ETABS"]
    },
    "Revit Architecture & BIM": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": True,
        "aliases": ["Revit", "Autodesk Revit", "BIM", "Building Information Modeling", "Revit Architecture"]
    },
    "SketchUp": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": True,
        "aliases": ["SketchUp", "Google SketchUp", "3D Modeling SketchUp", "V-Ray"]
    },
    "Primavera P6 & MS Project": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": True,
        "aliases": ["Primavera P6", "Primavera", "MS Project", "Microsoft Project", "Project scheduling", "Gantt chart management"]
    },
    "Structural Analysis & Design": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["Structural analysis", "Structural design", "Load calculation", "Seismic analysis", "Reinforced concrete design", "Steel design"]
    },
    "Site Supervision & Construction Management": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["Site supervision", "Construction management", "Project engineer", "Site engineer", "Field supervision", "Contractor monitoring", "Subcontractor supervision"]
    },
    "Concrete Pouring & Rebar Inspection": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["Concrete pouring", "Rebar inspection", "Slump test", "Compressive strength test", "Formwork inspection", "Reinforcing bars inspection"]
    },
    "Quantity Surveying & Cost Estimation": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["Quantity surveying", "Cost estimation", "Material take-off", "Takeoff", "Project costing", "Budgeting"]
    },
    "Bill of Quantities (BOQ)": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["Bill of Quantities", "BOQ", "BOM", "Bill of Materials", "BOQ preparation"]
    },
    "Blueprint Reading & Plan Interpretation": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["Blueprint reading", "Plan interpretation", "Architectural plans", "Structural plans", "As-built drawings", "Shop drawings"]
    },
    "Basic Occupational Safety and Health (BOSH)": {
        "type": "Certification / License",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["BOSH", "BOSH Certified", "BOSH SO2", "Safety Officer 2", "Safety Officer SO2", "DOLE BOSH"]
    },
    "Construction Occupational Safety and Health (COSH)": {
        "type": "Certification / License",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["COSH", "COSH Certified", "Construction safety", "Safety Officer SO1", "Safety Officer SO3"]
    },
    "ISO 9001 Quality Standards": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["ISO 9001", "Quality management system", "QMS", "ISO compliance", "Quality inspection"]
    },
    "PLC Programming & Mechatronics": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": True,
        "aliases": ["PLC", "PLC programming", "Programmable Logic Controller", "SCADA", "Mechatronics", "Automation engineering", "Pneumatics", "Hydraulics"]
    },
    "Accomplishment & Progress Reporting": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["Accomplishment reports", "Daily accomplishment reports", "Progress reporting", "Weekly accomplishment reports", "Site progress reports", "Daily reports"]
    },
    "Subcontractor Manpower Management": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["Subcontractor manpower", "Manpower monitoring", "Subcontractor supervision", "Manpower management", "Subcontractor coordination", "Subcontractor monitoring"]
    },


    # ══════════════════════════════════════════════════════════════════════════
    # 7. HEALTHCARE, EDUCATION & FINANCE
    # ══════════════════════════════════════════════════════════════════════════
    "Patient Care & Vital Signs Monitoring": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": False,
        "aliases": ["Patient care", "Vital signs monitoring", "Blood pressure monitoring", "Pulse rate taking", "Bedside care", "Patient assessment"]
    },
    "Venipuncture & Phlebotomy": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": False,
        "aliases": ["Venipuncture", "Phlebotomy", "Blood extraction", "Blood drawing", "Cannulation"]
    },
    "IV Insertion & Therapy": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": False,
        "aliases": ["IV insertion", "IV therapy", "Intravenous therapy", "Drip administration", "IV medication"]
    },
    "Medication Administration": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": False,
        "aliases": ["Medication administration", "Administering medication", "Dosage computation", "Oral medication", "Subcutaneous injection"]
    },
    "Caregiving & Elderly Assistance": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": False,
        "aliases": ["Caregiving", "Elderly care", "Assisted living", "Geriatric care", "Palliative care", "Activities of Daily Living", "ADLs"]
    },
    "Lesson Planning & Classroom Management": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": False,
        "aliases": ["Lesson planning", "Classroom management", "Teaching", "Instructional design", "Student evaluation", "Curriculum development"]
    },
    "ESL Teaching": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": False,
        "aliases": ["ESL teaching", "English as a Second Language", "Online English teacher", "TEFL", "TESOL", "English tutoring"]
    },
    "Financial Reporting & Auditing": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": False,
        "aliases": ["Financial reporting", "Financial statements preparation", "Balance sheet preparation", "Income statement", "Financial auditing", "Internal audit", "External audit"]
    },
    "Tax Compliance & BIR Filing": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": False,
        "aliases": ["Tax compliance", "BIR filing", "BIR compliance", "BIR Form 1601C", "BIR Form 2550M", "BIR Form 1702", "eFPS", "Withholding tax"]
    },
    "QuickBooks & Xero": {
        "type": "Hard Skill",
        "domain": "Healthcare, Education & Finance",
        "is_tool": True,
        "aliases": ["QuickBooks", "QuickBooks Online", "Xero", "Xero Accounting", "Cloud accounting software", "SAP ERP", "SAP"]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 8. SOFT SKILLS & FILIPINO WORKPLACE TRAITS
    # ══════════════════════════════════════════════════════════════════════════
    "Teamwork & Collaboration": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": ["Teamwork", "Team player", "Collaboration", "Pakikisama", "Cooperative", "Team-oriented", "Group collaboration"]
    },
    "Stress Tolerance (Can Work Under Pressure)": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": ["Can work under pressure", "Work under pressure", "Stress tolerance", "High pressure environment", "Composure under stress", "Handles pressure well"]
    },
    "Autonomy (Can Work With Minimal Supervision)": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": ["Can work with minimal supervision", "Minimal supervision", "Independent worker", "Self-starter", "Self-motivated", "Autonomous"]
    },
    "Fast Learner & Willing to be Trained": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": ["Fast learner", "Quick learner", "Willing to be trained", "Willing to learn", "Teachable", "Trainable", "Fast learner and willing to be trained"]
    },
    "Overtime & Shifting Flexibility": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": [
            "Willing to render overtime", "Willing to work overtime", "Amenable to shifting schedules",
            "Amenable to shifting", "Night shift", "Amenable to night shift", "Shifting schedule",
            "Graveyard shift", "Rotational shift", "Holiday overtime", "Weekend work", "Flexible schedule"
        ]
    },
    "Interpersonal Skills": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": ["Interpersonal skills", "Good interpersonal skills", "People skills", "Relationship building", "Social skills"]
    },
    "Communication Skills": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": ["Communication skills", "Verbal communication", "Written communication", "Effective communication", "Strong communication"]
    },
    "Problem Solving": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": ["Problem solving", "Problem-solving", "Troubleshooting skills", "Analytical skills", "Root cause analysis", "Critical thinking"]
    },
    "Time Management & Multitasking": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": ["Time management", "Multitasking", "Multi-tasking", "Prioritization", "Organizational skills", "Detail-oriented", "Attention to detail"]
    },
    "Honesty & Integrity": {
        "type": "Soft Skill",
        "domain": "Soft Skills & Filipino Workplace Traits",
        "is_tool": False,
        "aliases": ["Honesty", "Integrity", "Trustworthy", "Dependable", "Reliable", "Strong work ethic"]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 9. PHILIPPINE LICENSES, ELIGIBILITY & LANGUAGES
    # ══════════════════════════════════════════════════════════════════════════
    "PRC Registered Civil Engineer": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": [
            "PRC Registered Civil Engineer", "Licensed Civil Engineer", "Civil Engineer Board Exam Passer",
            "Civil Engineering Board Exam", "PRC Civil Engineer", "Registered Civil Engineer"
        ]
    },
    "PRC Registered Mechanical Engineer": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["PRC Registered Mechanical Engineer", "Licensed Mechanical Engineer", "Mechanical Engineer Board Passer", "Registered Mechanical Engineer"]
    },
    "PRC Registered Electrical Engineer": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["PRC Registered Electrical Engineer", "Licensed Electrical Engineer", "Electrical Engineer Board Passer", "Registered Electrical Engineer", "Registered Master Electrician"]
    },
    "PRC Registered Nurse": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["PRC Registered Nurse", "Licensed Nurse", "Registered Nurse", "RN", "Nurse Licensure Exam Passer", "NLE Passer"]
    },
    "PRC Certified Public Accountant (CPA)": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Certified Public Accountant", "CPA", "PRC CPA", "CPA Board Passer", "Licensed Accountant"]
    },
    "PRC Licensed Professional Teacher (LPT)": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Licensed Professional Teacher", "LPT", "LET Passer", "Licensure Exam for Teachers Passer"]
    },
    "Civil Service Professional Eligibility": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": [
            "Civil Service Professional", "Civil Service Exam - Professional", "CSC Professional",
            "Civil Service Passer", "CSC-PPT Professional", "Civil Service Eligibility"
        ]
    },
    "Civil Service Sub-Professional Eligibility": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Civil Service Sub-Professional", "CSC Sub-Professional", "CSC SubProfessional"]
    },
    "TESDA National Certificate (NC II)": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["TESDA NC II", "NC II", "NC II Certified", "National Certificate II", "TESDA Certified", "TESDA NC I", "TESDA NC III"]
    },
    "SOSIA Security Guard License": {
        "type": "Certification / License",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Security Guard License", "SOSIA License", "Licensed Security Guard", "Security Officer License", "PNP SOSIA"]
    },
    "Tagalog / Filipino": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Tagalog", "Filipino", "Tagalog / Filipino", "Fluent in Tagalog", "Filipino language"]
    },
    "English": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["English", "Fluent in English", "English language", "Business English", "Oral English", "Written English"]
    },
    "Cebuano / Bisaya": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Cebuano", "Bisaya", "Cebuano / Bisaya", "Binisaya"]
    },
    "Ilocano": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Ilocano", "Ilokano"]
    },
    "Hiligaynon / Ilonggo": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Hiligaynon", "Ilonggo"]
    },
    "Kapampangan": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Kapampangan", "Pampango", "Capampangan"]
    },
    "Bicolano / Bikol": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Bicolano", "Bikol", "Bicol"]
    },
    "Waray-Waray / Waray": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Waray", "Waray-Waray", "Winaray"]
    },
    "Japanese (Nihongo)": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Nihongo", "Japanese", "Japanese language", "JLPT"]
    },
    "Mandarin Chinese": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Mandarin", "Chinese", "Mandarin Chinese", "HSK"]
    },
    "Spanish": {
        "type": "Language",
        "domain": "Philippine Licenses, Eligibility & Languages",
        "is_tool": False,
        "aliases": ["Spanish", "Español", "Spanish language", "DELE"]
    },
    "Six Sigma Quality Management": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": False,
        "aliases": ["Six Sigma", "Lean Six Sigma", "Yellow Belt", "Green Belt", "Black Belt", "Lean Manufacturing"]
    },
    "PCB Design & Schematic Capture": {
        "type": "Hard Skill",
        "domain": "Engineering, Construction & Architecture",
        "is_tool": True,
        "aliases": ["PCB design", "PCB", "Altium", "Eagle PCB", "Schematic capture", "Printed Circuit Board"]
    },
    "Stenography & Shorthand": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Stenography", "Shorthand", "Stenographer", "Court reporting"]
    },
    "Cold Calling & Telemarketing": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Cold calling", "Telemarketing", "Outbound calling", "Telesales", "Outbound sales"]
    },
    "Appointment Setting": {
        "type": "Hard Skill",
        "domain": "BPO, Customer Service & Administrative",
        "is_tool": False,
        "aliases": ["Appointment setting", "Setting appointments", "Lead generation", "Setter"]
    },
}


# ─── 2. External Dataset Ingestion Hook (ESCO, O*NET, TESDA) ─────────────────

def load_external_skill_datasets(
    esco_csv_path: Optional[str] = None,
    onet_txt_path: Optional[str] = None,
    tesda_json_path: Optional[str] = None
) -> int:
    """
    Ingests external skill datasets at runtime and merges them into the taxonomy:
      - ESCO CSV (e.g., skills_en.csv with preferredLabel and altLabels)
      - O*NET text/CSV (Technology Skills.txt or Skills.txt)
      - TESDA qualification JSON
    Returns the total number of new skills ingested.
    """
    count = 0

    # 1. ESCO CSV Loader
    if esco_csv_path and os.path.exists(esco_csv_path):
        try:
            with open(esco_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    label = row.get("preferredLabel", "").strip()
                    if label and label not in PHILIPPINE_SKILLS_TAXONOMY:
                        alts = [a.strip() for a in row.get("altLabels", "").split("\n") if a.strip()]
                        PHILIPPINE_SKILLS_TAXONOMY[label] = {
                            "type": "Hard Skill",
                            "domain": "Software Development & IT" if "digital" in label.lower() else "Service, F&B & Hospitality",
                            "is_tool": False,
                            "aliases": alts + [label]
                        }
                        count += 1
        except Exception:
            pass

    # 2. O*NET TXT / CSV Loader
    if onet_txt_path and os.path.exists(onet_txt_path):
        try:
            with open(onet_txt_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    label = parts[0].strip() if parts else ""
                    if label and len(label) > 2 and label not in PHILIPPINE_SKILLS_TAXONOMY:
                        PHILIPPINE_SKILLS_TAXONOMY[label] = {
                            "type": "Hard Skill",
                            "domain": "Software Development & IT",
                            "is_tool": True,
                            "aliases": [label]
                        }
                        count += 1
        except Exception:
            pass

    # 3. TESDA JSON Loader
    if tesda_json_path and os.path.exists(tesda_json_path):
        try:
            with open(tesda_json_path, "r", encoding="utf-8") as f:
                t_data = json.load(f)
                for item in t_data:
                    title = item.get("qualification_title", "").strip()
                    if title and title not in PHILIPPINE_SKILLS_TAXONOMY:
                        PHILIPPINE_SKILLS_TAXONOMY[title] = {
                            "type": "Certification / License",
                            "domain": "Janitorial, Maintenance & Skilled Trades",
                            "is_tool": False,
                            "aliases": [title, item.get("acronym", "").strip()]
                        }
                        count += 1
        except Exception:
            pass

    return count
