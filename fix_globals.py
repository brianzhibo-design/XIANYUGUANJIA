with open('src/dashboard_server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith('class DashboardHandler(BaseHTTPRequestHandler):'):
        lines.insert(i, "_product_image_cache: dict[str, tuple[str, float]] = {}\n")
        lines.insert(i+1, "_PRODUCT_IMAGE_CACHE_TTL = 1800\n\n")
        break

with open('src/dashboard_server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
