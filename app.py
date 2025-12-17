from hospital_management.application import create_app, setup_database

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Setup database (create tables + admin user)
    setup_database(app)
    
    # Run the application
    app.run(debug=True)