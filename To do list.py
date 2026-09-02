tasks = []

def add_task():
    task = input("Enter a new task: ")
    tasks.append({"task": task, "completed": False})
    print("Task added successfully!")

def view_tasks():
    if not tasks:
        print("\nNo tasks available.")
        return
    print("\nTO-DO LIST")
    for i, task in enumerate(tasks, start=1):
        status = "done" if task["completed"] else "    "
        print(f"{i}. {task['task']} [{status}]")

def complete_task():
    view_tasks()
    if tasks:
        try:
            num = int(input("Enter task number to complete: "))
            tasks[num - 1]["completed"] = True
            print("Task marked as completed!")
        except:
            print("Invalid task number!")

def delete_task():
    view_tasks()
    if tasks:
        try:
            num = int(input("Enter task number to delete: "))
            removed = tasks.pop(num - 1)
            print(f"'{removed['task']}' deleted successfully!")
        except:
            print("Invalid task number!")

while True:
    print("\n=== TO-DO LIST MENU ===")
    print("1. Add Task")
    print("2. View Tasks")
    print("3. Complete Task")
    print("4. Delete Task")
    print("5. Exit")
    choice = input("Enter your choice: ")
    if choice == "1":
        add_task()
    elif choice == "2":
        view_tasks()
    elif choice == "3":
        complete_task()
    elif choice == "4":
        delete_task()
    elif choice == "5":
        print("Thank you for using the To-Do List Application!")
        break
    else:
        print("Invalid choice! Please try again.")