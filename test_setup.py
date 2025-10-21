#!/usr/bin/env python3
"""
Validate RedShift Chatbot setup and configuration.
"""

import sys
from pathlib import Path


def check_env_file():
    """Check if .env file exists and has required variables."""
    if not Path('.env').exists():
        print("❌ .env file not found")
        return False
    
    required_vars = [
        'AWS_REGION',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'REDSHIFT_HOST',
        'REDSHIFT_DATABASE',
        'REDSHIFT_USER',
        'REDSHIFT_PASSWORD'
    ]
    
    with open('.env', 'r') as f:
        env_content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if var not in env_content or f'{var}=your_' in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(
            f"⚠️  Missing or unconfigured variables: "
            f"{', '.join(missing_vars)}"
        )
        print("   Please update your .env file with actual credentials")
        return False
    
    print("✅ Environment variables configured")
    return True


def check_python_version():
    """Check if Python version is 3.9 or higher."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(
            f"❌ Python 3.9+ required "
            f"(you have {version.major}.{version.minor})"
        )
        return False
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """Check if required Python packages are installed."""
    required_packages = [
        'flask',
        'boto3',
        'psycopg2',
        'dotenv'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    print("✅ Required packages installed")
    return True


def check_project_structure():
    """Check if required directories and files exist."""
    required_paths = [
        'modules/',
        'static/',
        'templates/',
        'app.py',
        'config.py',
        'requirements.txt'
    ]
    
    missing = []
    for path in required_paths:
        if not Path(path).exists():
            missing.append(path)
    
    if missing:
        print(f"❌ Missing files/directories: {', '.join(missing)}")
        return False
    
    print("✅ Project structure intact")
    return True


def main():
    """Run all validation checks."""
    print("\n🔍 Validating RedShift Chatbot Setup")
    print("=" * 40)
    
    checks = [
        ("Python Version", check_python_version),
        ("Project Structure", check_project_structure),
        ("Dependencies", check_dependencies),
        ("Environment Config", check_env_file),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✅ All checks passed! Ready to start.")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())