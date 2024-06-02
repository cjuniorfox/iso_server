import os
from flask import Flask, send_file, abort, jsonify, request
import pycdlib

app = Flask(__name__)
ISO_DIR = "/isos"

def list_iso_contents(iso_name, path='/'):
    iso_path = os.path.join(ISO_DIR, iso_name + ".iso")
    if not os.path.isfile(iso_path):
        abort(404, description="ISO file not found")
    try:
        iso = pycdlib.PyCdlib()
        iso.open(iso_path)
        files = []
        path = path.replace("path:", "").upper()
        try:
            for child in iso.list_children(iso_path=os.path.join(path)):
                child_name = child.file_identifier().decode('utf-8')
                files.append({
                    'path': os.path.join('/', 'download' if child.is_file() else 'list_html', iso_name) + '/path:' + os.path.join(path, child_name.lower().replace(';1', '')),
                    'name': child_name.lower().replace(';1', '') + ('' if child.is_file() else '/')
                })
        except pycdlib.pycdlibexception.PyCdlibInvalidInput as e:
            print(str(e))
        iso.close()
        return files
    except pycdlib.pycdlibexception.PyCdlibException as e:
        abort(500, description=f"Error processing ISO file: {str(e)}")
    except Exception as e:
        abort(500, description=f"Unexpected error: {str(e)}")

@app.route('/list/<iso_name>')
def list_root_contents(iso_name):
    return jsonify(list_iso_contents(iso_name, '/'))

@app.route('/list/<iso_name>/<path:file_path>')
def list_contents(iso_name, file_path):
    return jsonify(list_iso_contents(iso_name, file_path))

@app.route('/list_html/<iso_name>/<path:file_path>')
def list_contents_in_html(iso_name, file_path):
    files = list_iso_contents(iso_name, file_path)
    folder = file_path.replace('path:', '')
    head = f'''<html><head><title>Index of {folder}</title><style>body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }} .container {{ width: 80%; margin: auto; overflow: hidden; }} header {{ background: #333; color: #fff; padding-top: 30px; min-height: 70px; border-bottom: #77aaff 3px solid; }} header a {{ color: #fff; text-decoration: none; text-transform: uppercase; font-size: 16px; }} ul {{ list-style: none; padding: 0; }} ul li {{ background: #fff; margin: 5px 0; padding: 10px; border: #ccc 1px solid; }} ul li a {{ color: #333; text-decoration: none; }} ul li a:hover {{ color: #77aaff; }} hr {{ border: 0; height: 1px; background: #ccc; margin: 20px 0; }}</style></head><body><header><div class="container"><h1>ISO Directory Listing</h1></div></header><div class="container"><h2>{iso_name}</h2><h3>Index of {folder}</h3><hr/><ul>'''
    body = ''
    for item in files:
        if folder != '/' or (folder == '/' and item['name'] not in ['../', './']):
            path = item['path']
            name = item['name']
            body += f'<li><a href="{path}">{name}</a></li>'
    bottom = '''</ul><hr /></div></body></html>'''
    return head + body + bottom

@app.route('/download/<iso_name>/<path:file_path>')
def download_file(iso_name, file_path):
    iso_path = os.path.join(ISO_DIR, iso_name + ".iso")
    if not os.path.isfile(iso_path):
        abort(404, description="ISO file not found")
    try:
        file_path = file_path.replace('path:', '').upper()
        iso = pycdlib.PyCdlib()
        iso.open(iso_path)
        extracted_path = os.path.join("/tmp", iso_name, os.path.basename(file_path))
        extracted_dir = os.path.dirname(extracted_path)
        os.makedirs(extracted_dir, exist_ok=True)
        with open(extracted_path, 'wb') as f:
            iso.get_file_from_iso_fp(f, iso_path=file_path.upper() + ";1")
        iso.close()
        return send_file(extracted_path, as_attachment=True)
    except pycdlib.pycdlibexception.PyCdlibException as e:
        abort(500, description=f"Error extracting file: {str(e)}")
    except Exception as e:
        abort(500, description=f"Unexpected error: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)