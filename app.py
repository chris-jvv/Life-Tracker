from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///habits.db"
db = SQLAlchemy(app)


# Database initialization
with app.app_context():
    db.create_all()

# File-based task management
TASKS_DIR = 'tasks'
os.makedirs(TASKS_DIR, exist_ok=True)

DATA_FILE = 'data.json'

# Expense categories
EXPENSE_CATEGORIES = ['Rent', 'Food', 'Transportation', 'Entertainment', 'Utilities', 'Other']


# Functions for managing task JSON files
def get_tasks_file():
    return os.path.join(TASKS_DIR, "tasks.json")

def load_tasks():
    file_path = get_tasks_file()
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return []

def save_tasks(tasks):
    file_path = get_tasks_file()
    with open(file_path, 'w') as file:
        json.dump(tasks, file, default=str, indent=4)

def update_task_status(task):
    if isinstance(task['last_done'], str):
        task['last_done'] = datetime.fromisoformat(task['last_done'])
    due_date = task['last_done'] + timedelta(days=task['allocated_days'])
    if due_date < datetime.now():
        task['status'] = 'Overdue'
    elif due_date <= datetime.now() + timedelta(days=3):
        task['status'] = 'Near Due'
    else:
        task['status'] = 'On Time'

def calculate_days_left(last_done, allocated_days):
    if isinstance(last_done, str):
        last_done_date = datetime.strptime(last_done, "%Y-%m-%d")
    else:
        last_done_date = last_done
    due_date = last_done_date + timedelta(days=allocated_days)
    days_left = (due_date - datetime.now()).days
    return days_left


JSON_FILE = 'shopping_list.json'
CATEGORIES_Shopping = ['Groceries', 'Toiletries', 'Household', 'Wishlist']

def load_shopping_list():
    if not os.path.exists(JSON_FILE):
        return []
    with open(JSON_FILE, 'r') as f:
        return json.load(f)

def save_shopping_list(shopping_list):
    with open(JSON_FILE, 'w') as f:
        json.dump(shopping_list, f, indent=2)

DATA_FILE = 'workouts.json'
EXERCISES = [
    'bench press', 'push ups', 'pull ups', 'bicep curls',
    'overhead press', 'horizontal row', 'squat', 'skull crusher', 'tricep dips'
]

def read_workouts():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_workouts(workouts):
    with open(DATA_FILE, 'w') as f:
        json.dump(workouts, f, indent=2)

def get_max_weights(workouts):
    max_weights = {}
    for exercise in EXERCISES:
        entries = [w for w in workouts if w['exercise'] == exercise]
        if entries:
            if exercise in ['push ups', 'pull ups']:  # Bodyweight exercises
                # Sort by reps descending, then date descending
                sorted_entries = sorted(
                    entries,
                    key=lambda x: (-x['reps'], datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S')),
                )
            else:  # Weighted exercises
                # Sort by weight descending, then date descending
                sorted_entries = sorted(
    entries,
    key=lambda x: (-x['weight'], -x['reps'], datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S')),
                )
            max_weights[exercise] = sorted_entries[0]
        else:
            max_weights[exercise] = None
    return max_weights


def calculate_1rm(weight, reps):
    return round(weight * (1 + reps / 30), 2)

# Routes
@app.route('/')
def options():
    return render_template('options.html')

@app.route('/trending', methods=['GET'])
def trending():
    exercise = request.args.get('exercise')
    if exercise not in EXERCISES:
        return jsonify({'error': 'Invalid exercise'}), 400

    workouts = read_workouts()
    exercise_data = [w for w in workouts if w['exercise'] == exercise]
    
    # Sort by date
    exercise_data.sort(key=lambda w: datetime.strptime(w['date'], '%Y-%m-%d %H:%M:%S'))
    
    trend_data = [
        {
            'date': w['date'],
            'score': calculate_1rm(w['weight'], w['reps'])
        }
        for w in exercise_data
    ]
    
    return jsonify(trend_data)

@app.route('/workout', methods=['GET', 'POST'])
def workout_index():
    if request.method == 'POST':
        exercise = request.form['exercise']
        weight = request.form.get('weight', type=float)
        reps = request.form.get('reps', type=int)
        
        if exercise not in EXERCISES:
            return "Invalid exercise", 400
        if weight is None or reps is None:
            return "Invalid weight or reps", 400

        new_workout = {
            'exercise': exercise,
            'weight': weight,
            'reps': reps,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        workouts = read_workouts()
        workouts.append(new_workout)
        save_workouts(workouts)
        return redirect('/workout')

    workouts = read_workouts()
    max_weights = get_max_weights(workouts)
    return render_template('workout.html', 
                         exercises=EXERCISES,
                         workouts=workouts,
                         max_weights=max_weights)


@app.route('/shoppinglist')
def shop_index():
    shopping_list = load_shopping_list()
    return render_template('shoplist.html', 
                         shopping_list=shopping_list,
                         categories=CATEGORIES_Shopping)

@app.route('/add', methods=['POST'])
def add_item():
    shopping_list = load_shopping_list()
    new_item = {
        'id': len(shopping_list) + 1,
        'name': request.form['name'],
        'category': request.form['category'],
        'quantity': request.form.get('quantity', 1)
    }
    shopping_list.append(new_item)
    save_shopping_list(shopping_list)
    return redirect(url_for('shop_index'))

@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    shopping_list = load_shopping_list()
    shopping_list = [item for item in shopping_list if item['id'] != item_id]
    save_shopping_list(shopping_list)
    return redirect(url_for('shop_index'))


@app.route('/tasks')
def tasks_index():
    tasks = load_tasks()
    for task in tasks:
        update_task_status(task)
    save_tasks(tasks)
    return render_template('tasks.html', tasks=tasks, calculate_days_left=calculate_days_left)

@app.route('/add_task', methods=['POST'])
def add_task():
    tasks = load_tasks()
    task_name = request.form['task_name']
    allocated_days = int(request.form['allocated_days'])

    if 'custom_last_done' in request.form and request.form['custom_last_done'] == 'on':
        custom_last_done_date = request.form['custom_last_done_date']
        last_done = datetime.strptime(custom_last_done_date, '%Y-%m-%d').isoformat()
    else:
        last_done = datetime.now().isoformat()

    new_task = {"id": len(tasks) + 1, "name": task_name, "last_done": last_done, "allocated_days": allocated_days}
    tasks.append(new_task)
    save_tasks(tasks)
    return redirect(url_for('tasks_index'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    tasks = load_tasks()
    task = next((task for task in tasks if task['id'] == task_id), None)
    if task:
        task['last_done'] = datetime.now().isoformat()
        update_task_status(task)
    save_tasks(tasks)
    return redirect(url_for('tasks_index'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    tasks = load_tasks()
    tasks = [task for task in tasks if task['id'] != task_id]
    save_tasks(tasks)
    return redirect(url_for('tasks_index'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
