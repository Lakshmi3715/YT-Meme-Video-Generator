import os
from app import app, db
from models import Asset

def sync():
    with app.app_context():
        assets = Asset.query.all()
        deleted_count = 0
        for a in assets:
            # Asset filename stored might be like 'bg_video/filename.mp4'
            file_path = os.path.join(app.root_path, 'uploads', 'assets', a.filename)
            if not os.path.exists(file_path):
                db.session.delete(a)
                deleted_count += 1
        db.session.commit()
        print(f"Synchronized database: Removed {deleted_count} missing assets.")

if __name__ == '__main__':
    sync()
