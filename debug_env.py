import os
import sys

print(f"Python Executable: {sys.executable}")
print(f"CWD: {os.getcwd()}")

print("-" * 20)
print("Checking .env file:")
if os.path.exists(".env"):
    print("✅ .env exists")
    with open(".env", "r") as f:
        content = f.read()
        print(f"Content length: {len(content)}")
        print("First 20 chars:", content[:20])
else:
    print("❌ .env NOT found")

print("-" * 20)
print("Checking python-dotenv:")
try:
    import dotenv
    print(f"✅ dotenv imported: {dotenv.__file__}")
    
    from dotenv import load_dotenv
    loaded = load_dotenv()
    print(f"load_dotenv() returned: {loaded}")
    
except ImportError:
    print("❌ python-dotenv NOT installed")

print("-" * 20)
print("Checking Environment Variable:")
token = os.environ.get("AIPROXY_TOKEN")
if token:
    print(f"✅ AIPROXY_TOKEN found: {token[:5]}...")
else:
    print("❌ AIPROXY_TOKEN is None")
