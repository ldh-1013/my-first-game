import base64
import os

def run():
    wav_file = 'assets/sound/boom.wav'
    py_file = 'snake_diet.py'
    
    if not os.path.exists(wav_file):
        print(f"Error: {wav_file} not found")
        return
    
    with open(wav_file, 'rb') as f:
        b64_data = base64.b64encode(f.read()).decode('utf-8')
        
    with open(py_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    in_boom_b64 = False
    found = False
    
    for line in lines:
        if line.startswith('BOOM_B64 = "'):
            new_lines.append(f'BOOM_B64 = "{b64_data}"\n')
            in_boom_b64 = True
            found = True
        elif in_boom_b64:
            if '"' in line or line.strip() == "":
                in_boom_b64 = False
                if line.strip() == "":
                    new_lines.append(line)
            # Skip lines that were part of the old multi-line b64 if any
            continue
        else:
            new_lines.append(line)
            
    if not found:
        print("Error: Could not find BOOM_B64 variable in snake_diet.py")
        return
        
    with open(py_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("Successfully embedded full sound data!")

if __name__ == "__main__":
    run()
