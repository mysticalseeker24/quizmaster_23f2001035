from app import app, db, Score

with app.app_context():
    # Check if the score already exists
    existing_score = Score.query.filter_by(user_id=1, quiz_id=1).first()
    
    if not existing_score:
        new_score = Score(user_id=1, quiz_id=1, score=1, timestamp="2025-03-23 15:00:00")
        db.session.add(new_score)
        db.session.commit()
        print("Test score added successfully.")
    else:
        print("Score already exists. Not adding again.")