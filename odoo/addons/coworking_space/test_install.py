#!/usr/bin/env python3
"""
Test script to check if the coworking_space addon can be installed
Run this script to diagnose installation issues
"""

import os
import sys
import ast

def check_manifest():
    """Check if __manifest__.py is valid"""
    manifest_path = '__manifest__.py'
    if not os.path.exists(manifest_path):
        print("❌ __manifest__.py not found")
        return False
    
    try:
        with open(manifest_path, 'r') as f:
            content = f.read()
        
        # Parse the manifest
        manifest = ast.literal_eval(content)
        print("✅ __manifest__.py is valid Python")
        
        # Check required fields
        required_fields = ['name', 'version', 'depends', 'data']
        for field in required_fields:
            if field in manifest:
                print(f"✅ {field}: {manifest[field] if field != 'data' else f'{len(manifest[field])} files'}")
            else:
                print(f"❌ Missing required field: {field}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error parsing __manifest__.py: {e}")
        return False

def check_files():
    """Check if all referenced files exist"""
    manifest_path = '__manifest__.py'
    
    try:
        with open(manifest_path, 'r') as f:
            content = f.read()
        manifest = ast.literal_eval(content)
        
        print("\n📁 Checking data files:")
        missing_files = []
        
        for file_path in manifest.get('data', []):
            if os.path.exists(file_path):
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path} - NOT FOUND")
                missing_files.append(file_path)
        
        if missing_files:
            print(f"\n⚠️  {len(missing_files)} files are missing")
            return False
        else:
            print("\n✅ All data files exist")
            return True
            
    except Exception as e:
        print(f"❌ Error checking files: {e}")
        return False

def check_python_syntax():
    """Check Python files for syntax errors"""
    print("\n🐍 Checking Python syntax:")
    
    python_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    errors = []
    for py_file in python_files:
        try:
            with open(py_file, 'r') as f:
                compile(f.read(), py_file, 'exec')
            print(f"✅ {py_file}")
        except SyntaxError as e:
            print(f"❌ {py_file}: {e}")
            errors.append((py_file, str(e)))
    
    if errors:
        print(f"\n⚠️  {len(errors)} Python files have syntax errors")
        return False
    else:
        print("\n✅ All Python files have valid syntax")
        return True

def main():
    print("🔍 Coworking Space Addon Installation Check")
    print("=" * 50)
    
    # Change to addon directory
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(addon_dir)
    
    checks = [
        ("Manifest file", check_manifest),
        ("Data files", check_files),
        ("Python syntax", check_python_syntax),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All checks passed! The addon should install correctly.")
        print("\n💡 If you still get 'Cancel Install', try:")
        print("   1. Restart Odoo server")
        print("   2. Update Apps List")
        print("   3. Check Odoo logs for detailed error messages")
        print("   4. Ensure all dependencies are installed")
    else:
        print("❌ Some checks failed. Fix the issues above before installing.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
