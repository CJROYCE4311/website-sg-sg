import json
import os

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'website', 'data', 'methodology_data.json')
    js_path = os.path.join(base_dir, 'website', 'data', 'methodology_data.js')
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        js_content = f"const methodologyData = {json.dumps(data, indent=2)};"
        
        with open(js_path, 'w') as f:
            f.write(js_content)
            
        print(f"Successfully converted {json_path} to {js_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
