starttime=$(date +%s)
echo 'Output of df -H $(pwd):' $(df -H $(pwd) | tail -n 1) | stdbuf -o0 cat >>/dev/stdout
while true; do
  elapsed=$(($(date +%s) - $starttime))
  memusg=$(free | grep Mem | awk '{print $3/$2 * 100.0 "%"}' | sed 's/%//' | cut -d"." -f1)
  cpuusg=$((100 - $(vmstat 1 2 | tail -1 | awk '{print $15}')))
  uptime=$(printf "%02d:%02d:%02d" $(($elapsed / 3600)) $(($elapsed / 60 % 60)) $(($elapsed % 60)))
  printf "Uptime %s CPU%% %02d Mem%% %02d\n" $uptime $cpuusg $memusg | stdbuf -o0 cat >>/dev/stdout
  sleep 5
done
