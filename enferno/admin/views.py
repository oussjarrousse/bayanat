import os
import boto3
import hashlib
from flask import request, abort, Response, Blueprint, current_app, json, g, session, send_from_directory
from flask.templating import render_template
from flask_bouncer import requires
from flask_security.decorators import roles_required, login_required, current_user
from sqlalchemy import desc, or_, distinct, text
from flask_security.utils import hash_password
from enferno.admin.models import (Bulletin, Label, Source, Location, Eventtype, Media, Actor, Incident,
                                  IncidentHistory, BulletinHistory, ActorHistory, PotentialViolation, ClaimedViolation,
                                  Activity, Settings, Query)
from enferno.extensions import bouncer, rds, babel
from enferno.tasks import bulk_update_bulletins, bulk_update_actors, bulk_update_incidents
from enferno.user.models import User, Role
from enferno.utils.search_utils import SearchUtils

root = os.path.abspath(os.path.dirname(__file__))
admin = Blueprint('admin', __name__,
                  template_folder=os.path.join(root, 'templates'),
                  static_folder=os.path.join(root, 'static'),
                  url_prefix='/admin')

# default global items per page
PER_PAGE = 30


@babel.localeselector
def get_locale():
    """
    Sets the system global language.
    :return: system language from the current session.
    """
    override = request.args.get('lang')
    if override:
        session['lang'] = override
    return session.get('lang', 'en')

@admin.before_request
@login_required
def before_request():
    """
    Attaches the user object to all requests
    and a version number that is used to clear the static files cache globally.
    :return: None
    """
    g.user = current_user
    g.version = '2'


@admin.app_context_processor
def ctx():
    """
    passes all users to the application, based on the current user's permissions.
    :return: None
    """
    users = User.query.all()
    if current_user.is_authenticated:
        if current_user.has_role('Admin') or current_user.view_usernames:
            hide_name = False
        else:
            hide_name = True
        users = [u.to_dict(hide_name=hide_name) for u in users]
        return {'users': users}
    return {}


@bouncer.authorization_method
def define_authorization(user, ability):
    """
    Defines users abilities based on their stored permissions.
    :param user: system user
    :param ability: used to restrict/allow what a user can do
    :return: None
    """
    if user.view_usernames:
        ability.can('view', 'usernames')
    if user.view_simple_history or user.view_full_history:
        ability.can('view', 'history')
    # if user.has_role('Admin'):
    #     ability.can('edit', 'Bulletin')
    # else:
    #     def if_assigned(bulletin):
    #         return bulletin.assigned_to_id == user.id

    #     ability.can('edit', Bulletin, if_assigned)


@admin.route('/dashboard')
def dashboard():
    """
    Endpoint to render the dashboard.
    :return: html template for dashboard.
    """
    return render_template('index.html')


# Labels routes
@admin.route('/labels/')
def labels():
    """
    Endpoint to render the labels backend page.
    :return: html template for labels management.
    """
    return render_template('admin/labels.html')


