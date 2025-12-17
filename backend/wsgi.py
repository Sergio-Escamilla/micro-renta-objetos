from app import create_app

# Puedes cambiar a ProdConfig cuando despliegues
app = create_app()

if __name__ == "__main__":
    app.run()
