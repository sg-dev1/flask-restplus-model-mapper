"""
Small Domain Mapper testing app
"""
import logging
from flask import Flask, request
from flask_restplus import Api, Resource

from domain_mapper import DomainMapper

app = Flask(__name__)
api = Api(app)
m = DomainMapper(api)

# configure logging
format_str = "[%(levelname)7s: %(asctime)s] %(message)s"
logging.basicConfig(format=format_str, datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
LOG = logging.getLogger(__name__)

#
# Test Domain Classes
#
class TestItem(object):
    def __init__(self, string=None, int_=None, float_=None, bool_=None):
        """
        :param string: A test string
        :param int_: A test integer
        :param float_: A test float
        :param bool_: A test boolean
        """
        self.string = string
        self.int_ = int_ 
        self.float_ = float_
        self.bool_ = bool_

    def _extra_str(self):
        return ""

    def __repr__(self):
        return "[%s] string=%s, int_=%s, float_=%s, bool_=%s%s" % \
            (self.__class__.__name__, self.string, self.int_, self.float_, self.bool_, self._extra_str())

class InheritedTestItem(TestItem):
    def __init__(self, str_lst=None, int_lst=None, **kwargs):
        super().__init__(**kwargs)
        self.str_lst = str_lst
        self.int_lst = int_lst

    def _extra_str(self):
        return ", str_lst=%s, int_lst=%s" % (self.str_lst, self.int_lst)

class TestComposition(object):
    def __init__(self, test_item=None, test_inherited_item=None):
        self.test_item = test_item
        self.test_inherited_item = test_inherited_item

    def _extra_str(self):
        return ""

    def __repr__(self):
        return "[%s] test_item=%s, test_inherited_item=%s%s" % (self.__class__.__name__, self.test_item, self.test_inherited_item, self._extra_str())

class DerivedComplexTestComposition(TestComposition):
    def __init__(self, test_item_lst=None, **kwargs):
        super().__init__(**kwargs)
        self.test_item_lst = test_item_lst

    def _extra_str(self):
        return ", test_item_lst=%s" % self.test_item_lst

#
# Register the Domain Classes with the DomainMapper
#
testItem = TestItem(string="hello world", int_=12, float_=0.15, bool_=False)
inheritedTestItem = InheritedTestItem(string="hello world", int_=12, float_=0.15, bool_=False, str_lst=["a", "b"], int_lst=[1, 2])
testCompostion = TestComposition(test_item=testItem, test_inherited_item=inheritedTestItem)
derivedComplexTestComposition = DerivedComplexTestComposition(test_item=testItem, test_inherited_item=inheritedTestItem, test_item_lst=[testItem])

m.register(testItem, required_lst=["string"])
m.register(inheritedTestItem)
m.register(testCompostion)
m.register(derivedComplexTestComposition)

#
# Some Test REST interfaces
#
@api.route('/testItem')
class HelloTestItem(Resource):
    @api.marshal_with(m.get_flask_restplus_schema(TestItem))
    def get(self):
        """
        GET test endpoint.
        """
        return TestItem(string="world", int_=1, float_=2.454535, bool_=True)

    @api.expect(m.get_flask_restplus_schema(TestItem))
    def post(self):
        """
        POST test endpoint
        """
        obj = m.parse_data(TestItem, request.get_json())
        LOG.info("test post: %s" % obj)

@api.route("/testInheritedItem")
class HelloInheritedTestItem(Resource):
    @api.marshal_with(m.get_flask_restplus_schema(InheritedTestItem))
    def get(self):
        return InheritedTestItem(string="hello world", int_=12, float_=0.15, bool_=False, str_lst=["a", "b"], int_lst=[1, 2])

    @api.expect(m.get_flask_restplus_schema(InheritedTestItem))
    def post(self):
        obj = m.parse_data(InheritedTestItem, request.get_json())
        LOG.info("test post: %s" % obj)

@api.route("/testComposition")
class HelloTestComposition(Resource):
    @api.marshal_with(m.get_flask_restplus_schema(TestComposition))
    def get(self):
        return TestComposition(test_item=TestItem(string="world", int_=1, float_=2.454535, bool_=True),
                               test_inherited_item=InheritedTestItem(string="hello world", int_=12, float_=0.15, bool_=False, str_lst=["a", "b"], int_lst=[1, 2]))

    @api.expect(m.get_flask_restplus_schema(TestComposition))
    def post(self):
        obj = m.parse_data(TestComposition, request.get_json())
        LOG.info("test post: %s" % obj)

@api.route("/testDerivedComplexComposition")
class HelloDerivedComplexTestComposition(Resource):
    @api.marshal_with(m.get_flask_restplus_schema(DerivedComplexTestComposition))
    def get(self):
        return DerivedComplexTestComposition(
                    test_item=TestItem(string="world", int_=1, float_=2.454535, bool_=True),
                    test_inherited_item=InheritedTestItem(string="hello world", int_=12, float_=0.15, bool_=False, str_lst=["a", "b"], int_lst=[1, 2]),
                    test_item_lst=[TestItem(string="world ...", int_=1345345, float_=2.4545893453945834535, bool_=False)])

    @api.expect(m.get_flask_restplus_schema(DerivedComplexTestComposition))
    def post(self):
        obj = m.parse_data(DerivedComplexTestComposition, request.get_json())
        LOG.info("test post: %s" % obj)
        LOG.info("obj.test_item_lst[0].string: %s" % obj.test_item_lst[0].string)

if __name__ == '__main__':
    app.run(debug=True)
