from dateutil import parser

from flask import jsonify, Blueprint, request, make_response

from data.db_session import create_session
from data.items import Item

blueprint = Blueprint(
    'items_api',
    __name__
)


def my_make_response(code: int, message: str):
    return make_response(jsonify({
        'code': code,
        'message': message
    }), code)


def get(item_id, db_session):
    item = db_session.query(Item).get(item_id).to_dict()
    children = db_session.query(Item).filter(Item.parentId == item_id)
    if item['type'] == 'CATEGORY':
        item['children'] = []
        for child in children:
            item['children'].append(get(child.id, db_session))

        # Подсчёт цены
        prices = []
        for child in item['children']:
            if child['type'] == 'CATEGORY':
                prices += [child['price']] * len(child['children'])
            else:
                prices += [child['price']]
        if len(prices):
            item['price'] = int(sum(prices) / len(prices))
        else:
            item['price'] = None
    else:
        item['children'] = None

    return item


@blueprint.route('/api/nodes/<string:item_id>')
def nodes(item_id):
    db_session = create_session()

    if not db_session.query(Item).get(item_id):
        return my_make_response(404, "Item not found")

    return jsonify(get(item_id, db_session))


def set_date(item_id, date, db_session):
    item = db_session.query(Item).get(item_id)
    item.date = date
    if item.parentId:
        set_date(item.parentId, date, db_session)


@blueprint.route('/api/imports', methods=['POST'])
def imports():
    db_session = create_session()

    try:
        parser.isoparse(request.json['updateDate'])
    except ValueError:
        print(request.json['updateDate'])
        return my_make_response(400, 'Validation Failed')

    for item in request.json['items']:
        if item['parentId'] is not None and (db_session.query(Item).get(item['parentId']) is None or
                                             db_session.query(Item).get(item['parentId']).type == 'OFFER') or \
                item.get('type') == 'CATEGORY' and item.get('price') is not None or \
                item.get('type') == 'OFFER' and (item.get('price') is None or item.get('price') < 0) or \
                item.get('name', '') is None:
            return my_make_response(400, 'Validation Failed')

        old_item: Item = db_session.query(Item).get(item['id'])
        if old_item:
            for arg in item:
                if arg == 'name':
                    old_item.name = item[arg]
                elif arg == 'parentId':
                    old_item.parentId = item[arg]
                elif arg == 'price':
                    old_item.price = item[arg]
                elif arg == 'type' and item[arg] != old_item.type:
                    return my_make_response(400, 'Validation Failed')

            set_date(old_item.id, request.json['updateDate'], db_session)
        else:
            item['date'] = request.json['updateDate']
            new_item = Item(**item)
            db_session.add(new_item)
            set_date(new_item.id, request.json['updateDate'], db_session)

    db_session.commit()
    return my_make_response(200, 'Вставка или обновление прошли успешно.')


# Рекурсивная функция удаления детей категории
def delete_with_children(parent_id, db_session):
    item = db_session.query(Item).get(parent_id)
    db_session.delete(item)

    children = db_session.query(Item).filter(Item.parentId == parent_id)
    for child in children:
        delete_with_children(child.id, db_session)


@blueprint.route('/api/delete/<string:item_id>', methods=['DELETE'])
def delete(item_id):
    db_session = create_session()
    if not db_session.query(Item).get(item_id):
        return my_make_response(404, "Item not found")

    delete_with_children(item_id, db_session)
    db_session.commit()
    return my_make_response(200, 'OK')
