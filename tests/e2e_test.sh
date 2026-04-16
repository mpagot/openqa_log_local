#!/usr/bin/env bash

# e2e_test.sh - End-to-end tests for openqa-log-local
# Runs all commands in an isolated temporary directory

set -euo pipefail

# Require hostname and job_id as arguments
HOST="${1:?Usage: $0 <hostname> <job_id>}"
JOB_ID="${2:?Usage: $0 <hostname> <job_id>}"

# Get the absolute path to the project root
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- Setup temp dir & cleanup trap ---
TMPWORKDIR=$(mktemp -d)
trap 'echo "Cleaning up temp dir: $TMPWORKDIR"; rm -rf "$TMPWORKDIR"' EXIT

echo "Running tests in isolated temp directory: $TMPWORKDIR"
cd "$TMPWORKDIR"

# Counters
PASS=0
FAIL=0
TOTAL=0

# --- Helper functions ---
run_cli() {
	# Run the CLI using uv, pointing back to the project directory
	uv run --project "$PROJECT_DIR" openqa-log-local "$@"
}

pass_test() {
	local name="$1"
	local time_ms="$2"
	PASS=$((PASS + 1))
	TOTAL=$((TOTAL + 1))
	echo -e "[\033[32mPASS\033[0m] (${time_ms}ms) $name"
}

fail_test() {
	local name="$1"
	local time_ms="$2"
	local error_details="${3:-}"
	FAIL=$((FAIL + 1))
	TOTAL=$((TOTAL + 1))
	echo -e "[\033[31mFAIL\033[0m] (${time_ms}ms) $name"
	if [ -n "$error_details" ]; then
		echo -e "       Details: \033[33m$error_details\033[0m"
	fi
}

start_timer() {
	date +%s%3N
}

end_timer() {
	local start="$1"
	local end=$(date +%s%3N)
	echo $((end - start))
}

echo "========================================================="
echo "Starting E2E tests for openqa-log-local"
echo "Host:   $HOST"
echo "Job ID: $JOB_ID"
echo "========================================================="
echo ""

# --- Test 1: CLI Help ---
# search for a subcommand ("get-details") in the main --help
name="CLI --help displays get-details"
t0=$(start_timer)
if output=$(run_cli --help 2>&1) && echo "$output" | grep -q "get-details"; then
	pass_test "$name" $(end_timer $t0)
else
	fail_test "$name" $(end_timer $t0) "$output"
fi

# --- Test 2: CLI Version ---
name="CLI --version displays version"
t0=$(start_timer)
if output=$(run_cli --version 2>&1) && echo "$output" | grep -Eq "version [0-9]+\.[0-9]+\.[0-9]+"; then
	pass_test "$name" $(end_timer $t0)
else
	fail_test "$name" $(end_timer $t0) "$output"
fi

# --- Test 3: get-details (cold start) ---
name="get-details returns valid JSON with expected keys"
t0=$(start_timer)
if output=$(run_cli --log-level DEBUG --host "$HOST" get-details --job-id "$JOB_ID" 2>test3.err); then
	keys=$(echo "$output" | jq 'keys' 2>test3_jq.err || true)
	if [ -z "$keys" ]; then
		fail_test "$name" $(end_timer $t0) "jq failed to parse output as JSON:\n$(cat test3_jq.err)\nOutput was:\n$output"
	elif ! echo "$keys" | grep -q '"name"' || ! echo "$keys" | grep -q '"state"' || ! echo "$keys" | grep -q '"settings"'; then
		fail_test "$name" $(end_timer $t0) "Output did not contain all expected keys (name, state, settings):\n$keys"
	else
		pass_test "$name" $(end_timer $t0)
	fi
else
	fail_test "$name" $(end_timer $t0) "Command failed:\n$(cat test3.err)"
fi

# --- Test 4: Cache folder and file creation ---
name="Cache folder and file created and contain expected keys"
t0=$(start_timer)
CACHE_FILE=".cache/$HOST/$JOB_ID.json"
if [ ! -d ".cache/$HOST" ]; then
	fail_test "$name" $(end_timer $t0) "Cache directory .cache/$HOST does not exist"
