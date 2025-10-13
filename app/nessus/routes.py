from flask import Blueprint, render_template

nessus_bp = Blueprint('nessus', __name__, url_prefix='/nessus')

@nessus_bp.route('/')
def nessus_index():
    return render_template('nessus/index.html')