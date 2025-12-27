from waitress import serve
from warehouse.wsgi import application

if __name__ == '__main__':
    print("Waitress server is running on http://127.0.0.1:8000")
    serve(application, host='127.0.0.1', port='8000', threads=20, connection_limit=200)