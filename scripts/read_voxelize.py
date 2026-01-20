
import os

try:
    with open('/opt/ultrashape/ultrashape/utils/voxelize.py', 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Error reading file: {e}")