elif [ -f "$CACHE_FILE" ]; then
	keys=$(jq '.job_details | keys' "$CACHE_FILE" 2>test4_jq.err || true)
	if [ -z "$keys" ]; then
		fail_test "$name" $(end_timer $t0) "jq failed to parse cache file $CACHE_FILE:\n$(cat test4_jq.err)"
	elif ! echo "$keys" | grep -q '"name"' || ! echo "$keys" | grep -q '"state"' || ! echo "$keys" | grep -q '"settings"'; then
		fail_test "$name" $(end_timer $t0) "Cache file did not contain all expected keys (name, state, settings):\n$keys"
	else
		pass_test "$name" $(end_timer $t0)
	fi
else
	fail_test "$name" $(end_timer $t0) "File $CACHE_FILE does not exist"
fi

# --- Test 5: get-details (cache hit) ---
name="get-details works on cache hit (verified via file stat)"
t0=$(start_timer)
CACHE_FILE=".cache/$HOST/$JOB_ID.json"

# Sleep 1 second to ensure that if the file is re-downloaded, the mtime will change
sleep 1

if [ "$(uname)" = "Darwin" ]; then
	mtime_before=$(stat -f %m "$CACHE_FILE")
	atime_before=$(stat -f %a "$CACHE_FILE")
else
	mtime_before=$(stat -c %Y "$CACHE_FILE")
	atime_before=$(stat -c %X "$CACHE_FILE")
fi

if output=$(run_cli --host "$HOST" get-details --job-id "$JOB_ID" 2>test5.err); then
	if [ "$(uname)" = "Darwin" ]; then
		mtime_after=$(stat -f %m "$CACHE_FILE")
		atime_after=$(stat -f %a "$CACHE_FILE")
	else
		mtime_after=$(stat -c %Y "$CACHE_FILE")
		atime_after=$(stat -c %X "$CACHE_FILE")
	fi

	# On a cache hit, the file should be read (atime might change depending on FS mount options)
	# but it MUST NOT be modified (mtime must remain identical).
	if [ "$mtime_before" != "$mtime_after" ]; then
		fail_test "$name" $(end_timer $t0) "Cache file was modified (mtime changed $mtime_before -> $mtime_after). Expected a cache hit."
	else
		pass_test "$name" $(end_timer $t0)
	fi
else
	fail_test "$name" $(end_timer $t0) "Command failed:\n$(cat test5.err)"
fi

# --- Test 6: get-log-list (cold start) ---
name="get-log-list returns multiple lines on cold start"
t0=$(start_timer)
rm -rf .cache
if output=$(run_cli --log-level DEBUG --host "$HOST" get-log-list --job-id "$JOB_ID" 2>test6.err) && [ -n "$output" ]; then
	line_count=$(echo "$output" | wc -l)
	if [ "$line_count" -ge 2 ]; then
		pass_test "$name" $(end_timer $t0)
	else
		fail_test "$name" $(end_timer $t0) "Expected multiple lines of output, got $line_count:\n$output"
	fi
else
	fail_test "$name" $(end_timer $t0) "Output was empty or command failed:\n$(cat test6.err)"
fi

# --- Test 7: Cache file contains log_files ---
name="Cache file created and contains log_files key"
t0=$(start_timer)
CACHE_FILE=".cache/$HOST/$JOB_ID.json"
if [ ! -d ".cache/$HOST" ]; then
	fail_test "$name" $(end_timer $t0) "Cache directory .cache/$HOST does not exist"
elif [ -f "$CACHE_FILE" ]; then
	log_files=$(jq '.log_files' "$CACHE_FILE" 2>test7_jq.err || true)
	if [ -z "$log_files" ] || [ "$log_files" = "null" ]; then
		fail_test "$name" $(end_timer $t0) "jq failed to find 'log_files' in $CACHE_FILE:\n$(cat test7_jq.err)"
	elif ! echo "$log_files" | jq -e 'type == "array"' >/dev/null 2>&1; then
		fail_test "$name" $(end_timer $t0) "'log_files' is not an array in $CACHE_FILE"
	else
		pass_test "$name" $(end_timer $t0)
	fi
