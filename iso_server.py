import os
from flask import Flask, send_file, abort, jsonify
import pycdlib
import subprocess

app = Flask(__name__)

ISO_DIR = "/home/junior/Downloads/isos"

@app.route('/list/<iso_name>')
def list_iso_contents(iso_name):
    iso_path = os.path.join(ISO_DIR, iso_name + ".iso")
    
    if not os.path.isfile(iso_path):
        abort(404, description="ISO file not found")

    try:
        iso = pycdlib.PyCdlib()
        iso.open(iso_path)

        files = []

        def list_files(path):
            lpath = path.lower()
            try:
                for child in iso.list_children(lpath):
                    if child.is_file():
                        files.append(os.path.join(path, child.file_identifier()))
                    elif child.is_dir():
                        list_files(os.path.join(path, child.file_identifier()))
            except pycdlib.pycdlibexception.PyCdlibInvalidInput:
                pass

        list_files("/")
        iso.close()
        return jsonify(files)
    except Exception as e:
        abort(500, description=f"Error processing ISO file: {str(e)}")

@app.route('/download/<iso_name>/<path:file_path>')
def download_file(iso_name, file_path):
    iso_path = os.path.join(ISO_DIR, iso_name + ".iso")
    
    if not os.path.isfile(iso_path):
        abort(404, description="ISO file not found")

    try:
        iso = pycdlib.PyCdlib()
        iso.open(iso_path)

        extracted_path = f"/tmp/{iso_name}/{file_path}"
        extracted_dir = os.path.dirname(extracted_path)

        os.makedirs(extracted_dir, exist_ok=True)
        
        with open(extracted_path, 'wb') as f:
            iso.get_file_from_iso_fp(f, iso_path=file_path)
            
        iso.close()
        return send_file(extracted_path, as_attachment=True)
    except Exception as e:
        abort(500, description=f"Error extracting file: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
