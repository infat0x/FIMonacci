"""
Direct test of entropy calculation
"""
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from client.client import FIMonacciClient

# Create client instance
client = FIMonacciClient("http://localhost:5000")

# Test files
test_files = [
    r"C:\Users\orxan\OneDrive\Desktop\media\media\entropy_test_high_entropy.bin",
    r"C:\Users\orxan\OneDrive\Desktop\media\media\entropy_test_low_entropy.txt",
    r"C:\Users\orxan\OneDrive\Desktop\media\media\entropy_test_medium_entropy.bin"
]

print("=" * 60)
print("Testing Entropy Calculation Directly")
print("=" * 60)

for filepath in test_files:
    print(f"\nFile: {filepath}")
    entropy = client.calculate_entropy(filepath)
    print(f"Entropy result: {entropy}")

    if entropy is not None:
        if entropy >= 7.5:
            print(f"Classification: ENCRYPTED (High entropy)")
        elif entropy >= 4.0:
            print(f"Classification: COMPRESSED (Medium entropy)")
        else:
            print(f"Classification: PLAIN TEXT (Low entropy)")
    else:
        print(f"ERROR: Entropy calculation returned None!")

print("\n" + "=" * 60)
