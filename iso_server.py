import os
import subprocess
import logging
from flask import Flask, send_file, abort, jsonify, Response, redirect

app = Flask(__name__)

ISO_DIR = os.environ.get('ISO_DIR', '/isos')
CONTEXT = os.environ.get('CONTEXT', '/')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def to_dict(method, name, kind, iso_name, full_path=''):
    if full_path:
        path = os.path.join(CONTEXT, method, iso_name) + '/' + full_path.lstrip('/')
    else:
        path = os.path.join(CONTEXT, method, iso_name)

    # Add download link for ISO files
    download_link = os.path.join(CONTEXT, 'download', iso_name + '.iso') if kind == 'ISO' else None

    return {
        'path': path,
        'name': name,
        'kind': kind,
        'download_link': download_link
    }

def to_html(iso_name, files, file_path):
    folder = file_path.replace('path:', '')
    head = (
        f'''<html><head><title>Index of {folder}</title><style>'''
        '''body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }'''
        '''.container { width: 80%; margin: auto; overflow: hidden; }'''
        '''header { background: #333; color: #fff; padding-top: 30px; min-height: 70px; border-bottom: #77aaff 3px solid; }'''
        '''header a { color: #fff; text-decoration: none; text-transform: uppercase; font-size: 16px; }'''
        '''ul { list-style: none; padding: 0; }'''
        '''ul li { background: #fff; margin: 5px 0; padding: 10px; border: #ccc 1px solid; }'''
        '''ul li a { color: #333; text-decoration: none; }'''
        '''ul li a:hover { color: #77aaff; }'''
        '''hr { border: 0; height: 1px; background: #ccc; margin: 20px 0; }'''
        '''/* Styling for the download link */'''
        '''.download-link { margin-left: 10px;  text-decoration: none; }'''
        '''</style></head>'''
    )
    head += '''<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">'''
    head += f'''<body><header><div class="container"><h1>ISO Directory Listing</h1></div></header><div class="container"><h2>{iso_name}</h2><h3>Index of {folder}</h3><hr/><ul>'''
    
    body = ''
    for item in files:
        if folder != '/' or (folder == '/' and item['name'] not in ['../', './']):
            path = item['path']
            name = item['name']
            kind = item['kind']
            fa_icon = 'fa-folder' if kind == 'DIR' else 'fa-compact-disc'
            fa_icon = 'fa-file' if kind == 'FILE' else fa_icon
            fa_icon = 'fa-turn-up' if kind == 'BACK' else fa_icon
            
            # Add download link for ISO files with a download icon inside a button
            download_link = item.get('download_link')
            download_html = (
                f' <a href="{download_link}" class="download-link" aria-label="Download {name}">'
                f'<i class="fas fa-download"></i></a>'
            ) if download_link else ''
            
            body += f'<li><a href="{path}"><i class="fas {fa_icon} icon"></i> {name}</a>{download_html}</li>'
    
    bottom = '''</ul><hr /></div></body></html>'''
    return head + body + bottom

def list_isos_as_dict():
    files = []
    try:
        for f in os.listdir(ISO_DIR):
            if f.endswith('.iso'):
                iso_name = f.removesuffix('.iso')
                iso_dict = to_dict('html', f, 'ISO', iso_name, '')
                logger.info(f"ISO File: {f}, ISO Name: {iso_name}, Dict: {iso_dict}")
                files.append(iso_dict)
        
        return files
    except Exception as e:
        logger.error(f"Error listing ISO files: {str(e)}")
        abort(500, description=f"Error listing ISO files: {str(e)}")

