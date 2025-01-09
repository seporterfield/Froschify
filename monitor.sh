echo "Storage:" $(df -H $(pwd) | tail -n 1) |  stdbuf -o0 cat >> /dev/stdout
while true; do
  echo "CPU:" $((100-$(vmstat 1 2|tail -1|awk '{print $15}')))"%," "Mem: $(free | grep Mem | awk '{print $3/$2 * 100.0 "%"}')" |  stdbuf -o0 cat >> /dev/stdout
  sleep 5
done