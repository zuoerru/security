from app import create_app, db

app = create_app()
with app.app_context():
    inspector = db.inspect(db.engine)
    print('cisa表存在' if inspector.has_table('cisa') else 'cisa表不存在')