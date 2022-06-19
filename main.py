from flask import Flask

from data.db_session import global_init
from data.items_api import blueprint, my_make_response

app = Flask(__name__)
app.config['SECRET_KEY'] = 'backend_school_secret_key'


@app.errorhandler(404)
def not_found(error):
    return my_make_response(404, 'Page not found')


if __name__ == '__main__':
    global_init('db/blogs.db')

    app.register_blueprint(blueprint)
    app.run(host='0.0.0.0', port=80)
