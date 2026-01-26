#!/usr/bin/env bash
# Verify that all source code files use LF line endings only (per Constitution v1.2.0)
# This script checks source files and reports any with CRLF or mixed line endings.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Verifying source file line endings per Constitution v1.2.0..."
echo ""

# Find all source code files (excluding data files, git, venv, etc.)
SOURCE_FILES=$(find . -type f \
  \( -name "*.py" -o -name "*.md" -o -name "*.toml" -o -name "*.yaml" -o -name "*.yml" \
     -o -name "*.json" -o -name "*.txt" -o -name "*.sh" -o -name "*.ini" -o -name "*.cfg" \
     -o -name "*.editorconfig" -o -name "*.gitattributes" -o -name "*.gitignore" \) \
  -not -path "./.git/*" \
  -not -path "./.venv/*" \
  -not -path "./venv/*" \
  -not -path "./htmlcov/*" \
  -not -path "./.pytest_cache/*" \
  -not -path "*/__pycache__/*" \
  -not -path "*.egg-info/*" \
  -not -path "./node_modules/*" \
  -not -path "./.mypy_cache/*" \
  -not -path "./.ruff_cache/*" \
  2>/dev/null || true)

if [ -z "$SOURCE_FILES" ]; then
  echo -e "${YELLOW}⚠️  No source files found${NC}"
  exit 0
fi

TOTAL_FILES=0
CRLF_FILES=0
CRLF_FILE_LIST=()

while IFS= read -r file; do
  if [ -f "$file" ]; then
    TOTAL_FILES=$((TOTAL_FILES + 1))

    # Check for CRLF line endings using file command
    if file "$file" | grep -qi "CRLF"; then
      CRLF_FILES=$((CRLF_FILES + 1))
      CRLF_FILE_LIST+=("$file")
      echo -e "${RED}✗${NC} $file (has CRLF line endings)"
    fi
  fi
done <<< "$SOURCE_FILES"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Results:"
echo "   Total source files checked: $TOTAL_FILES"
echo "   Files with CRLF endings:    $CRLF_FILES"
echo ""

if [ $CRLF_FILES -eq 0 ]; then
  echo -e "${GREEN}✅ All source files use LF line endings${NC}"
  echo ""
  echo "Constitution v1.2.0 compliance: PASS"
  exit 0
else
  echo -e "${RED}❌ Found $CRLF_FILES file(s) with CRLF line endings${NC}"
  echo ""
  echo "To fix, run:"
  echo "  dos2unix ${CRLF_FILE_LIST[*]}"
  echo ""
  echo "Or configure git to auto-convert:"
  echo "  git config core.autocrlf input"
  echo ""
  echo "Constitution v1.2.0 compliance: FAIL"
  exit 1
fi
