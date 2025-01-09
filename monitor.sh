while true; do
  ps aux | grep "/app/.venv/bin/uvicorn" | grep -v "grep" | awk '{print "%CPU:"$3, "%MEM:"$4}' |  stdbuf -o0 tee -a /dev/stdout
  sleep 5
done