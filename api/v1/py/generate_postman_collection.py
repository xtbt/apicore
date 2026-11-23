"""Generate the Postman collection from the Insomnia export.

Layer: tooling (development only, never imported by the API). The Insomnia file
is the single source of truth: edit it, run this script, and both clients stay
in sync.

    python3 generate_postman_collection.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'insomnia_apicore.json')
TARGET = os.path.join(HERE, 'postman_apicore.json')

# Insomnia writes {{ _.name }}; Postman writes {{name}}
VARIABLE = re.compile(r'\{\{\s*_\.(\w+)\s*\}\}')


def to_postman_variables(text):
    """Rewrite Insomnia template variables to Postman syntax."""
    return VARIABLE.sub(r'{{\1}}', text or '')


def build_request(resource):
    """Convert one Insomnia request into a Postman item."""
    headers = [{'key': h['name'], 'value': to_postman_variables(h['value'])}
               for h in resource.get('headers', [])]
    request = {
        'method': resource['method'],
        'header': headers,
        'url': to_postman_variables(resource['url']),
        'description': resource.get('description', ''),
    }
    body = resource.get('body') or {}
    if body.get('text'):
        request['body'] = {
            'mode': 'raw',
            'raw': to_postman_variables(body['text']),
            'options': {'raw': {'language': 'json'}},
        }
    auth = resource.get('authentication') or {}
    if auth.get('type') == 'bearer':
        request['auth'] = {
            'type': 'bearer',
            'bearer': [{'key': 'token', 'value': to_postman_variables(auth['token']),
                        'type': 'string'}],
        }
    return {'name': resource['name'], 'request': request,
            'response': [], 'event': []}


def build_items(resources, parent_id):
    """Nest groups and requests under `parent_id`, keeping the export order."""
    items = []
    for resource in resources:
        if resource.get('parentId') != parent_id:
            continue
        if resource['_type'] == 'request_group':
            items.append({'name': resource['name'],
                          'description': resource.get('description', ''),
                          'item': build_items(resources, resource['_id'])})
        elif resource['_type'] == 'request':
            items.append(build_request(resource))
    return items


def main():
    with open(SOURCE, encoding='utf-8') as source_file:
        export = json.load(source_file)
    resources = export['resources']
    workspace = next(r for r in resources if r['_type'] == 'workspace')
    environment = next(r for r in resources if r['_type'] == 'environment')

    collection = {
        'info': {
            'name': workspace['name'],
            'description': workspace.get('description', ''),
            'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
        },
        'item': build_items(resources, workspace['_id']),
        'variable': [{'key': key, 'value': str(value)}
                     for key, value in environment['data'].items()],
    }
    with open(TARGET, 'w', encoding='utf-8') as target_file:
        json.dump(collection, target_file, ensure_ascii=False, indent=2)
        target_file.write('\n')
    print(f'{os.path.basename(TARGET)}: {len(collection["item"])} carpetas, '
          f'{sum(len(folder["item"]) for folder in collection["item"])} solicitudes')


if __name__ == '__main__':
    main()
