df -H |  stdbuf -o0 tee -a /dev/stdout
while true; do
  echo "CPU Usage:" $((100-$(vmstat 1 2|tail -1|awk '{print $15}')))"%" |  stdbuf -o0 tee -a /dev/stdout
  echo "Memory Usage: $(free | grep Mem | awk '{print $3/$2 * 100.0 "%"}')" |  stdbuf -o0 tee -a /dev/stdout
  sleep 5
done