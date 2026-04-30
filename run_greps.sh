cd /raid5/source/test/prism
echo "=== OPEN WITHOUT ENCODING ==="
grep -rn "open(" src/prism/scanner_config src/prism/scanner_io src/prism/scanner_readme src/prism/scanner_extract src/prism/cli_app src/prism/api_layer --include="*.py" | grep -v "encoding="
echo "=== EXCEPT THEN PASS OR RETURN ==="
grep -rn -A2 "except.*:" src/prism/scanner_config src/prism/scanner_io src/prism/scanner_readme src/prism/scanner_extract src/prism/cli_app src/prism/api_layer --include="*.py" | grep -B1 "^\-\-\|pass$\|return None$\|return {}$\|return \[\]$" | head -80
echo "=== OR EMPTY DICT/LIST/NONE PATTERNS ==="
grep -rn " or {}\| or \[\]\| or None\b\| or \"\"" src/prism/scanner_config src/prism/scanner_io src/prism/scanner_readme src/prism/scanner_extract src/prism/cli_app src/prism/api_layer --include="*.py" | head -40
echo "=== BARE EXCEPT ==="
grep -rn "^\s*except\s*:" src/prism/scanner_config src/prism/scanner_io src/prism/scanner_readme src/prism/scanner_extract src/prism/cli_app src/prism/api_layer --include="*.py"
echo "=== EXCEPT WITHOUT LOGGING ==="
grep -rn "except.*Exception" src/prism/scanner_config src/prism/scanner_io src/prism/scanner_readme src/prism/scanner_extract src/prism/cli_app src/prism/api_layer --include="*.py"
echo "=== LONG PARAMETER FUNCTIONS (approximate) ==="
grep -rn "^def \|^    def " src/prism/scanner_config src/prism/scanner_io src/prism/scanner_readme src/prism/scanner_extract src/prism/cli_app src/prism/api_layer --include="*.py" | grep -E "\w+\s*\([^)]*,[^)]*,[^)]*,[^)]*,[^)]*," | head -20
echo "=== FILES LIST ==="
find src/prism/scanner_config src/prism/scanner_io src/prism/scanner_readme src/prism/scanner_extract src/prism/cli_app src/prism/api_layer -name "*.py" | sort
