"""
Domain Mapper main module
"""
import logging

import flask_restplus as flaskrp
import marshmallow as mm

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


TO_FLASKRP_MAPPING = {
    # Types.RAW: flaskrp.fields.Raw,
    "str": flaskrp.fields.String,
    "int": flaskrp.fields.Integer,
    "float": flaskrp.fields.Float,
    "bool": flaskrp.fields.Boolean,
    "date": flaskrp.fields.Date,
    "datetime": flaskrp.fields.DateTime,
}

TO_MM_MAPPING = {
    # Types.RAW: mm.fields.Raw,
    "str": mm.fields.String,
    "int": mm.fields.Integer,
    "float": mm.fields.Float,
    "bool": mm.fields.Boolean,
    "date": mm.fields.Date,
    "datetime": mm.fields.DateTime,
}

class MappingError(Exception):
    """
    A MappingError which is thrown in case of error in the DomainMapper
    """
    def __init__(self, msg):
        """
        :param msg: The error message
        """
        self.msg = msg

class DomainMapper(object):
    """
    The main class for mapping domain objects onto flask restplus and marshmallow schemas.
    """
    def __init__(self, flaskrp_api):
        self.api = flaskrp_api
        self.flaskrp_mapping = {}
        self.mm_mapping = {}

    def _parse_doc_string(self, domain_obj):
        doc_string = domain_obj.__class__.__init__.__doc__
        if not doc_string:
            return {}
        lines = doc_string.replace("\t", "").strip().split("\n")
        param_to_desc_map = {}
        for line in lines:
            tmp = line.split(":")
            if len(tmp) != 3:
                LOG.info("Lenght was %d != 3. Skipping line '%s'" % (len(tmp), line))
                continue
            key = tmp[1].strip()
            val = tmp[2].strip()
            LOG.debug("Saving key=%s, val=%s" % (key, val))
            param_to_desc_map[key] = val
        return param_to_desc_map

    def register(self, domain_obj, required_lst=[]):
        """
        Registers a new domain object with this DomainMapper.
        :param domain_obj: The domain object to register
        """
        flaskrp_dict = {}
        mm_dict = {}
        param_to_desc_map = self._parse_doc_string(domain_obj)
        for key, val in domain_obj.__dict__.items():
            description = None
            if key in param_to_desc_map:
                description = param_to_desc_map[key]
                LOG.info("Found description %s" % description)
            if type(val).__name__ == "list":
                # handle specially
                if len(val) == 0:
                    raise MappingError("Empty list not supported. Can't determine type of elements")
                list_element = val[0]
                if not all([isinstance(elem, type(list_element)) for elem in val]):
                    raise MappingError("Lists must have all elements with same type: %s" % val)
                
                if type(list_element).__name__ in TO_FLASKRP_MAPPING:
                    # primitive type
                    flaskrp_dict[key] = flaskrp.fields.List(cls_or_instance=TO_FLASKRP_MAPPING[type(list_element).__name__], example=val, required=key in required_lst)
                    mm_dict[key] = mm.fields.List(TO_MM_MAPPING[type(list_element).__name__], required=key in required_lst)
                elif type(list_element).__name__ in self.flaskrp_mapping:
                    # complex nested type
                    flaskrp_dict[key] = flaskrp.fields.List(flaskrp.fields.Nested(self.flaskrp_mapping[type(list_element).__name__]), required=key in required_lst)
                    mm_dict[key] = mm.fields.Nested(self.mm_mapping[type(list_element).__name__], many=True, required=key in required_lst)
                else:
                    raise MappingError("Can't find %s either in primitive type mapping or in registered type mappings" % type(list_element).__name__)
                
            else:
                if type(val).__name__ in TO_FLASKRP_MAPPING:
                    flaskrp_dict[key] = TO_FLASKRP_MAPPING[type(val).__name__](example=val, description=description, required=key in required_lst)
                    mm_dict[key] = TO_MM_MAPPING[type(val).__name__](required=key in required_lst)
                elif type(val).__name__ in self.flaskrp_mapping:
                    # complex nested type
                    flaskrp_dict[key] = flaskrp.fields.Nested(self.flaskrp_mapping[type(val).__name__], required=key in required_lst)
                    mm_dict[key] = mm.fields.Nested(self.mm_mapping[type(val).__name__], required=key in required_lst)
                else:
                   raise MappingError("Can't find %s either in primitive type mapping or in registered type mappings" % type(val).__name__)

        # convert python dictionaries to Domain Objects
        @mm.post_load
        def make_object(self, data):
            return domain_obj.__class__(**data)
        mm_dict["make_object"] = make_object

        # check for inheritance
        bases = domain_obj.__class__.__bases__
        if len(bases) > 1:
            raise MappingError("Multi inheritance not supported (%s)" % bases)
        assert(len(bases) == 1)
        if bases[0].__name__ != "object":
            flaskrp_model = self.api.clone(domain_obj.__class__.__name__, self.flaskrp_mapping[bases[0].__name__], flaskrp_dict)
            mm_schema = type(domain_obj.__class__.__name__, (self.mm_mapping[bases[0].__name__],), mm_dict)
        else:
            # no inheritance
            flaskrp_model = self.api.model(domain_obj.__class__.__name__, flaskrp_dict)
            mm_schema = type(domain_obj.__class__.__name__, (mm.Schema,), mm_dict)

        # save the flask restplus model and the marshmallow schema class object for later use
        self.flaskrp_mapping[domain_obj.__class__.__name__] = flaskrp_model
        self.mm_mapping[domain_obj.__class__.__name__] = mm_schema

    def get_flask_restplus_schema(self, domain_class):
        """
        Get a flask restplus schema for a DomainClass object.
        :param domain_class: The domain_class for which the flask_restplus schema should be retrieved
        """
        if domain_class.__name__ not in self.flaskrp_mapping:
            raise MappingError("Flask Restplus schema %s not found" % domain_class.__name__)
        return self.flaskrp_mapping[domain_class.__name__]

    def _get_marshmallow_schema(self, domain_class):
        if domain_class.__name__ not in self.mm_mapping:
            raise MappingError("Marshmallow schema %s not found" % domain_class.__name__)
        return self.mm_mapping[domain_class.__name__]

    def parse_data(self, domain_class, json_data):
        """
        Parses json_data for a given domain_class using its marshmallow schema
        which was added in register.
        :param domain_class: The domain_class for which the data should be parsed
        :param json_data: The data which should be parsed
        :return: A newly created domain_object in case of success. A 400 error is returned in case of error.
        """
        mm_schema = self._get_marshmallow_schema(domain_class)
        data, errors = mm_schema().load(json_data)
        if errors:
            LOG.error("Validation error: %s" % errors)
            self.api.abort(400, "Validation error: %s" % errors)
        return data
