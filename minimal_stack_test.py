"""
Minimal Stack Test - No application code, just pure stack testing
Deploy this as code.py to measure absolute maximum stack capacity
"""

import time

print("=== MINIMAL STACK TEST (NO APPLICATION CODE) ===")
print("Testing absolute stack limits on CircuitPython...")
print()

# Test 1: Pure recursion (no local variables)
def test_pure_recursion(depth=0):
	if depth > 200:  # Safety limit
		return depth
	try:
		return test_pure_recursion(depth + 1)
	except:
		return depth

pure_depth = test_pure_recursion(0)
print(f"1. Pure recursion (no locals): {pure_depth} levels")

# Test 2: Recursion with local variables (realistic)
def test_with_locals(depth=0):
	if depth > 200:
		return depth
	try:
		# Realistic local variables
		data = {"depth": depth, "test": [1, 2, 3, 4, 5]}
		temp = [x * 2 for x in range(10)]
		return test_with_locals(depth + 1)
	except:
		return depth

local_depth = test_with_locals(0)
print(f"2. With local vars (realistic): {local_depth} levels")

# Test 3: Nested try/except (single level)
def test_single_try(depth=0):
	if depth > 200:
		return depth
	try:
		data = {"depth": depth}
		return test_single_try(depth + 1)
	except:
		return depth

single_try_depth = test_single_try(0)
print(f"3. Single try/except: {single_try_depth} levels")

# Test 4: Double-nested try/except
def test_double_nested_try(depth=0):
	if depth > 200:
		return depth
	try:
		try:
			data = {"depth": depth}
			return test_double_nested_try(depth + 1)
		except:
			pass
	except:
		return depth

double_try_depth = test_double_nested_try(0)
print(f"4. Double-nested try/except: {double_try_depth} levels")

# Test 5: Triple-nested try/except (the crash pattern)
def test_triple_nested_try(depth=0):
	if depth > 200:
		return depth
	try:
		try:
			try:
				data = {"depth": depth}
				return test_triple_nested_try(depth + 1)
			except:
				pass
		except:
			pass
	except:
		return depth

triple_try_depth = test_triple_nested_try(0)
print(f"5. Triple-nested try/except: {triple_try_depth} levels")

print()
print("=== COMPARISON ===")
print(f"Pure recursion:        {pure_depth} levels (baseline)")
print(f"With locals:           {local_depth} levels (cost: {pure_depth - local_depth})")
print(f"Single try/except:     {single_try_depth} levels (cost: {pure_depth - single_try_depth})")
print(f"Double-nested try:     {double_try_depth} levels (cost: {pure_depth - double_try_depth})")
print(f"Triple-nested try:     {triple_try_depth} levels (cost: {pure_depth - triple_try_depth})")
print()

# Calculate overhead of nesting
single_overhead = pure_depth - single_try_depth
double_overhead = pure_depth - double_try_depth
triple_overhead = pure_depth - triple_try_depth

print("=== OVERHEAD ANALYSIS ===")
print(f"Each try/except level costs: ~{single_overhead} stack units")
print(f"Double nesting overhead: {double_overhead} units (factor: {double_overhead/max(single_overhead,1):.1f}x)")
print(f"Triple nesting overhead: {triple_overhead} units (factor: {triple_overhead/max(single_overhead,1):.1f}x)")
print()

# Interpretation
print("=== INTERPRETATION ===")
if pure_depth > 30:
	print(f"✅ Baseline stack is EXCELLENT ({pure_depth} levels)")
	print("   Your application code is consuming most of the stack")
elif pure_depth > 15:
	print(f"⚠️  Baseline stack is MODERATE ({pure_depth} levels)")
	print("   CircuitPython has limited stack, careful with nesting")
else:
	print(f"🔴 Baseline stack is VERY LIMITED ({pure_depth} levels)")
	print("   CircuitPython stack is extremely constrained")

print()
print("Compare these numbers to your application:")
print(f"  Application recursion depth: 12 levels")
print(f"  Minimal test recursion: {local_depth} levels")
print(f"  Application overhead: {local_depth - 12} levels")
print()
print("This overhead comes from:")
print("  - Imported modules (displayio, wifi, etc)")
print("  - Global state objects")
print("  - Function call stack before tests")
print()
print("=== END MINIMAL STACK TEST ===")

# Keep display on
while True:
	time.sleep(1)
