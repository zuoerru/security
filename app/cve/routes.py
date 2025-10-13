from flask import Blueprint, render_template

cve_bp = Blueprint('cve', __name__, url_prefix='/cve')

@cve_bp.route('/')
def cve_index():
    return render_template('cve/index.html')