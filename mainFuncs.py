import traceback
import datetime as dt

def errorLogger(error):
    errorMessage = str(traceback.format_exc())
    with open("errorLog.txt", "a") as f:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{'*'*10}Logged on {now}{'*'*10}\n{errorMessage}\n")
    return errorMessage