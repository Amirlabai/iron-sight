import json
import os
import sys

def txt_to_json(txt_path, json_path):
    """
    Converts a .txt file with regions and coordinates to .json.
    Format:
    [Region Name]
    lat, lon
    lat, lon
    ...
    """
    if not os.path.exists(txt_path):
        print(f"Error: {txt_path} not found.")
        return

    data = {}
    current_region = None
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('[') and line.endswith(']'):
                current_region = line[1:-1].strip()
                data[current_region] = []
            elif current_region:
                try:
                    # Handle both comma and space separated
                    if ',' in line:
                        coords = [float(x.strip()) for x in line.split(',')]
                    else:
                        coords = [float(x.strip()) for x in line.split()]
                    
                    if len(coords) >= 2:
                        out_coords = coords[::-1]
                        data[current_region].append(out_coords)
                except ValueError:
                    print(f"Warning: Skipping invalid line in {current_region}: {line}")

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Successfully created {json_path} from {txt_path}")

def json_to_txt(json_path, txt_path, reverse=False):
    """
    Converts a .json file to .txt with coordinates.
    If reverse is True, it swaps [lat, lon] to [lon, lat].
    """
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(txt_path, 'w', encoding='utf-8') as f:
        for region, coords_list in data.items():
            f.write(f"[{region}]\n")
            for coords in coords_list:
                if reverse:
                    # Reverse the internal order (e.g., [lat, lon] -> [lon, lat])
                    out_coords = coords[::-1]
                else:
                    out_coords = coords
                f.write(f"{out_coords[0]}, {out_coords[1]}\n")
            f.write("\n")
    
    print(f"Successfully created {txt_path} from {json_path} (Reversed: {reverse})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python border_utils.py t2j <input.txt> <output.json>")
        print("  python border_utils.py j2t <input.json> <output.txt> [--reverse]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    
    if cmd == 't2j':
        if len(sys.argv) < 4:
            print("Usage: python border_utils.py t2j <input.txt> <output.json>")
        else:
            txt_to_json(sys.argv[2], sys.argv[3])
    elif cmd == 'j2t':
        if len(sys.argv) < 4:
            print("Usage: python border_utils.py j2t <input.json> <output.txt> [--reverse]")
        else:
            rev = '--reverse' in sys.argv
            json_to_txt(sys.argv[2], sys.argv[3], reverse=rev)
    else:
        print(f"Unknown command: {cmd}")
