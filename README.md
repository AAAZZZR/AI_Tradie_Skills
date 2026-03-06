# AI_Tradie_Skills

To 
#### step1
cd ~/.openclaw/workspace/skills
git init
git remote add origin https://github.com/AAAZZZR/AI_Tradie_Skills.git
git pull origin main

#### step2
cat > /app/sync-skills.sh << 'EOF'
#!/bin/bash
while true; do
  cd ~/.openclaw/workspace/skills
  git pull origin main
  rm -f README.md
  sleep 60
done
EOF
chmod +x /app/sync-skills.sh
nohup /app/sync-skills.sh > /app/sync-skills.log 2>&1 &
echo "Sync started, PID: $!"

cat /app/sync-skills.log