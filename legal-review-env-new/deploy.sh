#!/usr/bin/env bash
# deploy.sh — Push LegalReviewEnv to a HuggingFace Space
#
# Usage:
#   chmod +x deploy.sh
#   HF_USERNAME=yourname HF_TOKEN=hf_xxx ./deploy.sh
#
# Prerequisites: git, git-lfs, huggingface-hub (pip install huggingface-hub)

set -euo pipefail

HF_USERNAME="${HF_USERNAME:-}"
HF_TOKEN="${HF_TOKEN:-}"
SPACE_NAME="${SPACE_NAME:-legal-review-env}"
REPO_ID="${HF_USERNAME}/${SPACE_NAME}"

if [[ -z "$HF_USERNAME" || -z "$HF_TOKEN" ]]; then
  echo "ERROR: Set HF_USERNAME and HF_TOKEN environment variables."
  exit 1
fi

echo "▶ Creating HuggingFace Space: ${REPO_ID}"

# Create the Space via API (Docker SDK, public)
curl -s -X POST "https://huggingface.co/api/repos/create" \
  -H "Authorization: Bearer ${HF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"space\",
    \"name\": \"${SPACE_NAME}\",
    \"sdk\": \"docker\",
    \"private\": false
  }" | python3 -c "import sys,json; r=json.load(sys.stdin); print('Space URL:', r.get('url','(check HF)'))"

echo ""
echo "▶ Cloning Space repo..."
TMPDIR=$(mktemp -d)
git clone "https://user:${HF_TOKEN}@huggingface.co/spaces/${REPO_ID}" "$TMPDIR/space"

echo "▶ Copying project files..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Copy all project files
cp "$SCRIPT_DIR"/*.py     "$TMPDIR/space/"
cp "$SCRIPT_DIR"/*.yaml   "$TMPDIR/space/"
cp "$SCRIPT_DIR"/*.txt    "$TMPDIR/space/"
cp "$SCRIPT_DIR/Dockerfile" "$TMPDIR/space/"
cp "$SCRIPT_DIR/.gitignore" "$TMPDIR/space/"
cp "$SCRIPT_DIR/README.md"  "$TMPDIR/space/"

# Copy tests dir
mkdir -p "$TMPDIR/space/tests"
cp "$SCRIPT_DIR/tests/"*.py "$TMPDIR/space/tests/"

# HF Spaces requires the YAML frontmatter at top of README.md
# Prepend SPACES_README.md content to README.md
SPACES_HEADER=$(cat "$SCRIPT_DIR/SPACES_README.md" | head -9)
MAIN_README=$(cat "$TMPDIR/space/README.md")
echo "$SPACES_HEADER" > "$TMPDIR/space/README.md"
echo "" >> "$TMPDIR/space/README.md"
echo "$MAIN_README" >> "$TMPDIR/space/README.md"

echo "▶ Setting Space secrets..."
for VAR in API_BASE_URL MODEL_NAME; do
  VAL="${!VAR:-}"
  if [[ -n "$VAL" ]]; then
    curl -s -X POST "https://huggingface.co/api/spaces/${REPO_ID}/secrets" \
      -H "Authorization: Bearer ${HF_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"key\": \"${VAR}\", \"value\": \"${VAL}\"}" > /dev/null
    echo "  Set secret: ${VAR}"
  fi
done
# Always set HF_TOKEN as a secret too
curl -s -X POST "https://huggingface.co/api/spaces/${REPO_ID}/secrets" \
  -H "Authorization: Bearer ${HF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"key\": \"HF_TOKEN\", \"value\": \"${HF_TOKEN}\"}" > /dev/null
echo "  Set secret: HF_TOKEN"

echo "▶ Committing and pushing..."
cd "$TMPDIR/space"
git config user.email "deploy@legal-review-env"
git config user.name "LegalReviewEnv Deploy"
git add -A
git commit -m "Deploy LegalReviewEnv v1.0.0"
git push

echo ""
echo "✅ Deployed! Your Space is building at:"
echo "   https://huggingface.co/spaces/${REPO_ID}"
echo ""
echo "Once live, run the validator:"
echo "   SPACE_URL=https://${HF_USERNAME}-${SPACE_NAME}.hf.space ./validate.sh"

rm -rf "$TMPDIR"
