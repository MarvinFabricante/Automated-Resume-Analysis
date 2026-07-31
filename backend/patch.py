import sys

with open("app/services/google_calendar_service.py", "r") as f:
    content = f.read()

content = content.replace("print('KWARGS:', kwargs)\n        created = service.events().insert(**kwargs).execute()", "created = service.events().insert(**kwargs).execute()")

with open("app/services/google_calendar_service.py", "w") as f:
    f.write(content)
