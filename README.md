# To modify an instrument driver:
1) Modify the driver in src/instruments/<Driver_Name>, ensuring functions in src/instruments/InstrumentTemplate.py are implemented
2) Modify the driver in src/instrumentsQt/<Driver_Name>Qt, to allow config updates on the FRONT PANEL and general use on the SETTINGS TAB interfaces
Some functions use async functionality to prevent blocking calls. Use await, asyncio.ensure_future,
and similar

# To modify the program:
1) Update assign_instruments() in either src/Controller.py or src/ControllerQt.py to reflect changes to instruments used and their assigned port
2) Update src/Controller.py program_generate_tasks() to generate sweep parameters based on controller config
3) Update src/Controller.py program_execute_task() to obtain desired results per individual task
4) Update src/ControllerQt.py to allow controller config setting

Changing the database specified in src/Controller.py __init__() is suggested if any significant changes to config setup are made