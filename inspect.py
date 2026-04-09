import json
import struct
import sys

def inspect_glb(filepath):
    try:
        with open(filepath, 'rb') as f:
            magic = f.read(4)
            if magic != b'glTF':
                return
            
            version, = struct.unpack('<I', f.read(4))
            length, = struct.unpack('<I', f.read(4))
            
            chunk_length, = struct.unpack('<I', f.read(4))
            chunk_type, = struct.unpack('<4s', f.read(4))
            
            if chunk_type != b'JSON':
                return
                
            json_data = f.read(chunk_length)
            data = json.loads(json_data.decode('utf-8'))
            
            print("--- Nodes (Bones) ---")
            nodes = data.get('nodes', [])
            for i, n in enumerate(nodes):
                name = n.get('name', '')
                if 'jaw' in name.lower() or 'mouth' in name.lower() or 'head' in name.lower() or 'lip' in name.lower():
                    print(f"Index {i}: {name}")
            print(f"Total nodes checked: {len(nodes)}")
            
    except Exception as e:
        pass

if __name__ == '__main__':
    inspect_glb(sys.argv[1])
