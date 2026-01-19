#!/usr/bin/env python3
"""
Create test files for entropy detection testing
"""
import os
import random

# Target directory
test_dir = r"C:\Users\orxan\OneDrive\Desktop\media\media"

# Create high entropy file (random bytes - simulates encrypted file)
high_entropy_path = os.path.join(test_dir, "high_entropy_test.bin")
with open(high_entropy_path, 'wb') as f:
    random_bytes = bytes(random.randint(0, 255) for _ in range(10240))  # 10KB
    f.write(random_bytes)
print(f"[OK] Created high entropy file: {high_entropy_path}")

# Create low entropy file (plain text)
low_entropy_path = os.path.join(test_dir, "low_entropy_test.txt")
with open(low_entropy_path, 'w') as f:
    f.write("This is a plain text file.\n" * 100)
print(f"[OK] Created low entropy file: {low_entropy_path}")

# Create medium entropy file (repetitive pattern)
medium_entropy_path = os.path.join(test_dir, "medium_entropy_test.bin")
with open(medium_entropy_path, 'wb') as f:
    pattern = bytes([i % 128 for i in range(256)] * 40)
    f.write(pattern)
print(f"[OK] Created medium entropy file: {medium_entropy_path}")

print("\n[SUCCESS] Test files created! Now check the FIMonacci client console for entropy detection.")
