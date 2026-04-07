@echo off
cd /d "c:\Users\Abhimanyu Vishwakarm\OneDrive\Documents\GitHub\trading-bot"
echo Checking git status...
git status
echo.
echo Adding all files...
git add .
echo.
echo Committing changes...
git commit -m "Complete minimal trading bot with backtest and double-click startup"
echo.
echo Setting remote origin...
git remote add origin https://github.com/AxeDude7/trading-bot.git 2>nul
echo.
echo Pushing to GitHub...
git push -u origin main
echo.
echo Done! Project committed and pushed to GitHub.
pause