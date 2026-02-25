from database import init_db, create_habit, get_habits

init_db()

create_habit("Read 10 pages", "21:00")

habits = get_habits()

for habit in habits:
    print(dict(habit))