else
	fail_test "$name" $(end_timer $t0) "File $CACHE_FILE does not exist"
fi

# --- Test 8: get-log-list (cache hit) ---
name="get-log-list works on cache hit (verified via file stat)"
t0=$(start_timer)
CACHE_FILE=".cache/$HOST/$JOB_ID.json"

# Sleep 1 second to ensure that if the file is re-downloaded, the mtime will change
sleep 1

if [ "$(uname)" = "Darwin" ]; then
	mtime_before=$(stat -f %m "$CACHE_FILE")
else
	mtime_before=$(stat -c %Y "$CACHE_FILE")
fi

if output=$(run_cli --host "$HOST" get-log-list --job-id "$JOB_ID" 2>test8.err); then
	if [ "$(uname)" = "Darwin" ]; then
		mtime_after=$(stat -f %m "$CACHE_FILE")
	else
		mtime_after=$(stat -c %Y "$CACHE_FILE")
	fi

	if [ "$mtime_before" != "$mtime_after" ]; then
		fail_test "$name" $(end_timer $t0) "Cache file was modified (mtime changed $mtime_before -> $mtime_after). Expected a cache hit."
	else
		pass_test "$name" $(end_timer $t0)
	fi
else
	fail_test "$name" $(end_timer $t0) "Command failed:\n$(cat test8.err)"
fi

# --- Test 9: Capture first log filename ---
name="Extract first filename from log list"
t0=$(start_timer)
# Get the first line containing .txt, strip leading/trailing whitespace
FIRST_FILE=$(echo "$output" | grep "\.txt" | head -n 1 | awk '{$1=$1};1')
if [ -n "$FIRST_FILE" ]; then
	pass_test "$name (File: $FIRST_FILE)" $(end_timer $t0)
else
	fail_test "$name" $(end_timer $t0) "Could not extract a filename"
	echo "Aborting remaining tests as they depend on the filename."
	exit 1
fi

# --- Test 10: get-log-list --name-pattern ---
name="get-log-list filtering with --name-pattern"
t0=$(start_timer)
# Escape special chars in the filename to use as regex
PATTERN="^$(echo "$FIRST_FILE" | sed 's/[]\/$*.^[]/\\&/g')$"
if filtered_output=$(run_cli --log-level DEBUG --host "$HOST" get-log-list --job-id "$JOB_ID" --name-pattern "$PATTERN" 2>test10.err); then
	line_count=$(echo "$filtered_output" | grep -c . || true)
	if [ "$line_count" -eq 1 ]; then
		pass_test "$name" $(end_timer $t0)
	else
		fail_test "$name" $(end_timer $t0) "Expected exactly 1 result, got $line_count:\n$filtered_output"
	fi
else
	fail_test "$name" $(end_timer $t0) "Command failed:\n$(cat test10.err)"
fi

# --- Test 11: get-log-filename (download) ---
name="get-log-filename downloads file and returns path"
t0=$(start_timer)
if dl_output=$(run_cli --log-level DEBUG --host "$HOST" get-log-filename --job-id "$JOB_ID" --filename "$FIRST_FILE" 2>test11.err); then
	# Output should be the absolute path. Read it.
	LOG_PATH=$(echo "$dl_output" | tail -n 1 | awk '{$1=$1};1')
	if [ -f "$LOG_PATH" ]; then
		pass_test "$name" $(end_timer $t0)
	else
		fail_test "$name" $(end_timer $t0) "File $LOG_PATH does not exist"
	fi
else
	fail_test "$name" $(end_timer $t0) "Command failed:\n$(cat test11.err)"
fi

# --- Test 12: Downloaded file is non-empty ---
name="Downloaded file is non-empty"
t0=$(start_timer)
if [ -s "$LOG_PATH" ]; then
	pass_test "$name" $(end_timer $t0)
else
	fail_test "$name" $(end_timer $t0) "File $LOG_PATH is empty"
