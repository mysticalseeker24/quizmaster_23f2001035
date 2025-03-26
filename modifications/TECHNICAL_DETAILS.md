# Quiz Management System: Technical Modifications Document

## System Architecture Overview

The Quiz Management System is built using Flask with SQLAlchemy for database interactions. The system follows a Model-View-Controller (MVC) architecture:

- **Models**: Defined in `app.py` (User, Subject, Chapter, Quiz, Question, Score, UserAnswer)
- **Views**: HTML templates in the `templates/` directory
- **Controllers**: Flask routes defined in `app.py`

## Database Schema

Key models involved in our modifications:

```
+-------------+     +-------------+     +-------------+
|    User     |     |    Quiz     |     |  Question   |
+-------------+     +-------------+     +-------------+
| id          |     | id          |     | id          |
| email       |     | name        |     | quiz_id     |
| password    |     | chapter_id  |     | question_text|
| full_name   |     | duration    |     | option1-4   |
| qualification|     +-------------+     | correct_opt |
| dob         |           |             +-------------+
+-------------+           |                   |
      |                   |                   |
      |                   |                   |
      v                   v                   v
+-------------+     +-------------+     +-------------+
|    Score    |     | UserAnswer  |     |   Other     |
+-------------+     +-------------+     |   Models    |
| id          |     | id          |     +-------------+
| user_id     |     | quiz_id     |
| quiz_id     |     | question_id |
| score       |     | selected_opt|
| timestamp   |     +-------------+
+-------------+
```

## 1. Detailed Analysis of Original Issues

### Quiz Flow Issues

In the original implementation, the quiz completion flow had three critical problems:

1. The `start_quiz` function redirected directly to the scores page without calculating the final score:

```python
# Original problematic code from start_quiz function
if q_no == total_questions:
    flash("Answer submitted successfully!", "success")
    return redirect(url_for('scores', quiz_id=quiz_id))
```

2. The `UserAnswer` entries were being saved correctly, but never processed to calculate a score.

3. The `submit_quiz` function was defined but never actually called in the standard quiz flow.

### Score Calculation and Storage Issues

1. The `Score` model had a unique constraint that prevented multiple attempts of the same quiz:

```python
# Original Score model with constraint
class Score(db.Model):
    # ... fields ...
    __table_args__ = (db.UniqueConstraint('user_id', 'quiz_id', name='unique_user_quiz'),)
```

2. The timestamp field existed but wasn't consistently populated, making it difficult to track when scores were achieved.

## 2. Detailed Code Modifications

### Session Enhancement

Added user's full name to session to make it available in templates:

```python
# Modified userlogin function
@app.route('/userlogin', methods=['GET', 'POST'])
def userlogin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['fullname'] = user.full_name  # Added this line
            return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid credentials. Please try again.", "danger")
    
    return render_template('login.html')
```

### Score Model Enhancement

Removed the unique constraint to allow multiple attempts per quiz:

```python
# Before
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.String(20))
    user = db.relationship('User', backref='scores', lazy=True)
    quiz = db.relationship('Quiz', backref='scores', lazy=True)
    __table_args__ = (db.UniqueConstraint('user_id', 'quiz_id', name='unique_user_quiz'),)

# After - Removed constraint
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.String(20))
    user = db.relationship('User', backref='scores', lazy=True)
    quiz = db.relationship('Quiz', backref='scores', lazy=True)
```

### Quiz Completion Flow Correction

Modified the `start_quiz` function to calculate scores on quiz completion:

```python
@app.route('/start_quiz/<int:quiz_id>/<int:q_no>', methods=['GET', 'POST'])
def start_quiz(quiz_id, q_no):
    total_questions = Question.query.filter_by(quiz_id=quiz_id).count()
    
    # If no more questions, go to summary
    if q_no > total_questions:
        # Calculate and save score before redirecting
        calculate_score(quiz_id)
        return redirect(url_for('scores'))

    # ... rest of the function ...

    if request.method == 'POST':
        # ... processing answers ...

        if q_no == total_questions:
            # Last question - calculate score and save it
            calculate_score(quiz_id)
            flash("Quiz completed successfully! Check your score below.", "success")
            return redirect(url_for('scores'))
        else:
            # More questions to go
            return redirect(url_for('start_quiz', quiz_id=quiz_id, q_no=q_no + 1))

    # ... rest of the function ...
```

### Score Calculation Implementation

Implemented a dedicated function to calculate and save scores:

```python
# Helper function to calculate and save score
def calculate_score(quiz_id):
    if 'user_id' not in session:
        return
        
    user_id = session['user_id']
    
    # Get all questions for this quiz
    all_questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    # Get answers for this quiz
    user_answers = UserAnswer.query.filter(UserAnswer.quiz_id == quiz_id).all()
    
    # Calculate score
    correct_answers = 0
    for question in all_questions:
        for answer in user_answers:
            if answer.question_id == question.id:
                # Check if the answer matches correct option
                question_option_field = f"option{question.correct_option}"
                correct_option_text = getattr(question, question_option_field)
                if answer.selected_option == correct_option_text:
                    correct_answers += 1
                break
    
    # Add timestamp
    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Always create a new score record for each quiz attempt
    score = Score(user_id=user_id, quiz_id=quiz_id, score=correct_answers, timestamp=current_time)
    db.session.add(score)
    db.session.commit()
    
    return correct_answers
```

### Scores Page Enhancement

Improved the scores function to provide better data for the template:

