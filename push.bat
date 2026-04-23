@echo off
git add .
git commit -m "feat: automated db reset and cleanup"
git push origin staging --force
git push origin staging:main --force
pause
