import xml.etree.ElementTree as ET
from pathlib import Path

def adjust_traffic(input_path, num_agents=40, batch_size=10, interval=120, agent_type='vehicle'):
    """Adjust traffic by reducing agents and staggering departure times"""
    tree = ET.parse(input_path)
    root = tree.getroot()
    
    # Select agents (vehicles/pedestrians) to keep
    agents = []
    for agent in root.findall(agent_type):
        agent_id = agent.get('id')
        
        # For vehicles: Keep only base IDs (XX.0) to reduce duplicates
        if agent_type == 'vehicle' and not agent_id.endswith('.0'):
            continue
            
        agents.append(agent)
        if len(agents) >= num_agents:
            break

    # Remove all existing agents
    for agent in root.findall(agent_type):
        root.remove(agent)

    # Add back selected agents with staggered departure times
    for idx, agent in enumerate(agents[:num_agents]):
        batch = idx // batch_size
        depart = batch * interval
        agent.set('depart', f"{float(depart):.1f}")
        root.append(agent)

    # Save modified file
    tree.write(input_path, encoding='UTF-8', xml_declaration=True)

def main():
    base_dir = Path(__file__).parent  # Script location
    
    # Adjust vehicle traffic
    adjust_traffic(
        base_dir/'vehicles.rou.xml',
        num_agents=900,  # 4 batches of 10 vehicles
        agent_type='vehicle'
    )
    
    # Adjust pedestrian traffic
    adjust_traffic(
        base_dir/'pedestrians.rou.xml', 
        num_agents=300,  # 3 batches of 10 pedestrians
        agent_type='pedestrian'
    )

if __name__ == '__main__':
    main()