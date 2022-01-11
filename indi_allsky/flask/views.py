from datetime import datetime
from datetime import timedelta
import re

from flask import render_template
from flask import request
from flask import jsonify
from flask import Blueprint
from flask.views import View

from flask import current_app as app  # noqa

from . import db

from .models import IndiAllSkyDbCameraTable
from .models import IndiAllSkyDbImageTable

from sqlalchemy import func

from .forms import IndiAllskyConfigForm


bp = Blueprint('indi-allsky', __name__, template_folder='templates', url_prefix='/')


#@bp.route('/')
#@bp.route('/index')
#def index():
#    return render_template('index.html')


class TemplateView(View):
    def __init__(self, template_name):
        self.template_name = template_name

    def dispatch_request(self):
        return render_template(self.template_name)


class ListView(View):
    def __init__(self, template_name):
        self.template_name = template_name

    def render_template(self, context):
        return render_template(self.template_name, **context)

    def dispatch_request(self):
        context = {'objects': self.get_objects()}
        return self.render_template(context)

    def get_objects(self):
        raise NotImplementedError()


class FormView(ListView):
    def dispatch_request(self):
        context = self.get_objects()
        return self.render_template(context)


class JsonView(View):
    def dispatch_request(self):
        json_data = self.get_objects()
        return jsonify(json_data)

    def get_objects(self):
        raise NotImplementedError()



class IndexView(TemplateView):
    pass


class CamerasView(ListView):
    def get_objects(self):
        cameras = IndiAllSkyDbCameraTable.query.all()
        return cameras


class ImageLoopView(TemplateView):
    pass


class JsonImageLoopView(JsonView):
    def __init__(self):
        self.camera_id = self.getLatestCamera()
        self.limit = 40
        self.hours = 2
        self.sqm_history_minutes = 30
        self.stars_history_minutes = 30
        self.rootpath = '/var/www/html/allsky/'


    def get_objects(self):
        self.limit = request.args.get('limit', self.limit)

        data = {
            'image_list' : self.getLatestImages(),
            'sqm_data'   : self.getSqmData(),
            'stars_data' : self.getStarsData(),
        }

        return data


    def getLatestCamera(self):
        latest_camera = IndiAllSkyDbCameraTable.query\
            .order_by(IndiAllSkyDbCameraTable.connectDate.desc())\
            .first()

        return latest_camera.id


    def getLatestImages(self):
        now_minus_hours = datetime.now() - timedelta(hours=self.hours)

        latest_images = IndiAllSkyDbImageTable.query\
            .join(IndiAllSkyDbImageTable.camera)\
            .filter(IndiAllSkyDbCameraTable.id == self.camera_id)\
            .filter(IndiAllSkyDbImageTable.createDate > now_minus_hours)\
            .order_by(IndiAllSkyDbImageTable.createDate.desc())\
            .limit(self.limit)

        image_list = list()
        for i in latest_images:
            rel_filename = re.sub(r'^{0:s}'.format(self.rootpath), '', i.filename)

            data = {
                'file'  : rel_filename,
                'sqm'   : i.sqm,
                'stars' : i.stars,
            }

            image_list.append(data)

        return image_list


    def getSqmData(self):
        now_minus_minutes = datetime.now() - timedelta(minutes=self.sqm_history_minutes)

        sqm_images = db.session\
            .query(
                func.max(IndiAllSkyDbImageTable.sqm).label('image_max_sqm'),
                func.min(IndiAllSkyDbImageTable.sqm).label('image_min_sqm'),
                func.avg(IndiAllSkyDbImageTable.sqm).label('image_avg_sqm'),
            )\
            .join(IndiAllSkyDbImageTable.camera)\
            .filter(IndiAllSkyDbCameraTable.id == self.camera_id)\
            .filter(IndiAllSkyDbImageTable.createDate > now_minus_minutes)\
            .first()


        sqm_data = {
            'max' : sqm_images.image_max_sqm,
            'min' : sqm_images.image_min_sqm,
            'avg' : sqm_images.image_avg_sqm,
        }

        return sqm_data


    def getStarsData(self):
        now_minus_minutes = datetime.now() - timedelta(minutes=self.stars_history_minutes)

        stars_images = db.session\
            .query(
                func.max(IndiAllSkyDbImageTable.stars).label('image_max_stars'),
                func.min(IndiAllSkyDbImageTable.stars).label('image_min_stars'),
                func.avg(IndiAllSkyDbImageTable.stars).label('image_avg_stars'),
            )\
            .join(IndiAllSkyDbImageTable.camera)\
            .filter(IndiAllSkyDbCameraTable.id == self.camera_id)\
            .filter(IndiAllSkyDbImageTable.createDate > now_minus_minutes)\
            .first()


        stars_data = {
            'max' : stars_images.image_max_stars,
            'min' : stars_images.image_min_stars,
            'avg' : stars_images.image_avg_stars,
        }

        return stars_data


class ConfigView(FormView):
    def get_objects(self):
        objects = {
            'form_config' : IndiAllskyConfigForm(),
        }

        return objects


bp.add_url_rule('/', view_func=IndexView.as_view('index_view', template_name='index.html'))
bp.add_url_rule('/cameras', view_func=CamerasView.as_view('cameras_view', template_name='cameras.html'))
bp.add_url_rule('/config', view_func=ConfigView.as_view('config_view', template_name='config.html'))
bp.add_url_rule('/loop', view_func=ImageLoopView.as_view('image_loop_view', template_name='loop.html'))
bp.add_url_rule('/js/loop', view_func=JsonImageLoopView.as_view('js_image_loop_view'))
