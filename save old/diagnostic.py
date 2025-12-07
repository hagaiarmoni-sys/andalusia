#!/usr/bin/env python3
"""
Diagnostic script - Run this in your andalusia-app folder
to check if you have the updated files
"""

import os
import sys

print("=" * 70)
print("DIAGNOSTIC: Checking City Normalization Fix")
print("=" * 70)
print()

# Check 1: Does text_norm.py exist?
print("CHECK 1: text_norm.py file")
if os.path.exists('text_norm.py'):
    print("  ✅ PASS: text_norm.py exists")
    try:
        from text_norm import canonicalize_city, CITY_ALIASES
        print("  ✅ PASS: Can import canonicalize_city")
        print(f"  ✅ PASS: CITY_ALIASES has {len(CITY_ALIASES)} entries")
    except ImportError as e:
        print(f"  ❌ FAIL: Cannot import: {e}")
else:
    print("  ❌ FAIL: text_norm.py NOT FOUND")
    print("  → You need to add text_norm.py to your project folder")
print()

# Check 2: Does itinerary_generator_car.py have the import?
print("CHECK 2: itinerary_generator_car.py")
if os.path.exists('itinerary_generator_car.py'):
    with open('itinerary_generator_car.py', 'r') as f:
        content = f.read()
    
    if 'from text_norm import canonicalize_city' in content:
        print("  ✅ PASS: Has 'from text_norm import canonicalize_city'")
    else:
        print("  ❌ FAIL: Missing 'from text_norm import canonicalize_city'")
        print("  → You're running the OLD version!")
        print("  → Replace itinerary_generator_car.py with the updated version")
    
    # Check for the new validation code
    if 'start_city_canonical = canonicalize_city' in content:
        print("  ✅ PASS: Has canonicalization code")
    else:
        print("  ❌ FAIL: Missing canonicalization code")
        print("  → Replace itinerary_generator_car.py with the updated version")
else:
    print("  ❌ FAIL: itinerary_generator_car.py NOT FOUND")
print()

# Check 3: Does trip_planner_page.py have normalize_start_end_text?
print("CHECK 3: trip_planner_page.py")
if os.path.exists('trip_planner_page.py'):
    with open('trip_planner_page.py', 'r') as f:
        content = f.read()
    
    if 'def normalize_start_end_text' in content:
        print("  ✅ PASS: Has normalize_start_end_text function")
    else:
        print("  ❌ FAIL: Missing normalize_start_end_text function")
        print("  → Replace trip_planner_page.py with the updated version")
    
    if 'from text_norm import canonicalize_city' in content:
        print("  ✅ PASS: Has text_norm import")
    else:
        print("  ❌ FAIL: Missing text_norm import")
        print("  → Replace trip_planner_page.py with the updated version")
else:
    print("  ❌ FAIL: trip_planner_page.py NOT FOUND")
print()

# Check 4: Test the actual functionality
print("CHECK 4: Functional test")
try:
    from text_norm import canonicalize_city
    
    # Create a mock known_cities set
    known_cities = {'Málaga', 'Seville', 'Córdoba', 'Granada'}
    
    test_cases = [
        ('Malaga', 'Málaga'),
        ('Seville', 'Seville'),
        ('seville', 'Seville'),
    ]
    
    all_passed = True
    for input_val, expected in test_cases:
        result = canonicalize_city(input_val, known_cities)
        if result == expected:
            print(f"  ✅ '{input_val}' → '{result}'")
        else:
            print(f"  ❌ '{input_val}' → '{result}' (expected '{expected}')")
            all_passed = False
    
    if all_passed:
        print("  ✅ PASS: All functional tests passed")
    else:
        print("  ❌ FAIL: Some functional tests failed")
        
except Exception as e:
    print(f"  ❌ FAIL: Error during functional test: {e}")
print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)

# Count checks
checks = []
if os.path.exists('text_norm.py'):
    try:
        from text_norm import canonicalize_city
        checks.append(True)
    except:
        checks.append(False)
else:
    checks.append(False)

if os.path.exists('itinerary_generator_car.py'):
    with open('itinerary_generator_car.py', 'r') as f:
        content = f.read()
    checks.append('from text_norm import canonicalize_city' in content)
else:
    checks.append(False)

if os.path.exists('trip_planner_page.py'):
    with open('trip_planner_page.py', 'r') as f:
        content = f.read()
    checks.append('def normalize_start_end_text' in content)
else:
    checks.append(False)

passed = sum(checks)
total = len(checks)

if passed == total:
    print("🎉 ALL CHECKS PASSED - Fix is properly deployed!")
    print()
    print("If you're still getting errors:")
    print("1. Stop your Streamlit app (Ctrl+C)")
    print("2. Delete Python cache: rm -rf __pycache__ *.pyc")
    print("3. Restart: streamlit run app.py")
else:
    print(f"⚠️  {passed}/{total} checks passed")
    print()
    print("ACTION REQUIRED:")
    print("1. Copy these files to your project folder:")
    print("   - text_norm.py")
    print("   - itinerary_generator_car.py")
    print("   - trip_planner_page.py")
    print("2. Delete Python cache: rm -rf __pycache__ *.pyc")
    print("3. Restart your app")

print("=" * 70)