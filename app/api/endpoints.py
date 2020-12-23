import datetime
import io
import os
from pathlib import Path

import flask

from app.api import api


def fix_name(base_path, file_name, restore: bool):
    if restore:
        return f'{base_path}:{file_name}'.replace(os.sep, ':')
    return f'{file_name}'.replace(':', os.sep)


@api.route('/config/<name>', methods=['GET'])
def get_config(name: str):
    """
    Reads the file with the corresponding name that was passed.

    :param name: Configuration file name
    :type name: str

    :return: Rendered HTML document with content of the configuration file.
    :rtype: str
    """
    nginx_path = flask.current_app.config['NGINX_PATH']

    with io.open(os.path.join(nginx_path, name), 'r') as f:
        _file = f.read()

    return flask.render_template('config.html', name=name, file=_file), 200


@api.route('/config/<name>', methods=['POST'])
def post_config(name: str):
    """
    Accepts the customized configuration and saves it in the configuration file with the supplied name.

    :param name: Configuration file name
    :type name: str

    :return:
    :rtype: werkzeug.wrappers.Response
    """
    content = flask.request.get_json()
    nginx_path = flask.current_app.config['NGINX_PATH']

    with io.open(os.path.join(nginx_path, name), 'w') as f:
        f.write(content['file'])

    return flask.make_response({'success': True}), 200


@api.route('/domains', methods=['GET'])
def get_domains():
    """
    Reads all files from the configuration file directory and checks the state of the site configuration.

    :return: Rendered HTML document with the domains
    :rtype: str
    """
    base_config_path = flask.current_app.config['CONFIG_PATH']
    sites_available = []
    sites_enabled = []

    def deep_path(config_path):
        for root, dirs, files in os.walk(config_path):
            for file in files:
                my_file = Path(f"{config_path}{os.sep}{file}")
                if not my_file.exists():
                    continue
                domain, state = file.rsplit('.', 1)
                if state == 'conf':
                    time = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(config_path, file)))

                    sites_available.append({
                        'name': fix_name(config_path.replace(base_config_path, ''), domain, True),
                        'time': time
                    })
                    sites_enabled.append(fix_name(config_path.replace(base_config_path, ''), domain, True))
                elif state == 'disabled':
                    time = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(config_path, file)))

                    sites_available.append({
                        'name': fix_name(config_path.replace(base_config_path, ''), domain, True).rsplit('.', 1)[0],
                        'time': time
                    })
            for dir in dirs:
                deep_path(f'{config_path}{os.sep}{dir}')

    deep_path(base_config_path)
    # sort sites by name
    sites_available = sorted(sites_available, key=lambda _: _['name'])
    return flask.render_template('domains.html', sites_available=sites_available, sites_enabled=sites_enabled), 200


@api.route('/domain/<name>', methods=['GET'])
def get_domain(name: str):
    """
    Takes the name of the domain configuration file and
    returns a rendered HTML with the current configuration of the domain.

    :param name: The domain name that corresponds to the name of the file.
    :type name: str

    :return: Rendered HTML document with the domain
    :rtype: str
    """
    config_path = flask.current_app.config['CONFIG_PATH']
    _file = ''
    enabled = True
    ret_name = name
    name = fix_name(base_path=None, file_name=name, restore=False)
    if Path(f'{config_path}{os.sep}{name}.conf').exists():
        name = f'{name}.conf'
    else:
        name = f'{name}.disabled'
    domain, state = name.rsplit('.', 1)
    if state == 'disabled':
        enabled = False

    with io.open(os.path.join(f'{config_path}{os.sep}{name}'), 'r') as f:
        _file = f.read()

    fix_name(base_path=None, file_name=name, restore=False)
    return flask.render_template('domain.html', name=ret_name, file=_file, enabled=enabled), 200


@api.route('/domain/<name>', methods=['POST'])
def post_domain(name: str):
    """
    Creates the configuration file of the domain.

    :param name: The domain name that corresponds to the name of the file.
    :type name: str

    :return: Returns a status about the success or failure of the action.
    """
    config_path = flask.current_app.config['CONFIG_PATH']
    new_domain = flask.render_template('new_domain.j2', name=name)
    name = fix_name(base_path=None, file_name=name, restore=False)
    name = name + '.disabled'

    try:
        with io.open(os.path.join(config_path, name), 'w') as f:
            f.write(new_domain)

        response = flask.jsonify({'success': True}), 201
    except Exception as ex:
        response = flask.jsonify({'success': False, 'error_msg': ex}), 500

    return response


@api.route('/domain/<name>', methods=['DELETE'])
def delete_domain(name: str):
    """
    Deletes the configuration file of the corresponding domain.

    :param name: The domain name that corresponds to the name of the file.
    :type name: str

    :return: Returns a status about the success or failure of the action.
    """
    config_path = flask.current_app.config['CONFIG_PATH']
    removed = False
    name = fix_name(base_path=None, file_name=name, restore=False)

    for _ in os.listdir(config_path):

        if os.path.isfile(os.path.join(config_path, _)):
            if _.startswith(name):
                os.remove(os.path.join(config_path, _))
                removed = not os.path.exists(os.path.join(config_path, _))
                break

    if removed:
        return flask.jsonify({'success': True}), 200
    else:
        return flask.jsonify({'success': False}), 400


@api.route('/domain/<name>', methods=['PUT'])
def put_domain(name: str):
    """
    Updates the configuration file with the corresponding domain name.

    :param name: The domain name that corresponds to the name of the file.
    :type name: str

    :return: Returns a status about the success or failure of the action.
    """
    content = flask.request.get_json()
    config_path = flask.current_app.config['CONFIG_PATH']
    name = fix_name(base_path=None, file_name=name, restore=False)

    if Path(f'{config_path}{os.sep}{name}.conf').exists():
        name = f'{name}.conf'
    else:
        name = f'{name}.disabled'

    with io.open(os.path.join(f'{config_path}{os.sep}{name}'), 'w') as f:
        f.write(content['file'])

    return flask.make_response({'success': True}), 200


@api.route('/domain/<name>/enable', methods=['POST'])
def enable_domain(name: str):
    """
    Activates the domain in Nginx so that the configuration is applied.

    :param name: The domain name that corresponds to the name of the file.
    :type name: str

    :return: Returns a status about the success or failure of the action.
    """
    content = flask.request.get_json()
    config_path = flask.current_app.config['CONFIG_PATH']
    name = fix_name(base_path=None, file_name=name, restore=False)
    if Path(f'{config_path}{os.sep}{name}.conf').exists():
        name = f'{name}.conf'
    else:
        name = f'{name}.disabled'

    if content['enable']:
        os.rename(f'{config_path}{os.sep}{name}', f'{config_path}{os.sep}{name}'.replace(".conf", '')
                  .replace('.disabled', '') + '.conf')
    else:
        print(f'{config_path}{os.sep}{name}')
        os.rename(f'{config_path}{os.sep}{name}', f'{config_path}{os.sep}{name}'.replace(".conf", '')
                  .replace('.disabled', '') + '.disabled')

    return flask.make_response({'success': True}), 200


@api.route('/nginx/reload', methods=['GET'])
def nginx_reload():
    ret = os.system('nginx -s reload')
    print(ret)
    if ret == 0:
        return flask.make_response({'success': True}), 200
    return flask.make_response({'success': False}), 200