```python
@app.route('/scores')
def scores():
    if 'user_id' not in session:
        return redirect(url_for('userlogin')) 

    user_id = session['user_id']
    
    # Get user scores with detailed information about each quiz
    # Order by timestamp descending (newest first)
    user_scores = db.session.query(Score, Quiz)\
        .join(Quiz)\
        .filter(Score.user_id == user_id)\
        .order_by(Score.timestamp.desc())\
        .all()
    
    # Prepare the data for the template
    score_data = []
    for score, quiz in user_scores:
        # Get number of questions in the quiz
        question_count = Question.query.filter_by(quiz_id=quiz.id).count()
        
        # Calculate percentage
        percentage = (score.score / question_count * 100) if question_count > 0 else 0
        
        score_data.append({
            'score': score,
            'quiz': quiz,
            'question_count': question_count,
            'percentage': round(percentage, 2)
        })

    return render_template('scores.html', scores=score_data)
```

### Score Reset Functionality

Added the ability to reset all scores:

```python
@app.route('/reset_scores', methods=['POST'])
def reset_scores():
    if 'user_id' not in session:
        return redirect(url_for('userlogin'))
    
    user_id = session['user_id']
    
    # Delete all scores for this user
    Score.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    
    flash("All your quiz scores have been reset successfully!", "success")
    return redirect(url_for('scores'))
```

### Updated Scores Template

Enhanced the scores.html template:

```html
<!-- Reset Scores Button -->
<div class="d-flex justify-content-end mb-3">
    <form action="{{ url_for('reset_scores') }}" method="POST" onsubmit="return confirm('Are you sure you want to reset all your quiz scores? This action cannot be undone.')">
        <button type="submit" class="btn btn-danger">Reset All Scores</button>
    </form>
</div>

<table class="table table-bordered">
    <thead class="table-dark">
        <tr>
            <th>Quiz ID</th>
            <th>Quiz Name</th>
            <th>Score</th>
            <th>Percentage</th>
            <th>Date</th>
        </tr>
    </thead>
    <tbody>
        {% for data in scores %}
        <tr>
            <td>{{ data.quiz.id }}</td>
            <td>{{ data.quiz.name }}</td>
            <td>{{ data.score.score }} out of {{ data.question_count }}</td>
            <td>{{ data.percentage }}%</td>
            <td>{{ data.score.timestamp }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

## 3. Performance Considerations

- **Query Optimization**: The modified scores function uses a join to efficiently retrieve quiz details along with scores
- **Memory Utilization**: By calculating percentages in the controller rather than the template, we reduce template complexity
- **Database Access**: The performance impact of storing multiple score records per quiz is minimal, as the total number of records remains manageable

## 4. Security Considerations

- **Session Security**: We maintain proper session validation in all routes
- **User Data Isolation**: All queries filter by user_id to ensure users can only see/modify their own data
- **Confirmation Dialogs**: Added to prevent accidental data deletion

## 5. Testing Strategy

### Unit Testing

The following functions should be tested individually:

1. `calculate_score`: Verify correct score calculation for various answer patterns
2. `reset_scores`: Confirm proper deletion of user's scores only

### Integration Testing

Test the complete flow:

1. Login → Take Quiz → View Scores → Take Same Quiz Again → Verify Multiple Scores
2. Reset Scores → Verify Deletion

### Test Cases

| Test ID | Description | Expected Result |
|---------|-------------|------------------|
| TC01 | Complete Quiz 1 | Score displayed with timestamp |
| TC02 | Complete Quiz 1 again | New score record added, ordered by newest first |
| TC03 | Complete Quiz 2 | Scores for both quizzes visible |
| TC04 | Reset Scores | All scores removed, empty state message shown |

## 6. Deployment Considerations

### Database Migration

The removal of the unique constraint on the Score table is a non-destructive change that doesn't require a formal migration with SQLite. However, when deploying to production systems, consider:

```python
# Migration script if using Flask-Migrate
# migrations/versions/xxxx_remove_unique_constraint.py

def upgrade():
    op.drop_constraint('unique_user_quiz', 'score', type_='unique')

def downgrade():
    op.create_unique_constraint('unique_user_quiz', 'score', ['user_id', 'quiz_id'])
```

## 7. Future Enhancement Suggestions

### Individual Score Deletion

Add route for deleting individual scores:

```python
@app.route('/delete_score/<int:score_id>', methods=['POST'])
def delete_score(score_id):
    if 'user_id' not in session:
        return redirect(url_for('userlogin'))
    
    user_id = session['user_id']
    score = Score.query.get(score_id)
    
    # Ensure score belongs to current user
    if score and score.user_id == user_id:
        db.session.delete(score)
        db.session.commit()
        flash("Score deleted successfully!", "success")
    
    return redirect(url_for('scores'))
```

### Quiz Attempt Details

Implement a detailed view of quiz attempts:

```python
@app.route('/score_details/<int:score_id>')
def score_details(score_id):
    # Retrieve the score and all associated user answers
    # Show which questions were answered correctly/incorrectly
```

### User Performance Analytics

Add charts to visualize performance over time:

```python
@app.route('/performance_trends')
def performance_trends():
    # Query scores with timestamps
    # Generate charts showing improvement over time
```

## 8. External API Integration

Potential integrations to enhance the quiz system:

- **Export to PDF**: Generate PDF reports of score history
- **Share on Social Media**: Allow sharing of quiz achievements
- **Learning Management System (LMS) Integration**: Push scores to external LMS platforms
