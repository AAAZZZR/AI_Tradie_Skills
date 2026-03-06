# AI_Tradie_Skills


#### step1 initialize the git in skills folder
```
cd ~/.openclaw/workspace/skills
git init
git remote add origin https://github.com/AAAZZZR/AI_Tradie_Skills.git
git pull origin main
```

#### step2  create cron workflow
```
cat > /app/sync-skills.sh << 'EOF'
#!/bin/bash
while true; do
  cd ~/.openclaw/skills
  git pull origin main
  rm -f README.md
  sleep 60
done
EOF
chmod +x /app/sync-skills.sh
nohup /app/sync-skills.sh > /app/sync-skills.log 2>&1 &
echo "Sync started, PID: $!"
```
#### step 3 Make sure it work
```cat /app/sync-skills.log```