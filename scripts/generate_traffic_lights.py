import xml.etree.ElementTree as ET
from pathlib import Path

def generate_valid_traffic_lights(net_file, output_path):
    """Generate traffic lights only for actual TLS junctions"""
    tree = ET.parse(net_file)
    root = tree.getroot()
    
    additional = ET.Element('additional')
    
    # Find only actual traffic light junctions
    tls_junctions = root.findall('.//junction[@type="traffic_light"]')
    
    for tls in tls_junctions:
        tl_id = tls.get('id')
        print(f"Creating traffic light for {tl_id}")
        
        tl_logic = ET.SubElement(additional, 'tlLogic', {
            'id': tl_id,
            'type': 'static',
            'programID': '0',
            'offset': '0'
        })
        
        # Basic 4-phase cycle
        phases = [
            (31, 'GGGgrr'),  # Main green
            (5, 'yyygrr'),   # Yellow
            (31, 'rrrGGG'),  # Cross green
            (5, 'rrryyy')    # Yellow
        ]
        
        for duration, state in phases:
            ET.SubElement(tl_logic, 'phase', {
                'duration': str(duration),
                'state': state
            })
    
    # Validate at least one TLS created
    if not tls_junctions:
        raise ValueError("No traffic light junctions found in network!")
    
    # Write output file
    ET.ElementTree(additional).write(output_path, encoding='UTF-8', xml_declaration=True)
    print(f"Generated {len(tls_junctions)} traffic lights in {output_path}")

if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    generate_valid_traffic_lights(
        net_file=project_root/'data'/'network'/'trafalgar.net.xml',
        output_path=project_root/'scenarios'/'baseline'/'trafficlights.tll.xml'
    )