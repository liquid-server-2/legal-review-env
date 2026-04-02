#!/usr/bin/env bash
# validate.sh — Pre-submission validation for LegalReviewEnv
#
# Usage:
#   SPACE_URL=https://yourname-legal-review-env.hf.space ./validate.sh
#   or for local:
#   SPACE_URL=http://localhost:7860 ./validate.sh
#
# Checks:
#   Step 1 — HF Space /reset returns HTTP 200
#   Step 2 — docker build succeeds
#   Step 3 — openenv validate passes

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
NC="\033[0m"

SPACE_URL="${SPACE_URL:-http://localhost:7860}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCKER_BUILD_TIMEOUT="${DOCKER_BUILD_TIMEOUT:-300}"

pass()  { echo -e "  ${GREEN}${BOLD}✓ PASS${NC}  $*"; }
fail()  { echo -e "  ${RED}${BOLD}✗ FAIL${NC}  $*"; }
warn()  { echo -e "  ${YELLOW}⚠ WARN${NC}  $*"; }
log()   { echo -e "$*"; }

run_with_timeout() {
  local timeout=$1; shift
  if command -v timeout &>/dev/null; then
    timeout "$timeout" "$@"
  else
    "$@"
  fi
}

echo ""
echo -e "${BOLD}================================================${NC}"
echo -e "${BOLD}  LegalReviewEnv — Pre-Submission Validator${NC}"
echo -e "${BOLD}================================================${NC}"
echo ""

FAILURES=0

# ── Step 1: HF Space ping ────────────────────────────────────────────────────
log "${BOLD}Step 1/3: Pinging ${SPACE_URL}/reset${NC}"

RESET_PAYLOAD='{"task_id":"clause_identification"}'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${SPACE_URL}/reset" \
  -H "Content-Type: application/json" \
  -d "$RESET_PAYLOAD" \
  --max-time 30 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
  pass "POST /reset returned HTTP 200"

  # Also validate the response shape
  BODY=$(curl -s -X POST "${SPACE_URL}/reset" \
    -H "Content-Type: application/json" \
    -d "$RESET_PAYLOAD" --max-time 30 2>/dev/null || echo "{}")
  if echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'contract_text' in d and 'task_id' in d" 2>/dev/null; then
    pass "Response contains required fields (contract_text, task_id)"
  else
    warn "Response shape unexpected — check Observation model"
  fi

  # Test /step
  STEP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${SPACE_URL}/step" \
    -H "Content-Type: application/json" \
    -d '{"action_type":"done","payload":{}}' \
    --max-time 30 2>/dev/null || echo "000")
  if [[ "$STEP_CODE" == "200" ]]; then
    pass "POST /step returned HTTP 200"
  else
    fail "POST /step returned HTTP $STEP_CODE"
    ((FAILURES++))
  fi

  # Test /state
  STATE_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    "${SPACE_URL}/state" --max-time 30 2>/dev/null || echo "000")
  if [[ "$STATE_CODE" == "200" ]]; then
    pass "GET /state returned HTTP 200"
  else
    fail "GET /state returned HTTP $STATE_CODE"
    ((FAILURES++))
  fi

  # Test all 3 tasks
  for TASK in clause_identification risk_flagging negotiation_strategy; do
    TC=$(curl -s -o /dev/null -w "%{http_code}" \
      -X POST "${SPACE_URL}/reset" \
      -H "Content-Type: application/json" \
      -d "{\"task_id\":\"${TASK}\"}" \
      --max-time 30 2>/dev/null || echo "000")
    if [[ "$TC" == "200" ]]; then
      pass "Task '${TASK}' reachable"
    else
      fail "Task '${TASK}' reset returned HTTP $TC"
      ((FAILURES++))
    fi
  done

else
  fail "POST /reset returned HTTP $HTTP_CODE (expected 200)"
  echo "    → Make sure the server is running at ${SPACE_URL}"
  ((FAILURES++))
fi

echo ""

# ── Step 2: docker build ─────────────────────────────────────────────────────
log "${BOLD}Step 2/3: Running docker build${NC}"

if ! command -v docker &>/dev/null; then
  warn "docker not found — skipping build check"
  warn "Install Docker: https://docs.docker.com/get-docker/"
else
  DOCKERFILE_DIR=""
  if [[ -f "$SCRIPT_DIR/Dockerfile" ]]; then
    DOCKERFILE_DIR="$SCRIPT_DIR"
  elif [[ -f "$SCRIPT_DIR/server/Dockerfile" ]]; then
    DOCKERFILE_DIR="$SCRIPT_DIR/server"
  fi

  if [[ -z "$DOCKERFILE_DIR" ]]; then
    fail "No Dockerfile found"
    ((FAILURES++))
  else
    log "  Building from $DOCKERFILE_DIR ..."
    BUILD_OK=false
    BUILD_OUTPUT=$(run_with_timeout "$DOCKER_BUILD_TIMEOUT" docker build "$DOCKERFILE_DIR" -t legal-review-env:validate 2>&1) && BUILD_OK=true

    if $BUILD_OK; then
      pass "docker build succeeded"
    else
      fail "docker build failed"
      echo "$BUILD_OUTPUT" | tail -20
      ((FAILURES++))
    fi
  fi
fi

echo ""

# ── Step 3: openenv validate ─────────────────────────────────────────────────
log "${BOLD}Step 3/3: Running openenv validate${NC}"

if ! command -v openenv &>/dev/null; then
  warn "openenv CLI not found"
  warn "Install: pip install openenv-core"
  warn "Skipping — install and re-run before submitting"
else
  cd "$SCRIPT_DIR"
  VALIDATE_OK=false
  VALIDATE_OUTPUT=$(openenv validate 2>&1) && VALIDATE_OK=true

  if $VALIDATE_OK; then
    pass "openenv validate passed"
    [[ -n "$VALIDATE_OUTPUT" ]] && log "  $VALIDATE_OUTPUT"
  else
    fail "openenv validate failed"
    echo "$VALIDATE_OUTPUT"
    ((FAILURES++))
  fi
fi

echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
echo -e "${BOLD}================================================${NC}"
if [[ $FAILURES -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}  ✓ All checks passed — ready to submit!${NC}"
else
  echo -e "${RED}${BOLD}  ✗ ${FAILURES} check(s) failed — fix before submitting${NC}"
fi
echo -e "${BOLD}================================================${NC}"
echo ""

exit $FAILURES