def list_iso_contents_dict(iso_name, path='/'):
    iso_path = os.path.join(ISO_DIR, iso_name + ".iso")
    if not os.path.isfile(iso_path):
        abort(404, description="ISO file not found")
    try:
        files = []
        output = run_7z_command(iso_path)
        # No need to replace 'path:' anymore
        # path = path.replace("path:", "")
        files_buffer = False
        add_up_directory_link(files, iso_name, path)
        for line in output:
            if line.startswith('------'):
                files_buffer = True
                continue
            if files_buffer:
                process_line(line, files, iso_name, path)
        files = sorted(files, key=lambda x: x['kind'])
        return files
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running 7z command: {str(e)}")
        abort(500, description=f"Error running 7z command: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        abort(500, description=f"Unexpected error: {str(e)}")

def run_7z_command(iso_path):
    cmd = ['7z', 'l', iso_path]
    iso = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return iso.stdout.split('\n')

def add_up_directory_link(files, iso_name, path):
    if path not in ['', '/']:
        iso_fs_path = os.path.join(path, '..')
        files.append(to_dict('html', 'Up one Directory', 'BACK', iso_name, iso_fs_path))
    else:
        files.append(to_dict('html', 'ISO Directory Listing', 'BACK', ''))

def add_files(files, iso_name, path_look, dir_name, iso_fs_path, name):
    if dir_name == path_look or dir_name == path_look.rstrip('/'):
        files.append(to_dict('download', name, 'FILE', iso_name, iso_fs_path))

def process_line(line, files, iso_name, path):
    values = line.split()
    if len(values) == 6:
        iso_fs_path = os.path.join('/', values[5])
        name = os.path.basename(values[5])
        dir_name = os.path.dirname(iso_fs_path)
        path_look = os.path.join('/', path)
        add_dirs(files, path_look, dir_name, iso_name)
        add_files(files, iso_name, path_look, dir_name, iso_fs_path, name)

def add_dirs(files, path_look, dir_name, iso_name):
    len_look_dir = len(path_look.split('/')) - 1
    if dir_name.startswith(path_look):
        split_dir = dir_name.split('/')
        if len(split_dir) > len_look_dir:
            subdir = split_dir[len_look_dir]
            if subdir and subdir != files[-1]['name']:
                iso_fs_path = os.path.join(path_look, subdir + '/')
                files.append(to_dict('html', subdir, 'DIR', iso_name, iso_fs_path))

@app.route(f'{CONTEXT}json/<iso_name>')
def list_root_contents(iso_name):
    return jsonify(list_iso_contents_dict(iso_name, '/'))

@app.route(f'{CONTEXT}json/<iso_name>/<path:file_path>')
def list_contents(iso_name, file_path):
    return jsonify(list_iso_contents_dict(iso_name, file_path))

@app.route(f'{CONTEXT}html/<iso_name>/<path:file_path>')
def list_contents_in_html(iso_name, file_path):
    files = list_iso_contents_dict(iso_name, file_path)
    return to_html(iso_name, files, file_path)

@app.route(f'{CONTEXT}html/<iso_name>/')
def list_root_contents_in_html(iso_name):
    return list_contents_in_html(iso_name, '/')

@app.route(f'{CONTEXT}download/<iso_name>/<path:file_path>')
def download_file(iso_name, file_path):
    iso_path = os.path.join(ISO_DIR, iso_name + ".iso")
    if not os.path.isfile(iso_path):
        abort(404, description="ISO file not found")
    try:
        file_path = file_path.replace('path:', '').lstrip('/')
        cmd = ['7z', 'e', '-so', iso_path, file_path]
        result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def generate():
            chunk_size = 8192
            try:
                for chunk in iter(lambda: result.stdout.read(chunk_size), b''):
                    yield chunk
                result.stdout.close()
                result.wait()
                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
            except Exception as e:
                logger.error(f"Error streaming file: {str(e)}")
                abort(500, description=f"Error streaming file: {str(e)}")

        return Response(generate(), content_type='application/octet-stream')
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        abort(500, description=f"Unexpected error: {str(e)}")

@app.route(f'{CONTEXT}download/<file_name>')
def download_iso(file_name):
    iso_path = os.path.join(ISO_DIR, file_name )
    if not os.path.isfile(iso_path):
        abort(404, description="ISO file not found")
    return send_file(iso_path, as_attachment=True)

@app.route(f'{CONTEXT}json/')
def list_isos():
    return jsonify(list_isos_as_dict())

@app.route(f'{CONTEXT}html/')
def list_isos_as_html():
    return to_html('root', list_isos_as_dict(), 'ISOS')

@app.route(f'{CONTEXT}')
def redirect_to_html():
    return redirect(f'{CONTEXT}html/')

if __name__ == '__main__':
    logger.info(f' * ISO Directory: "{ISO_DIR}"')
    logger.info(f' * Context Path: "{CONTEXT}"')
    app.run(host='0.0.0.0', port=8000)