fi

# --- Test 13: get-log-filename works on cache hit (verified via file stat) ---
name="get-log-filename works on cache hit (verified via file stat)"
t0=$(start_timer)

# Sleep 1 second to ensure that if the file is re-downloaded, the mtime will change
sleep 1

if [ "$(uname)" = "Darwin" ]; then
	mtime_before=$(stat -f %m "$LOG_PATH")
else
	mtime_before=$(stat -c %Y "$LOG_PATH")
fi

if dl_output_cached=$(run_cli --host "$HOST" get-log-filename --job-id "$JOB_ID" --filename "$FIRST_FILE" 2>test13.err); then
	if [ "$(uname)" = "Darwin" ]; then
		mtime_after=$(stat -f %m "$LOG_PATH")
	else
		mtime_after=$(stat -c %Y "$LOG_PATH")
	fi

	if [ "$mtime_before" != "$mtime_after" ]; then
		fail_test "$name" $(end_timer $t0) "Cache file was modified (mtime changed $mtime_before -> $mtime_after). Expected a cache hit."
	else
		pass_test "$name" $(end_timer $t0)
	fi
else
	fail_test "$name" $(end_timer $t0) "Command failed:\n$(cat test13.err)"
fi

# Store hash of original file for later comparison
ORIG_HASH=$(sha256sum "$LOG_PATH" | awk '{print $1}')

# --- Test 14: Re-download after deletion ---
name="get-log-filename re-downloads if file deleted"
t0=$(start_timer)
rm -f "$LOG_PATH"
if dl_output2=$(run_cli --log-level DEBUG --host "$HOST" get-log-filename --job-id "$JOB_ID" --filename "$FIRST_FILE" 2>test14.err); then
	if [ -f "$LOG_PATH" ]; then
		pass_test "$name" $(end_timer $t0)
	else
		fail_test "$name" $(end_timer $t0) "File $LOG_PATH was not re-created"
	fi
else
	fail_test "$name" $(end_timer $t0) "Command failed:\n$(cat test14.err)"
fi

# --- Test 15: Hash match ---
name="Re-downloaded file matches original hash"
t0=$(start_timer)
NEW_HASH=$(sha256sum "$LOG_PATH" | awk '{print $1}')
if [ "$ORIG_HASH" = "$NEW_HASH" ]; then
	pass_test "$name" $(end_timer $t0)
else
	fail_test "$name" $(end_timer $t0) "Hash mismatch:\nOriginal: $ORIG_HASH\nNew:      $NEW_HASH"
fi

# --- Test 16: get-log-filename invalid file ---
name="get-log-filename fails for non-existent file"
t0=$(start_timer)
if ! run_cli --log-level DEBUG --host "$HOST" get-log-filename --job-id "$JOB_ID" --filename "DOES_NOT_EXIST.log" 2>test16.err >/dev/null; then
	if grep -q "not found in the list of available logs" test16.err; then
		pass_test "$name" $(end_timer $t0)
	else
		fail_test "$name" $(end_timer $t0) "Did not see expected error message in logs:\n$(cat test16.err)"
	fi
else
	fail_test "$name" $(end_timer $t0) "Command unexpectedly succeeded"
fi

# --- Test 17: Full cold-start ---
name="Full cold-start (deleted .cache) downloads file"
t0=$(start_timer)
rm -rf .cache
if dl_output3=$(run_cli --log-level DEBUG --host "$HOST" get-log-filename --job-id "$JOB_ID" --filename "$FIRST_FILE" 2>test17.err); then
	if [ -f "$LOG_PATH" ]; then
		pass_test "$name" $(end_timer $t0)
	else
		fail_test "$name" $(end_timer $t0) "File $LOG_PATH was not created after wiping .cache"
	fi
else
	fail_test "$name" $(end_timer $t0) "Command failed:\n$(cat test17.err)"
fi

echo ""
echo "========================================================="
echo "Results: $PASS passed, $FAIL failed"
echo "========================================================="

# Exit with number of failures
exit $FAIL
