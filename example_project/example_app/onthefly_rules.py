# -*- coding: utf-8 -*-

from datetime import datetime

from carrier_pigeon.facility import add_item_to_push
from carrier_pigeon.validators import wellformed_xml_validator
from carrier_pigeon.configuration import SequentialPusherConfiguration
from carrier_pigeon.supervisors import BaseSupervisor
from carrier_pigeon.output_makers import TemplateOutputMaker, BinaryOutputMaker

from example_app.models import Story, Photo


class BPPhotoSupervisor(BaseSupervisor):

    def filter_by_instance_type(self, instance):
        return instance._meta.object_name == 'Photo'

    def filter_by_updates(self, instance):
        # We want all the photos in the queue
        return True

    def filter_by_state(self, instance):
        # We want all the photos in the queue
        return True

    @property
    def relative_final_directory(self):
        # Local directory in the working dir of pigeon
        return 'medias'

    @property
    def final_file_name(self, instance):
        return "%d.jpg" % instance.pk

    def get_output_makers(self):
        return [BinaryOutputMaker(self.configuration, self.instance, "original_file")]


class BPStoryOutputMaker(TemplateOutputMaker):

    validators = (wellformed_xml_validator,)

    def get_extra_context(self):
        read_also = Story.objects.all()[:3]  # Yes, ugly :)
        return {"read_also": read_also,}

    @property
    def final_file_name(self):
        return 'NEWS_%s_%d.xml' % (self.instance._meta.app_label.lower(), self.instance.pk)


class BPStorySupervisor(BaseSupervisor):

    def filter_by_instance_type(self, instance):
        return instance.__class__ == Story

    def filter_by_updates(self, instance):
        # Candidates are Story that have these fields modified at current save
        to_check = ["workflow_state", "updating_date"]
        if any(field in instance._modified_attrs for field in to_check):
            return True
        return False

    def filter_by_state(self, instance):
        # WARNING : put the lightest tests before

        # We only want online stories
        if not instance.workflow_state == instance.WORKFLOW_STATE.ONLINE:
            return False

        # Minimum length of text is 500
        if len(instance.content) < 500:
            return False
        return True

    def get_output_makers(self):
        return [BPStoryOutputMaker(self.configuration, self.instance)]

    def get_related_items(self, item):
        return [item.photo]


class BelovedPartner(SequentialPusherConfiguration):
    """
    Configuration for the exports to BelovedPartner.
    """
    
    def get_supervisor_for_item(self, item):
        if item.__class__ == Story:
            return BPStorySupervisor(self, item)
        elif item.__class__ == Photo:
            return BPPhotoSupervisor(self, item)
        else:
            ValueError("No supervisor found for class %s" % item.__class__)