@admin.route('/api/labels/', defaults={'page': 1})
@admin.route('/api/labels/<int:page>/')
def api_labels(page):
    """
    API endpoint feed and filter labels with paging
    :param page: db query offset
    :return: json response of label objects.
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(
            Label.title.ilike('%' + q + '%')
        )
    typ = request.args.get('typ', None)
    if typ and typ in ['for_bulletin', 'for_actor', 'for_incident', 'for_offline']:
        query.append(
            getattr(Label, typ) == True
        )
    fltr = request.args.get('fltr', None)
    if fltr and fltr in ['verified']:
        query.append(
            getattr(Label, fltr) == True
        )
    else:
        query.append(
            Label.verified == False
        )
    result = Label.query.filter(
        *query).order_by(Label.id).paginate(
        page, PER_PAGE, True)

    response = {'items': [item.to_dict(request.args.get('mode', 1)) for item in result.items], 'perPage': PER_PAGE,
                'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@roles_required(['Admin', 'Mod'])
@admin.route('/api/label/', methods=['POST'])
def api_label_create():
    """
    Endpoint to create a label.
    :return: success/error based on the operation result.
    """
    if request.method == 'POST':
        label = Label()
        created = label.from_json(request.json['item'])
        if created.save():
            return 'Created !'
        else:
            return 'Save Failed', 417


@roles_required(['Admin', 'Mod'])
@admin.route('/api/label/<int:id>', methods=['PUT'])
def api_label_update(id):
    """
    Endpoint to update a label.
    :param id: id of the label
    :return: success/error based on the operation result.
    """
    if request.method == 'PUT':
        label = Label.query.get(id)
        if label is not None:
            label = label.from_json(request.json['item'])
            label.save()
            return 'Saved !', 200
        else:
            return 'Not Found!', 417

    else:
        return 'Unauthorized', 403


@roles_required(['Admin', 'Mod'])
@admin.route('/api/label/<int:id>', methods=['DELETE'])
def api_label_delete(id):
    """
    Endpoint to delete a label.
    :param id: id of the label
    :return: Success/error based on operation's result.
    """
    if request.method == 'DELETE':
        label = Label.query.get(id)
        label.delete()
        return 'Deleted !'
    else:
        return 'Error', 417




@roles_required(['Admin', 'Mod'])
@admin.route('/api/label/import/', methods=['POST'])
def api_label_import():
    """
    Endpoint to import labels via CSV
    :return: Success/error based on operation's result.
    """
    if 'csv' in request.files:
        Label.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# EventType routes
@admin.route('/eventtypes/')
def eventtypes():
    """
    Endpoint to render event types backend
    :return: html template of the event types backend
    """
    return render_template('admin/eventtypes.html')


@admin.route('/api/eventtypes/', defaults={'page': 1})
@admin.route('/api/eventtypes/<int:page>/')
def api_eventtypes(page):
    """
    API endpoint to serve json feed of even types with paging support
    :param page: db query offset
    :return: json feed/success or error/404 based on request data
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(Eventtype.title.ilike('%' + q + '%'))

    typ = request.args.get('typ', None)
    if typ and typ in ['for_bulletin', 'for_actor']:
        query.append(
            getattr(Eventtype, typ) == True
        )
    result = Eventtype.query.filter(
        *query).order_by(Eventtype.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@roles_required(['Admin', 'Mod'])
@admin.route('/api/eventtype/', methods=['POST'])
def api_eventtype_create():
    """
    Endpoint to create an Event Type
    :return: Success/Error based on operation's result
    """
    if request.method == 'POST':
        eventtype = Eventtype()
        created = eventtype.from_json(request.json['item'])
        if created.save():
            return 'Created !'
        else:
            return 'Save Failed', 417


@roles_required(['Admin', 'Mod'])
@admin.route('/api/eventtype/<int:id>', methods=['PUT'])
def api_eventtype_update(id):
    """
    Endpoint to update an Event Type
    :param id: id of the item to be updated
    :return: success/error based on the operation's result
    """
    if request.method == 'PUT':
        eventtype = Eventtype.query.get(id)
        if eventtype is not None:
            eventtype = eventtype.from_json(request.json['item'])
            eventtype.save()
            return 'Saved !', 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


@roles_required(['Admin', 'Mod'])
@admin.route('/api/eventtype/<int:id>', methods=['DELETE'])
def api_eventtype_delete(id):
    """
    Endpoint to delete an event type
    :param id: id of the item
    :return: success/error based on the operation's result
    """
    if request.method == 'DELETE':
        eventtype = Eventtype.query.get(id)
        eventtype.delete()
        return 'Deleted !'
    else:
        return 'Error',417


@roles_required(['Admin', 'Mod'])
@admin.route('/api/eventtype/import/', methods=['POST'])
def api_eventtype_import():
    """
    Endpoint to bulk import event types from a CSV file
    :return: success/error based on the operation's result
    """
    if 'csv' in request.files:
        Eventtype.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400



@admin.route('/api/potentialviolation/', defaults={'page': 1})
@admin.route('/api/potentialviolation/<int:page>/')
def api_potentialviolations(page):
    """
    API endpoint that feeds json data of potential violations with paging and search support
    :param page: db query offset
    :return: json feed / success or error based on the operation/request data
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(PotentialViolation.title.ilike('%' + q + '%'))
    result = PotentialViolation.query.filter(
        *query).order_by(PotentialViolation.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@roles_required(['Admin', 'Mod'])
@admin.route('/api/potentialviolation/', methods=['POST'])
def api_potentialviolation_create():
    """
    Endpoint to create a potential violation
    :return: success/error based on operation's result
    """
    if request.method == 'POST':
        potentialviolation = PotentialViolation()
        created = potentialviolation.from_json(request.json['item'])
        if created.save():
            return 'Created !'
        else:
            return 'Save Failed', 417


@roles_required(['Admin', 'Mod'])
@admin.route('/api/potentialviolation/<int:id>', methods=['PUT'])
def api_potentialviolation_update(id):
    """
    Endpoint to update a potential violation
    :param id: id of the item to be updated
    :return: success/error based on the operation's result
    """
    if request.method == 'PUT':
        potentialviolation = PotentialViolation.query.get(id)
        if potentialviolation is not None:
            potentialviolation = potentialviolation.from_json(request.json['item'])
            potentialviolation.save()
            return 'Saved !', 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


@roles_required(['Admin', 'Mod'])
@admin.route('/api/potentialviolation/<int:id>', methods=['DELETE'])
def api_potentialviolation_delete(id):
    """
    Endpoint to delete a potential violation
    :param id: id of the item to delete
    :return: success/error based on the operation's result
    """
    if request.method == 'DELETE':
        potentialviolation = PotentialViolation.query.get(id)
        potentialviolation.delete()
        return 'Deleted !'
    else:
        return 'Error', 417


@roles_required(['Admin', 'Mod'])
@admin.route('/api/potentialviolation/import/', methods=['POST'])
def api_potentialviolation_import():
    """
    Endpoint to import potential violations from csv file
    :return: success/error based on operation's result
    """
    if 'csv' in request.files:
        PotentialViolation.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


@admin.route('/api/claimedviolation/', defaults={'page': 1})
@admin.route('/api/claimedviolation/<int:page>')
def api_claimedviolations(page):
    """
    API endpoint to feed json items of claimed violations, supports paging and search
    :param page: db query offset
    :return: json feed / success or error code
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(ClaimedViolation.title.ilike('%' + q + '%'))
    result = ClaimedViolation.query.filter(
        *query).order_by(ClaimedViolation.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@roles_required(['Admin', 'Mod'])
@admin.route('/api/claimedviolation/', methods=['POST'])
def api_claimedviolation_create():
    """
    Endpoint to create a claimed violation
    :return: success / error based on operation's result
    """
    if request.method == 'POST':
        claimedviolation = ClaimedViolation()
        created = claimedviolation.from_json(request.json['item'])
        if created.save():
            return 'Created !'
        else:
            return 'Save Failed', 417


@roles_required(['Admin', 'Mod'])
@admin.route('/api/claimedviolation/<int:id>', methods=['PUT'])
def api_claimedviolation_update(id):
    """
    Endpoint to update a claimed violation
    :param id: id of the item to update
    :return: success/error based on operation's result
    """
    if request.method == 'PUT':
        claimedviolation = ClaimedViolation.query.get(id)
        if claimedviolation is not None:
            claimedviolation = claimedviolation.from_json(request.json['item'])
            claimedviolation.save()
            return 'Saved !', 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


@roles_required(['Admin', 'Mod'])
@admin.route('/api/claimedviolation/<int:id>', methods=['DELETE'])
def api_claimedviolation_delete(id):
    """
    Endpoint to delete a claimed violation
    :param id: id of the item to delete
    :return: success/ error based on operation's result
    """
    if request.method == 'DELETE':
        claimedviolation = ClaimedViolation.query.get(id)
        claimedviolation.delete()
        return 'Deleted !'


@roles_required(['Admin', 'Mod'])
@admin.route('/api/claimedviolation/import/', methods=['POST'])
def api_claimedviolation_import():
    """
    Endpoint to import claimed violations from a CSV file
    :return: success/error based on operation's result
    """
    if 'csv' in request.files:
        ClaimedViolation.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# Sources routes
@admin.route('/sources/')
def sources():
    """
    Endpoint to render sources backend page
    :return: html of the sources page
    """
    return render_template('admin/sources.html')


@admin.route('/api/sources/', defaults={'page': 1})
@admin.route('/api/sources/<int:page>')
def api_sources(page):
    """
    API Endpoint to feed json data of sources, supports paging and search
    :param page: db query offset
    :return: json feed of sources or error code based on operation's result
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(Source.title.ilike('%' + q + '%'))
    result = Source.query.filter(
        *query).order_by(-Source.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@roles_required(['Admin', 'Mod'])
@admin.route('/api/source/', methods=['POST'])
def api_source_create():
    """
    Endpoint to create a source
    :return: success/error based on operation's result
    """
    if request.method == 'POST':
        source = Source()
        created = source.from_json(request.json['item'])
        if created.save():
            return 'Created !'
        else:
            return 'Save Failed', 417


@roles_required(['Admin', 'Mod'])
@admin.route('/api/source/<int:id>', methods=['PUT'])
def api_source_update(id):
    """
    Endpoint to update a source
    :param id: id of the item to update
    :return: success/error based on the operation's result
    """
    if request.method == 'PUT':
        source = Source.query.get(id)
        if source is not None:
            source = source.from_json(request.json['item'])
            source.save()
            return 'Saved !', 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


@roles_required(['Admin', 'Mod'])
@admin.route('/api/source/<int:id>', methods=['DELETE'])
def api_source_delete(id):
    """
    Endopint to delete a source item
    :param id: id of the item to delete
    :return: success/error based on operation's result
    """
    if request.method == 'DELETE':
        source = Source.query.get(id)
        source.delete()
        return 'Deleted !'



@roles_required(['Admin', 'Mod'])
@admin.route('/api/source/import/', methods=['POST'])
def api_source_import():
    """
    Endpoint to import sources from CSV data
    :return: success/error based on operation's result
    """
    if 'csv' in request.files:
        Source.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# locations routes

@admin.route('/locations/')
def locations():
    """Endpoint for locations management."""
    return render_template('admin/locations.html')


@admin.route('/api/locations/', defaults={'page': 1})
@admin.route('/api/locations/<int:page>')
def api_locations(page):
    """Returns locations in JSON format, allows search and paging."""
    query = []
    q = request.args.get('q', None)
    per_page = request.args.get('per_page', PER_PAGE, int)
    typ = request.args.get('typ', None)
    if q is not None:
        search = '%' + q.replace(' ', '%') + '%'
        query.append(
            or_(
                Location.full_location.ilike(search),
                Location.title_ar.ilike(search),
            )

        )
    res_type = 0
    if typ and typ in ['s', 'g', 'c', 'd']:
        result = Location.query.with_entities(distinct(getattr(Location, 'parent_{}_id'.format(typ)))).all()
        ids = [item[0] for item in result]
        query.append(
            Location.id.in_(ids)
        )
        res_type = 1

    result = Location.query.filter(*query).order_by(Location.id).paginate(
        page, per_page, True)
    items = [item.to_dict() for item in result.items if item.id != 0] if res_type == 0 else [item.min_json() for item in result.items if item.id != 0]
    response = {'items':items, 'perPage': per_page,
                'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@roles_required(['Admin', 'Mod'])
@admin.route('/api/location/', methods=['POST'])
def api_location_create():
    """Endpoint for creating locations."""
    if request.method == 'POST':
        location = Location()
        created = location.from_json(request.json['item'])
        if created.save():
            return 'Created !'
        else:
            return 'Save Failed', 417


@roles_required(['Admin', 'Mod'])
@admin.route('/api/location/<int:id>', methods=['PUT'])
def api_location_update(id):
    """Endpoint for updating locations. """
    if request.method == 'PUT':
        location = Location.query.get(id)
        if location is not None:
            location = location.from_json(request.json['item'])
            location.save()
            return 'Saved !', 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


@roles_required(['Admin', 'Mod'])
@admin.route('/api/location/<int:id>', methods=['DELETE'])
def api_location_delete(id):
    """Endpoint for deleting locations. """

    if request.method == 'DELETE':
        location = Location.query.get(id)
        location.delete()
        return 'Deleted !'


@roles_required(['Admin', 'Mod'])
@admin.route('/api/location/import/', methods=['POST'])
def api_location_import():
    """Endpoint for importing locations."""
    if 'csv' in request.files:
        Location.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# Bulletin routes
@admin.route('/bulletins/', defaults={'id': None})
@admin.route('/bulletins/<int:id>')
def bulletins(id):
    """Endpoint for bulletins management."""
    return render_template('admin/bulletins.html')


@admin.route('/api/bulletins/', methods=['POST', 'GET'])
def api_bulletins():
    """Returns bulletins in JSON format, allows search and paging."""
    query = []
    su = SearchUtils(request.json, cls='Bulletin')
    queries, ops = su.get_query()
    result = Bulletin.query.filter(*queries.pop(0))

    if len(queries) > 0:
            while queries:
                nextOp = ops.pop(0)
                nextQuery = queries.pop(0)
                if nextOp == 'union':
                    result = result.union(Bulletin.query.filter(*nextQuery))
                elif nextOp == 'intersect':
                    result = result.intersect(Bulletin.query.filter(*nextQuery))
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    # handle sort
    #default
    sort = '-id'


    options = request.json.get('options')
    if options:
        sort_by = options.get('sortBy')
        sort_desc = options.get('sortDesc')
        if sort_by:
            sort = sort_by[0]
            if sort_desc and sort_desc[0]:
                sort = '{} desc'.format(sort)


    result = result.order_by(text(sort)).paginate(
        page, per_page, True)

    # Select json encoding type
    mode = request.args.get('mode', '1')
    response = {'items': [item.to_dict(mode=mode) for item in result.items], 'perPage': per_page, 'total': result.total}

    return Response(json.dumps(response),
                    content_type='application/json'), 200


@roles_required(['Admin', 'DA'])
@admin.route('/api/bulletin/', methods=['POST'])
def api_bulletin_create():
    """Creates a new bulletin."""

    if request.method == 'POST':
        bulletin = Bulletin()
        bulletin.from_json(request.json['item'])
        bulletin.save()
        # the below will create the first revision by default 
        bulletin.create_revision()
        # Record activity
        Activity.create(current_user, Activity.ACTION_CREATE, bulletin.to_mini(), 'bulletin')
        return 'Created bulletin {}'.format(bulletin.id)
    else:
        return 'Save Failed', 417


@roles_required(['Admin', 'DA'])
@admin.route('/api/bulletin/<int:id>', methods=['PUT'])
def api_bulletin_update(id):
    """Updates a bulletin."""

    if request.method == 'PUT':
        bulletin = Bulletin.query.get(id)
        if bulletin is not None:
            bulletin = bulletin.from_json(request.json['item'])
            # Create a revision using latest values
            # this method automatically commits
            # bulletin changes (referenced)           
            bulletin.create_revision()

            # Record Activity
            Activity.create(current_user, Activity.ACTION_UPDATE, bulletin.to_mini(), 'bulletin')
            return 'Saved Bulletin ... # {}'.format(bulletin.id), 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


# Add/Update review bulletin endpoint
@roles_required(['Admin', 'DA'])
@admin.route('/api/bulletin/review/<int:id>', methods=['PUT'])
def api_bulletin_review_update(id):
    """
    Endpoint to update a bulletin review
    :param id: id of the bulletin
    :return: success/error based on the outcome
    """
    if request.method == 'PUT':
        bulletin = Bulletin.query.get(id)
        if bulletin is not None:
            bulletin.review = request.json['item']['review'] if 'review' in request.json['item'] else ''
            bulletin.review_action = request.json['item']['review_action'] if 'review_action' in request.json[
                'item'] else ''

            bulletin.status = 'Peer Reviewed'

            # Create a revision using latest values
            # this method automatically commi
            #  bulletin changes (referenced)           
            bulletin.create_revision()

            # Record Activity
            Activity.create(current_user, Activity.ACTION_UPDATE, bulletin.to_mini(), 'bulletin')
            return 'Buulletin review updated ... # {}'.format(bulletin.id), 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


# bulk update bulletin endpoint
@admin.route('/api/bulletin/bulk/', methods=['PUT'])
@roles_required('Admin')
def api_bulletin_bulk_update():
    """
    Endpoint to bulk update bulletins
    :return: success / error
    """
    if request.method == 'PUT':
        ids = request.json['items']
        bulk = request.json['bulk']

        if ids and len(bulk):
            job = bulk_update_bulletins.delay(ids, bulk, current_user.id)
            # store job id in user's session for status monitoring
            key = 'user{}:{}'.format(current_user.id, job.id)
            rds.set(key, job.id)
            # expire in 3 hour
            rds.expire(key, 60 * 60 * 3)
            return '{}'.format('Bulk update queued successfully.'), 200
        else:
            return 'No items selected, or nothing to update', 417

    else:
        return 'Unauthorized', 403


@admin.route('/api/bulletin/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_bulletin_delete(id):
    """
    Endpoint to delete a bulletin
    :param id: id of the bulletin to be deleted
    :return: success/error
    """
    if request.method == 'DELETE':
        bulletin = Bulletin.query.get(id)
        bulletin.delete()

        # Record Activity
        Activity.create(current_user, Activity.ACTION_DELETE, bulletin.to_mini(), 'bulletin')
        return 'Deleted !'


# get one bulletin
@admin.route('/api/bulletin/<int:id>', methods=['GET'])
def api_bulletin_get(id):
    """
    Endpoint to get a single bulletin
    :param id: id of the bulletin
    :return: bulletin in json format / success or error
    """
    if request.method == 'GET':
        bulletin = Bulletin.query.get(id)
        if not bulletin:
            abort(404)
        else:
            return bulletin.to_json(), 200


@roles_required(['Admin', 'DA'])
@admin.route('/api/bulletin/import/', methods=['POST'])
def api_bulletin_import():
    """
    Endpoint to import bulletins from csv data
    :return: success / error
    """
    if 'csv' in request.files:
        Bulletin.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# Media special endpoints
@roles_required(['Admin', 'DA'])
@admin.route('/api/media/upload/', methods=['POST'])
def api_medias_upload():
    """
    Endpoint to upload files (based on file system settings : s3 or local file system)
    :return: success /error based on operation's result
    """

    if 'media' in request.files:
        if current_app.config['FILESYSTEM_LOCAL']:
            return api_local_medias_upload(request)
        else:

            s3 = boto3.resource('s3', aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                                aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'])

            f = request.files.get('media')

            # final file
            filename = Media.generate_file_name(f.filename)
            # filepath = (Media.media_dir/filename).as_posix()

            response = s3.Bucket(current_app.config['S3_BUCKET']).put_object(Key=filename, Body=f)
            # print(response.get())
            etag = response.get()['ETag']

            return json.dumps({'filename': filename, 'etag': etag}), 200

    return 'Invalid request params', 417


''' #File delete is disabled for now 
@admin.route('/api/media/upload/', methods=['DELETE'])
@roles_required('Admin')
def api_media_file_delete():
    """
    Endpoint to handle file deletions
    :return: success/error
    """
    data = request.get_json(force=True)
    try:
        os.remove((Media.media_dir / data['filename']).as_posix())
        return 'Removed', 200
    except Exception as e:
        print(str(e))
        return 'Error', 417
'''

# return signed url from s3 valid for some time
@admin.route('/api/media/<filename>')
def serve_media(filename):
    """
    Endpoint to generate  file urls to be served (based on file system type)
    :param filename: name of the file
    :return: temporarily accesssible url of the file
    """

    if current_app.config['FILESYSTEM_LOCAL']:
        return '/admin/api/serve/media/{}'.format(filename)
    else:
        s3 = boto3.client('s3',
                          aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                          aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'])
        url = s3.generate_presigned_url('get_object', Params={'Bucket': current_app.config['S3_BUCKET'], 'Key': filename},                            ExpiresIn=36000)
        return url



def api_local_medias_upload(request):
    # file pond sends multiple requests for multiple files (handle each request as a separate file )
    try:
        f = request.files.get('media')
        # final file
        filename = Media.generate_file_name(f.filename)
        filepath = (Media.media_dir / filename).as_posix()
        f.save(filepath)
        # get md5 hash
        f = open(filepath,'rb').read()
        etag = hashlib.md5(f).hexdigest()

        response = {'etag': etag, 'filename': filename}

        return Response(json.dumps(response), content_type='application/json'), 200
    except Exception as e:
        return 'Problem uploading file: {}'.format(e), 417


@admin.route('/api/serve/media/<filename>')
def api_local_serve_media(filename):
    """
    serves file from local file system
    """
    return send_from_directory('media', filename)



# Medias routes

@admin.route('/api/medias/', defaults={'page': 1})
@admin.route('/api/medias/<int:page>/')
def api_medias(page):
    """
    Endopint to feed json data of media items , supports paging and search
    :param page: db query offset
    :return: success + json feed or error in case of failure
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(
            Media.title.ilike('%' + q + '%')
        )
    result = Media.query.filter(
        *query).order_by(Media.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@roles_required(['Admin', 'DA'])
@admin.route('/api/media/', methods=['POST'])
def api_media_create():
    """
    Endpoint to create a media item
    :return: success / error
    """
    if request.method == 'POST':
        media = Media()
        created = media.from_json(request.json['item'])
        if created.save():
            return 'Created !'
        else:
            return 'Save Failed', 417


@roles_required(['Admin', 'DA'])
@admin.route('/api/media/<int:id>', methods=['PUT'])
def api_media_update(id):
    """
    Endpoint to update a media item
    :param id: id of the item to be updated
    :return: success / error
    """
    if request.method == 'PUT':
        media = Media.query.get(id)
        if media is not None:
            media = media.from_json(request.json['item'])
            media.save()
            return 'Saved !', 200
        else:
            return 'Not Found!', 417

    else:
        return 'Unauthorized', 403


@admin.route('/api/media/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_media_delete(id):
    """
    Endpoint to handle media deletion
    :param id: id of the media to be deleted
    :return: success / error
    """
    if request.method == 'DELETE':
        media = Media.query.get(id)
        media.delete()
        return 'Deleted !'



# Actor routes
@admin.route('/actors/', defaults={'id': None})
@admin.route('/actors/<int:id>')
def actors(id):
    """Endpoint to render actors page."""
    return render_template('admin/actors.html')


@admin.route('/api/actors/', methods=['POST', 'GET'])
def api_actors():
    """Returns actors in JSON format, allows search and paging."""
    query = []
    su = SearchUtils(request.json, cls='Actor')
    queries, ops = su.get_query()
    result = Actor.query.filter(*queries.pop(0))
    # print (queries, ops)
    if len(queries) > 0:
        while queries:
            nextOp = ops.pop(0)
            nextQuery = queries.pop(0)
            if nextOp == 'union':
                result = result.union(Actor.query.filter(*nextQuery))
            elif nextOp == 'intersect':
                result = result.intersect(Actor.query.filter(*nextQuery))

    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    result = result.order_by(Actor.id.desc()).paginate(
        page, per_page, True)
    # Select json encoding type
    mode = request.args.get('mode', '1')
    response = {'items': [item.to_dict(mode=mode) for item in result.items], 'perPage': per_page, 'total': result.total}

    return Response(json.dumps(response),
                    content_type='application/json'), 200


# create actor endpoint
@roles_required(['Admin', 'DA'])
@admin.route('/api/actor/', methods=['POST'])
def api_actor_create():
    """
    Endpoint to create an Actor item
    :return: success/error based on the operation's result
    """
    if request.method == 'POST':
        actor = Actor()
        actor.from_json(request.json['item'])
        actor.save()

        # the below will create the first revision by default
        actor.create_revision()
        # Record activity
        Activity.create(current_user, Activity.ACTION_CREATE, actor.to_mini(), 'actor')
        return 'Created actor {}'.format(actor.id)
    else:
        return 'Save Failed', 417


# update actor endpoint 
@roles_required(['Admin', 'DA'])
@admin.route('/api/actor/<int:id>', methods=['PUT'])
def api_actor_update(id):
    """
    Endpoint to update an Actor item
    :param id: id of the actor to be updated
    :return: success/error
    """
    if request.method == 'PUT':
        actor = Actor.query.get(id)
        if actor is not None:
            actor = actor.from_json(request.json['item'])
            # Create a revision using latest values
            # this method automatically commits
            #  actor changes (referenced)           
            actor.create_revision()

            # Record Activity
            Activity.create(current_user, Activity.ACTION_UPDATE, actor.to_mini(), 'actor')
            return 'Saved Actor ... # {}'.format(actor.id), 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


# Add/Update review actor endpoint
@roles_required(['Admin', 'DA'])
@admin.route('/api/actor/review/<int:id>', methods=['PUT'])
def api_actor_review_update(id):
    """
    Endpoint to update an Actor's review item
    :param id: id of the actor
    :return: success/error
    """
    if request.method == 'PUT':
        actor = Actor.query.get(id)
        if actor is not None:
            actor.review = request.json['item']['review'] if 'review' in request.json['item'] else ''
            actor.review_action = request.json['item']['review_action'] if 'review_action' in request.json[
                'item'] else ''

            actor.status = 'Peer Reviewed'

            # Create a revision using latest values
            # this method automatically commi
            #  bulletin changes (referenced)           
            actor.create_revision()

            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, actor.to_mini(), 'actor')
            return 'Actor review updated ... # {}'.format(actor.id), 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


# bulk update actor endpoint
@roles_required(['Admin', 'DA'])
@admin.route('/api/actor/bulk/', methods=['PUT'])
def api_actor_bulk_update():
    """
    Endpoint to bulk update actors
    :return: success/error
    """
    if request.method == 'PUT':
        ids = request.json['items']
        bulk = request.json['bulk']
        if ids and len(bulk):
            job = bulk_update_actors.delay(ids, bulk, current_user.id)
            # store job id in user's session for status monitoring
            key = 'user{}:{}'.format(current_user.id, job.id)
            rds.set(key, job.id)
            # expire in 3 hour
            rds.expire(key, 60 * 60 * 3)
            return '{}'.format('Bulk update queued successfully.'), 200
        else:
            return 'No items selected, or nothing to update', 417

    else:
        return 'Unauthorized', 403


@roles_required('Admin')
@admin.route('/api/actor/<int:id>', methods=['DELETE'])
def api_actor_delete(id):
    """
    Endpoint to delete an actor
    :param id: id of the actor to be deleted
    :return: success/error
    """
    if request.method == 'DELETE':
        actor = Actor.query.get(id)
        actor.delete()
        # Record activity
        Activity.create(current_user, Activity.ACTION_DELETE, actor.to_mini(), 'actor')
        return 'Deleted !'


# get one actor

@admin.route('/api/actor/<int:id>', methods=['GET'])
def api_actor_get(id):
    """
    Endpoint to get a single actor
    :param id: id of the actor
    :return: actor data in json format + success or error in case of failure
    """
    if request.method == 'GET':
        actor = Actor.query.get(id)
        if not actor:
            abort(404)
        else:
            return actor.to_json(), 200


# Bulletin History Helpers

@admin.route('/api/bulletinhistory/<int:bulletinid>')
@requires('view', 'history')
def api_bulletinhistory(bulletinid):
    """
    Endpoint to get revision history of a bulletin
    :param bulletinid: id of the bulletin item
    :return: json feed of item's history , or error
    """
    result = BulletinHistory.query.filter_by(bulletin_id=bulletinid).order_by(desc(BulletinHistory.id)).all()
    # For standardization 
    response = {'items': [item.to_dict() for item in result]}
    return Response(json.dumps(response),
                    content_type='application/json')


# Actor History Helpers 

@admin.route('/api/actorhistory/<int:actorid>')
@requires('view', 'history')
def api_actorhistory(actorid):
    """
        Endpoint to get revision history of an actor
        :param actorid: id of the actor item
        :return: json feed of item's history , or error
        """
    result = ActorHistory.query.filter_by(actor_id=actorid).order_by(desc(ActorHistory.id)).all()
    # For standardization 
    response = {'items': [item.to_dict() for item in result]}
    return Response(json.dumps(response),
                    content_type='application/json')


# Incident History Helpers

@admin.route('/api/incidenthistory/<int:incidentid>')
@requires('view', 'history')
def api_incidenthistory(incidentid):
    """
        Endpoint to get revision history of an incident item
        :param incidentid: id of the incident item
        :return: json feed of item's history , or error
        """
    result = IncidentHistory.query.filter_by(incident_id=incidentid).order_by(desc(IncidentHistory.id)).all()
    # For standardization 
    response = {'items': [item.to_dict() for item in result]}
    return Response(json.dumps(response),
                    content_type='application/json')


# user management routes


@admin.route('/api/users/', defaults={'page': 1})
@admin.route('/api/users/<int:page>/')
@roles_required('Admin')
def api_users(page):
    """
    API endpoint to feed users data in json format , supports paging and search
    :param page: db query offset
    :return: success and json feed of items or error
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(User.name.ilike('%' + q + '%'))
    result = User.query.filter(
        *query).order_by(User.id).paginate(
        page, 100, True)

    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json'), 200


@admin.route('/users/')
@roles_required('Admin')
def users():
    """
    Endpoint to render the users backend page
    :return: html page of the users backend.
    """
    return render_template('admin/users.html')


@admin.route('/api/user/', methods=['POST'])
@roles_required('Admin')
def api_user_create():
    """
    Endpoint to create a user item
    :return: success / error baesd on operation's outcome
    """
    if request.method == 'POST':
        # validate existing
        u = request.json['item']
        email = u.get('email',None)
        exists = User.query.filter(User.email==email).first()
        if exists:
            return 'Error, Email Already Exists', 417
        user = User()
        user.from_json(u)
        user.save()

        # Record activity
        Activity.create(current_user, Activity.ACTION_CREATE, user.to_mini(), 'user')
        return 'Success.', 200
    else:
        return 'rejected', 417


@admin.route('/api/user/<int:uid>', methods=['PUT'])
@roles_required('Admin')
def api_user_update(uid):
    """Endpoint to update a user."""
    if request.method == 'PUT':
        user = User.query.get(uid)
        if user is not None:
            # set password only if user updated it 
            if len(request.json['item']['password']) > 0:
                user.password = hash_password(request.json['item']['password'])
            user.active = request.json['item']['active']
            if 'roles' in request.json['item']:
                role_ids = [r['id'] for r in request.json['item']['roles']]
                roles = Role.query.filter(Role.id.in_(role_ids)).all()
                user.roles = roles
            user.view_usernames = request.json['item']['view_usernames']
            user.view_simple_history = request.json['item']['view_simple_history']
            user.view_full_history = request.json['item']['view_full_history']

            user.name = request.json['item']['name']
            user.save()

            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, user.to_mini(), 'user')
            return 'Success.', 200
        else:
            return 'Not Found!', 404

    else:
        return 'Error', 417


@admin.route('/api/user/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_user_delete(id):
    """
    Endpoint to delete a user
    :param id: id of the user to be deleted
    :return: success/error
    """
    if request.method == 'DELETE':
        user = User.query.get(id)
        user.delete()

        # Record activity
        Activity.create(current_user, Activity.ACTION_DELETE, user.to_mini(), 'user')
        return 'Deleted !'



# Roles routes
@admin.route('/roles/')
def roles():
    """
    Endpoint to redner roles backend page
    :return: html of the page
    """
    return render_template('admin/roles.html')


@admin.route('/api/roles/', defaults={'page': 1})
@admin.route('/api/roles/<int:page>/')
def api_roles(page):
    """
    API endpoint to feed roles items in josn format - supports paging and search
    :param page: db query offset
    :return: successful json feed or error
    """
    query = []
    q = request.args.get('q', None)
    if q is not None:
        query.append(
            Role.title.ilike('%' + q + '%')
        )
    result = Role.query.filter(
        *query).order_by(Role.id).paginate(
        page, PER_PAGE, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': PER_PAGE, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@roles_required('Admin')
@admin.route('/api/role/', methods=['POST'])
def api_role_create():
    """
    Endpoint to create a role item
    :return: success/error
    """
    if request.method == 'POST':
        role = Role()
        created = role.from_json(request.json['item'])
        if created.save():
            return 'Created !'
            # Record activity
            Activity.create(current_user, Activity.ACTION_CREATE, role.to_mini(), 'user')
        else:
            return 'Save Failed', 417


@roles_required('Admin')
@admin.route('/api/role/<int:id>', methods=['PUT'])
def api_role_update(id):
    """
    Endpoint to update a role item
    :param id: id of the role to be updated
    :return: success / error
    """
    if request.method == 'PUT':
        role = Role.query.get(id)
        if role is not None:
            role = role.from_json(request.json['item'])
            role.save()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, role.to_mini(), 'user')
            return 'Saved !', 200
        else:
            return 'Not Found!', 417

    else:
        return 'Unauthorized', 403


@admin.route('/api/role/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_role_delete(id):
    """
    Endpoint to delete a role item
    :param id: id of the role to be deleted
    :return: success / error
    """
    if request.method == 'DELETE':
        role = Role.query.get(id)
        role.delete()
        # Record activity
        Activity.create(current_user, Activity.ACTION_DELETE, role.to_mini(), 'user')
        return 'Deleted !'


@admin.route('/api/role/import/', methods=['POST'])
@roles_required('Admin')
def api_role_import():
    """
    Endpoint to import role items from a CSV file
    :return: success / error
    """
    if 'csv' in request.files:
        Role.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 400


# Incident routes
@admin.route('/incidents/', defaults={'id': None})
@admin.route('/incidents/<int:id>')
def incidents(id):
    """
    Endpoint to render incidents backend page
    :return: html page of the incidents backend management
    """
    # Pass all users to the template
    return render_template('admin/incidents.html')


@admin.route('/api/incidents/', methods=['POST', 'GET'])
def api_incidents():
    """Returns actors in JSON format, allows search and paging."""
    query = []

    su = SearchUtils(request.json, cls='Incident')

    query = su.get_query()

    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    print(*query)
    result = Incident.query.filter(
        *query).order_by(Incident.id.desc()).paginate(
        page, per_page, True)
    # Select json encoding type
    mode = request.args.get('mode', '1')
    response = {'items': [item.to_dict(mode=mode) for item in result.items], 'perPage': per_page, 'total': result.total}

    return Response(json.dumps(response),
                    content_type='application/json'), 200



@roles_required(['Admin', 'DA'])
@admin.route('/api/incident/', methods=['POST'])
def api_incident_create():
    """API endpoint to create an incident."""
    if request.method == 'POST':
        incident = Incident()
        incident.from_json(request.json['item'])
        incident.save()
        # the below will create the first revision by default 
        incident.create_revision()
        # Record activity
        Activity.create(current_user, Activity.ACTION_CREATE, incident.to_mini(), 'incident')
        return 'Created incident {}'.format(incident.id)
    else:
        return 'Save Failed', 417


# update incident endpoint 
@roles_required(['Admin', 'DA'])
@admin.route('/api/incident/<int:id>', methods=['PUT'])
def api_incident_update(id):
    """API endpoint to update an incident."""
    if request.method == 'PUT':
        incident = Incident.query.get(id)
        if incident is not None:
            incident = incident.from_json(request.json['item'])
            # Create a revision using latest values
            # this method automatically commits
            # incident changes (referenced)           
            incident.create_revision()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, incident.to_mini(), 'incident')
            return 'Saved Incident ... # {}'.format(incident.id), 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


# Add/Update review incident endpoint
@roles_required(['Admin', 'DA'])
@admin.route('/api/incident/review/<int:id>', methods=['PUT'])
def api_incident_review_update(id):
    """
    Endpoint to update an incident review item
    :param id: id of the incident
    :return: success / error
    """
    if request.method == 'PUT':
        incident = Incident.query.get(id)
        if incident is not None:
            incident.review = request.json['item']['review'] if 'review' in request.json['item'] else ''
            incident.review_action = request.json['item']['review_action'] if 'review_action' in request.json[
                'item'] else ''

            incident.status = 'Peer Reviewed'
            # Create a revision using latest values
            # this method automatically commi
            #  incident changes (referenced)           
            incident.create_revision()
            # Record activity
            Activity.create(current_user, Activity.ACTION_UPDATE, incident.to_mini(), 'incident')
            return 'Buulletin review updated ... # {}'.format(incident.id), 200
        else:
            return 'Not Found!'

    else:
        return 'Unauthorized', 403


# bulk update incident endpoint
@roles_required(['Admin', 'DA'])
@admin.route('/api/incident/bulk/', methods=['PUT'])
def api_incident_bulk_update():
    """endpoint to handle bulk incidents updates."""
    if request.method == 'PUT':
        ids = request.json['items']
        bulk = request.json['bulk']
        if ids and len(bulk):
            job = bulk_update_incidents.delay(ids, bulk, current_user.id)
            # store job id in user's session for status monitoring
            key = 'user{}:{}'.format(current_user.id, job.id)
            rds.set(key, job.id)
            # expire in 3 hour
            rds.expire(key, 60 * 60 * 3)
            return '{}'.format('Bulk update queued successfully.'), 200
        else:
            return 'No items selected, or nothing to update', 417

    else:
        return 'Unauthorized', 403


@admin.route('/api/incident/<int:id>', methods=['DELETE'])
@roles_required('Admin')
def api_incident_delete(id):
    """endpoint handles deletion of incidents."""
    if request.method == 'DELETE':
        incident = Incident.query.get(id)
        incident.delete()

        # Record activity
        Activity.create(current_user, Activity.ACTION_DELETE, incident.to_mini(), 'incident')
        return 'Deleted !'


# get one incident

@admin.route('/api/incident/<int:id>', methods=['GET'])
def api_incident_get(id):
    """
    Endopint to get a single incident by id
    :param id: id of the incident item
    :return: successful incident item in json format or error
    """
    if request.method == 'GET':
        incident = Incident.query.get(id)
        if not incident:
            abort(404)
        else:
            return incident.to_json(), 200


@roles_required(['Admin', 'DA'])
@admin.route('/api/incident/import/', methods=['POST'])
def api_incident_import():
    """
    Endpoint to handle incident imports.
    :return: successful response or error code in case of failure.
    """
    if 'csv' in request.files:
        Incident.import_csv(request.files.get('csv'))
        return 'Success', 200
    else:
        return 'Error', 417


# Activity routes
@admin.route('/activity/')
@roles_required('Admin')
def activity():
    """
    Endpoint to render activity backend page
    :return: html of the page
    """
    return render_template('admin/activity.html')



@admin.route('/api/activity', methods=['POST', 'GET'])
@roles_required('Admin')
def api_activity():
    """
    API endpoint to feed activity items in json format, supports paging and filtering by tag
    :return: successful json feed or error
    """
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', PER_PAGE, int)
    query = []
    tag = request.json.get('tag',None)
    if tag:
        query.append(Activity.tag == tag)

    result = Activity.query.filter(
        *query).order_by(-Activity.id).paginate(
        page, per_page, True)
    response = {'items': [item.to_dict() for item in result.items], 'perPage': per_page, 'total': result.total}
    return Response(json.dumps(response),
                    content_type='application/json')


@admin.route('/api/bulk/status/')
def bulk_status():
    """Endpoint to get status update about background bulk operations"""
    uid = current_user.id
    cursor, jobs = rds.scan(0, 'user{}:*'.format(uid), 1000)
    tasks = []
    for key in jobs:
        result = {}
        id = key.split(':')[-1]
        type = request.args.get('type')
        if type == 'bulletin':
            status = bulk_update_bulletins.AsyncResult(id).status
        elif type == 'actor':
            status = bulk_update_incidents.AsyncResult(id).status
        elif type == 'incident':
            status = bulk_update_actors.AsyncResult(id).status
        else:
            abort(404)

        if status != 'SUCCESS':
            result['id'] = id
            result['status'] = status
            tasks.append(result)
        else:
            rds.delete(key)
    return json.dumps(tasks)

""" 
# Unused 
@roles_required('Admin')
@admin.route('/api/key/', methods=['POST'])
def gen_api_key():
    s = Settings.query.first()
    if not s:
        s = Settings().save()
    key = passlib.totp.generate_secret()
    s.api_key = key
    s.save()
    return key, 200


@roles_required(['Admin'])
@admin.route('/api/key/')
def get_api_key():
    return Settings.get_api_key(), 200

"""

# Saved Searches
@admin.route('/api/queries/')
def api_queries():
    """
    Endpoint to get user saved searches
    :return: successful json feed of saved searches or error
    """
    user_id = current_user.id
    queries = Query.query.filter(Query.user_id == user_id)
    return json.dumps([query.to_dict() for query in queries]), 200


@roles_required(['Admin', 'DA'])
@admin.route('/api/query/', methods=['POST'])
def api_query_create():
    """
    API Endpoint save a query search object (advanced search)
    :return: success if save is successful, error otherwise
    """
    q = request.json.get('q', None)

    name = request.json.get('name', None)
    if q and name:
        query = Query()
        query.name = name
        query.data = q
        query.user_id = current_user.id
        query.save()
        return 'Query successfully saved!', 200
    else:
        return 'Error parsing query data', 417
