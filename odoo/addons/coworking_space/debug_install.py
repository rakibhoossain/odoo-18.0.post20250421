#!/usr/bin/env python3
"""
Debug script to identify installation issues
Run this to get detailed information about potential problems
"""

import os
import sys
import subprocess
import xml.etree.ElementTree as ET

def check_odoo_version():
    """Check if we can determine Odoo version"""
    print("🔍 Checking Odoo environment...")
    
    # Try to find Odoo installation
    possible_paths = [
        '../../..',  # If we're in addons/coworking_space
        '../../../odoo',
        '/opt/odoo',
        '/usr/lib/python3/dist-packages/odoo',
    ]
    
    for path in possible_paths:
        version_file = os.path.join(path, 'odoo', 'release.py')
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    content = f.read()
                    if 'version_info' in content:
                        print(f"✅ Found Odoo installation at: {path}")
                        # Extract version info
                        lines = content.split('\n')
                        for line in lines:
                            if 'version_info' in line or 'version =' in line:
                                print(f"   {line.strip()}")
                        return True
            except Exception as e:
                print(f"⚠️  Could not read version from {version_file}: {e}")
    
    print("❌ Could not find Odoo installation")
    return False

def check_xml_files():
    """Check XML files for syntax errors"""
    print("\n🔍 Checking XML files...")
    
    xml_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))
    
    errors = []
    for xml_file in xml_files:
        try:
            ET.parse(xml_file)
            print(f"✅ {xml_file}")
        except ET.ParseError as e:
            print(f"❌ {xml_file}: {e}")
            errors.append((xml_file, str(e)))
        except Exception as e:
            print(f"⚠️  {xml_file}: {e}")
            errors.append((xml_file, str(e)))
    
    return len(errors) == 0

def check_csv_files():
    """Check CSV files for format issues"""
    print("\n🔍 Checking CSV files...")
    
    csv_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(os.path.join(root, file))
    
    errors = []
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r') as f:
                lines = f.readlines()
                
            # Check header
            if lines and not lines[0].startswith('id,name,model_id:id'):
                print(f"⚠️  {csv_file}: Unusual header format")
            
            # Check each line has same number of columns
            if len(lines) > 1:
                header_cols = len(lines[0].split(','))
                for i, line in enumerate(lines[1:], 2):
                    if line.strip() and len(line.split(',')) != header_cols:
                        print(f"❌ {csv_file}:{i}: Column count mismatch")
                        errors.append((csv_file, f"Line {i} column count mismatch"))
                        break
            
            if csv_file not in [e[0] for e in errors]:
                print(f"✅ {csv_file}")
                
        except Exception as e:
            print(f"❌ {csv_file}: {e}")
            errors.append((csv_file, str(e)))
    
    return len(errors) == 0

def check_dependencies():
    """Check if dependencies are likely available"""
    print("\n🔍 Checking dependencies...")
    
    # Read manifest
    try:
        with open('__manifest__.py', 'r') as f:
            content = f.read()
        
        # Extract dependencies
        import ast
        manifest = ast.literal_eval(content)
        depends = manifest.get('depends', [])
        
        print(f"Required dependencies: {depends}")
        
        # Common Odoo modules that should be available
        common_modules = [
            'base', 'web', 'website', 'sale', 'account', 'crm', 
            'portal', 'calendar', 'product', 'stock', 'hr'
        ]
        
        missing_common = []
        for dep in depends:
            if dep in common_modules:
                print(f"✅ {dep} (common module)")
            else:
                print(f"⚠️  {dep} (may not be installed)")
                missing_common.append(dep)
        
        if missing_common:
            print(f"\n💡 Consider installing these modules first: {missing_common}")
            print("   Or comment them out in __manifest__.py for testing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking dependencies: {e}")
        return False

def suggest_fixes():
    """Suggest potential fixes"""
    print("\n💡 Suggested fixes for 'Cancel Install' error:")
    print("=" * 50)
    
    fixes = [
        "1. Restart Odoo server completely",
        "2. Update Apps List (Apps → Update Apps List)",
        "3. Enable Developer Mode and try again",
        "4. Check Odoo server logs for detailed error messages",
        "5. Try installing dependencies first (if any are missing)",
        "6. Use command line installation:",
        "   ./odoo-bin -d your_db -i coworking_space --stop-after-init",
        "7. Try with a fresh database",
        "8. Check file permissions (chmod -R 755 coworking_space/)",
        "9. Verify addon is in correct addons path",
        "10. Try minimal version first (use __manifest_minimal__.py)"
    ]
    
    for fix in fixes:
        print(f"   {fix}")

def main():
    print("🐛 Coworking Space Addon Debug Tool")
    print("=" * 50)
    
    # Change to addon directory
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(addon_dir)
    
    checks = [
        ("Odoo environment", check_odoo_version),
        ("XML syntax", check_xml_files),
        ("CSV format", check_csv_files),
        ("Dependencies", check_dependencies),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}:")
        if not check_func():
            all_passed = False
    
    suggest_fixes()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ No obvious issues found.")
        print("The 'Cancel Install' error is likely due to:")
        print("   - Server configuration issues")
        print("   - Missing dependencies")
        print("   - Database permissions")
        print("   - Odoo version compatibility")
    else:
        print("❌ Issues found above. Fix them and try again.")
    
    print(f"\n📁 Current directory: {os.getcwd()}")
    print(f"📁 Addon files: {len([f for f in os.listdir('.') if not f.startswith('.')])}")

if __name__ == "__main__":
    main()
