import json
import sys
import os

VERSION_FILE = os.path.join(os.path.dirname(__file__), '..', 'version.json')

def update_version(change_type):
    if not os.path.exists(VERSION_FILE):
        print(f"Error: {VERSION_FILE} not found.")
        return

    with open(VERSION_FILE, 'r') as f:
        data = json.load(f)

    v_parts = list(map(int, data['version'].split('.')))
    
    if change_type == 'major':
        v_parts[0] += 1
        v_parts[1] = 0
        v_parts[2] = 0
    elif change_type == 'feat':
        v_parts[1] += 1
        v_parts[2] = 0
    elif change_type == 'fix':
        v_parts[2] += 1
    else:
        print(f"Unknown change type: {change_type}")
        return

    new_version = ".".join(map(str, v_parts))
    data['version'] = new_version
    data['last_commit_type'] = change_type
    
    with open(VERSION_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Version updated to: {new_version} ({change_type})")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        update_version(sys.argv[1])
    else:
        print("Usage: python version_util.py [fix|feat|major]")
