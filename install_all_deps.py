"""Install all missing dependencies recursively"""
import urllib.request, json, os, zipfile, io, sys

site_packages = None
for p in sys.path:
    if 'site-packages' in p and os.path.isdir(p):
        site_packages = p
        break
print(f"Target: {site_packages}")

installed = set()

def install_pkg(pkg_name):
    if pkg_name in installed:
        return True
    installed.add(pkg_name)
    
    print(f"\n=== {pkg_name} ===")
    try:
        api_url = f'https://pypi.org/pypi/{pkg_name}/json'
        resp = urllib.request.urlopen(api_url, timeout=15)
        data = json.loads(resp.read())
    except Exception as e:
        print(f"  SKIP (not found): {e}")
        return False
    
    ver = data['info']['version']
    print(f"  Version: {ver}")
    
    # Find py3-none-any wheel
    wheel_url = None
    for url_info in data['urls']:
        if url_info['packagetype'] == 'bdist_wheel' and 'py3-none-any' in url_info['filename']:
            wheel_url = url_info['url']
            break
    if not wheel_url:
        for url_info in data['urls']:
            if url_info['packagetype'] == 'bdist_wheel':
                wheel_url = url_info['url']
                break
    
    if not wheel_url:
        print(f"  No wheel, trying sdist...")
        for url_info in data['urls']:
            if url_info['packagetype'] == 'sdist':
                print(f"  SKIP sdist (need build): {url_info['filename']}")
                break
        return False
    
    print(f"  Downloading...")
    resp = urllib.request.urlopen(wheel_url, timeout=60)
    whl_data = resp.read()
    
    with zipfile.ZipFile(io.BytesIO(whl_data)) as zf:
        zf.extractall(site_packages)
    print(f"  OK ({len(whl_data)} bytes)")
    
    # Install dependencies
    requires = data['info'].get('requires_dist') or []
    for req in requires:
        # Parse "package[extras]>=version; extra != 'xxx'"
        # Skip extras-only deps
        if '; extra ==' in req or "; extra ==" in req:
            continue
        dep_name = req.split()[0].split('[')[0].split('>')[0].split('<')[0].split('=')[0].split('!')[0].split(';')[0]
        dep_name = dep_name.strip()
        if dep_name and dep_name not in installed:
            install_pkg(dep_name)
    
    return True

# Core packages
for pkg in ['typing-extensions', 'annotated-doc', 'anyio', 'idna', 'sniffio',
            'starlette', 'fastapi', 'uvicorn', 'python-dotenv', 'pydantic',
            'pydantic-core', 'annotated-types', 'h11', 'click',
            'httpx', 'httpcore', 'certifi', 'hpack', 'hyperframe']:
    try:
        install_pkg(pkg)
    except Exception as e:
        print(f"  FAILED: {e}")

print("\n\n=== FINAL VERIFICATION ===")
try:
    import fastapi
    print(f"  fastapi {fastapi.__version__}")
except Exception as e:
    print(f"  fastapi: {e}")
try:
    import uvicorn
    print(f"  uvicorn OK")
except Exception as e:
    print(f"  uvicorn: {e}")
try:
    import httpx
    print(f"  httpx {httpx.__version__}")
except Exception as e:
    print(f"  httpx: {e}")
try:
    import pydantic
    print(f"  pydantic {pydantic.__version__}")
except Exception as e:
    print(f"  pydantic: {e}")
