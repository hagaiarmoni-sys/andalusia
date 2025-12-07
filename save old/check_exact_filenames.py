"""
List exact filenames in data directory
This will show any hidden characters or encoding issues
"""
import os

print("=" * 70)
print("FILENAME DIAGNOSTIC")
print("=" * 70)
print()

# Check if data directory exists
if os.path.exists("data"):
    print("✅ data/ directory exists")
    print()
    
    # List all files
    files = os.listdir("data")
    print(f"Found {len(files)} files in data/:")
    print("-" * 70)
    
    for filename in sorted(files):
        # Show the filename
        print(f"\nFilename: '{filename}'")
        
        # Show the bytes (to detect hidden characters)
        filename_bytes = filename.encode('utf-8')
        print(f"Bytes: {filename_bytes}")
        
        # Show length
        print(f"Length: {len(filename)} characters")
        
        # Check if it contains "attractions"
        if "attraction" in filename.lower():
            print("👉 THIS IS YOUR ATTRACTIONS FILE")
            
            # Try to construct the full path
            full_path = os.path.join("data", filename)
            print(f"Full path: '{full_path}'")
            print(f"File exists: {os.path.exists(full_path)}")
            
            # Get file size
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                print(f"File size: {size:,} bytes ({size/1024:.1f} KB)")
        
        print("-" * 70)
    
    print()
    print("=" * 70)
    print("SOLUTION")
    print("=" * 70)
    
    # Find the attractions file
    attractions_files = [f for f in files if "attraction" in f.lower() and f.endswith(".json")]
    
    if attractions_files:
        actual_filename = attractions_files[0]
        print(f"\n✅ Found attractions file: '{actual_filename}'")
        
        if actual_filename != "andalusia_attractions_filtered.json":
            print()
            print("⚠️  FILENAME MISMATCH!")
            print(f"   Expected: 'andalusia_attractions_filtered.json'")
            print(f"   Actual:   '{actual_filename}'")
            print()
            print("SOLUTION:")
            print(f"   Rename the file to: andalusia_attractions_filtered.json")
            print()
            print("PowerShell command:")
            print(f'   Rename-Item "data\\{actual_filename}" "andalusia_attractions_filtered.json"')
        else:
            print()
            print("✅ Filename is correct!")
            print()
            print("The file should be loading... check if there's a caching issue:")
            print("1. Close Streamlit (Ctrl+C)")
            print("2. Delete __pycache__: Remove-Item -Recurse -Force __pycache__")
            print("3. Restart: streamlit run app.py")
    else:
        print("\n❌ No attractions file found in data/ directory!")
        print()
        print("Please make sure you have a file named:")
        print("   andalusia_attractions_filtered.json")
        print("in the data/ subdirectory")
        
else:
    print("❌ data/ directory does NOT exist!")
    print()
    print("Current directory:", os.getcwd())
    print()
    print("Files in current directory:")
    for f in os.listdir('.'):
        print(f"   {f}")