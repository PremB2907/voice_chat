import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract styles
style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
if style_match:
    styles = style_match.group(1).strip()
    with open('frontend/style.css', 'w', encoding='utf-8') as f:
        f.write(styles)

# Extract scripts
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    script = script_match.group(1).strip()
    with open('frontend/app.js', 'w', encoding='utf-8') as f:
        f.write(script)

# Replace in HTML
new_content = re.sub(r'<style>.*?</style>', '<link rel="stylesheet" href="frontend/style.css"/>', content, flags=re.DOTALL)
new_content = re.sub(
    r'<script>.*?</script>', 
    '<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.8/dist/purify.min.js"></script>\n'
    '<script src="frontend/app.js" defer></script>', 
    new_content, 
    flags=re.DOTALL
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Split complete.')
