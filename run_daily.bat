@echo off
echo ============================== >> "C:\Users\Gabriel\Documents\Syen\Ferramentas\Scrapping\Scrapping Poki\data\run_daily.log"
echo Execucao iniciada em %date% %time% >> "C:\Users\Gabriel\Documents\Syen\Ferramentas\Scrapping\Scrapping Poki\data\run_daily.log"
"C:\Users\Gabriel\AppData\Local\Programs\Python\Python313\python.exe" "C:\Users\Gabriel\Documents\Syen\Ferramentas\Scrapping\Scrapping Poki\run_daily.py" >> "C:\Users\Gabriel\Documents\Syen\Ferramentas\Scrapping\Scrapping Poki\data\run_daily.log" 2>&1
