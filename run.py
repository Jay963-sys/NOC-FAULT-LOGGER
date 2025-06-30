from app import create_app

print("Attempting to import create_app...")
app = create_app()
print("Starting Flask app...")
if __name__ == '__main__':
    app.run(debug=True)