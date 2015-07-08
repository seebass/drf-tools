import drf_hal_json
from drf_tools.test.base import IncludeFields, ModelViewSetTest, AdvancedReadModelViewSetTestMixin, BaseRestTest

from .models import TestResource, RelatedResource1, RelatedResource2


class TestResourceViewSetTest(AdvancedReadModelViewSetTestMixin, ModelViewSetTest):
    def setUp(self):
        super(TestResourceViewSetTest, self).setUp()
        self.nameCt = 0

    def _getModelClass(self):
        return TestResource

    def _getOrCreateModelInstance(self):
        self.nameCt += 1
        return TestResource.objects.create(name="resource_{}".format(self.nameCt))

    def _createModelAsJson(self):
        stateAttrs = {
            "name": "test-resource",
        }
        linkAttrs = {}
        return self._buildContent(stateAttrs, linkAttrs), None

    def _assertModelEqual(self, content, testResource):
        stateAttrs, linkAttrs, embeddedAttrs = self._splitContent(content)

        self.assertEqual(stateAttrs.get('name'), testResource.name)

        if self._SELF_FIELD_NAME in content:
            self.assertEqual(linkAttrs[self._SELF_FIELD_NAME], self._getAbsoluteDetailURI(testResource))

    def _getUpdateAttributes(self):
        return {"name": "new_name"}

    def _getIncludeFields(self):
        return IncludeFields(["name"])


class RelatedResource1ViewSetTest(AdvancedReadModelViewSetTestMixin, ModelViewSetTest):
    def setUp(self):
        super(RelatedResource1ViewSetTest, self).setUp()
        self.nameCt = 0

    def _getModelClass(self):
        return RelatedResource1

    def _getOrCreateModelInstance(self):
        self.nameCt += 1
        resource = TestResource.objects.create(name="resource_{}".format(self.nameCt))
        return RelatedResource1.objects.create(name="relatedresource1_{}".format(self.nameCt), resource=resource)

    def _createModelAsJson(self):
        testResource = TestResource.objects.create(name="test-resource")
        stateAttrs = {
            "name": "related-resource1",
            "active": True,
        }
        linkAttrs = {
            "resource": self._getAbsoluteDetailURI(testResource)
        }
        parentLookups = {
            "resource": testResource.id
        }
        return self._buildContent(stateAttrs, linkAttrs), parentLookups

    def _assertModelEqual(self, content, relatedResource1):
        stateAttrs, linkAttrs, embeddedAttrs = self._splitContent(content)

        self.assertEqual(stateAttrs.get('name'), relatedResource1.name)
        self.assertEqual(stateAttrs.get('active'), relatedResource1.active)

        if self._SELF_FIELD_NAME in content:
            self.assertEqual(linkAttrs[self._SELF_FIELD_NAME], self._getAbsoluteDetailURI(relatedResource1))
            self.assertEqual(linkAttrs["resource"], self._getAbsoluteDetailURI(relatedResource1.resource))

    def _getUpdateAttributes(self):
        return {"name": "new_name"}

    def _getIncludeFields(self):
        return IncludeFields(["name"], [], {"resource": IncludeFields(["name"])})


class RelatedResource2ViewSetTest(AdvancedReadModelViewSetTestMixin, ModelViewSetTest):
    def setUp(self):
        super(RelatedResource2ViewSetTest, self).setUp()
        self.nameCt = 0

    def _getModelClass(self):
        return RelatedResource2

    def _getOrCreateModelInstance(self):
        self.nameCt += 1
        resource1 = TestResource.objects.create(name="resource1_{}".format(self.nameCt))
        resource2 = TestResource.objects.create(name="resource2_{}".format(self.nameCt))
        nestedRelatedResource11 = RelatedResource1.objects.create(name="nestedrelatedresource11_{}".format(self.nameCt),
                                                                  resource=resource2)
        resource3 = TestResource.objects.create(name="resource3_{}".format(self.nameCt))
        nestedRelatedResource12 = RelatedResource1.objects.create(name="nestedrelatedresource12_{}".format(self.nameCt),
                                                                  resource=resource3)
        relatedResource2 = RelatedResource2.objects.create(name="relatedresource2_{}".format(self.nameCt), resource=resource1)
        relatedResource2.related_resources_1.add(nestedRelatedResource11, nestedRelatedResource12)
        return relatedResource2

    def _createModelAsJson(self):
        resource1 = TestResource.objects.create(name="resource1")
        resource2 = TestResource.objects.create(name="resource2")
        nestedRelatedResource11 = RelatedResource1.objects.create(name="nestedrelatedresource11", resource=resource2)
        resource3 = TestResource.objects.create(name="resource3")
        nestedRelatedResource12 = RelatedResource1.objects.create(name="nestedrelatedresource12", resource=resource3)
        stateAttrs = {
            "name": "related-resource2",
            "active": False,
        }
        linkAttrs = {
            "related_resources_1": [self._getAbsoluteDetailURI(nestedRelatedResource11),
                                    self._getAbsoluteDetailURI(nestedRelatedResource12)]
        }
        parentLookups = {
            "resource": resource1.id
        }
        return self._buildContent(stateAttrs, linkAttrs), parentLookups

    def _assertModelEqual(self, content, relatedResource2):
        stateAttrs, linkAttrs, embeddedAttrs = self._splitContent(content)

        self.assertEqual(stateAttrs.get('name'), relatedResource2.name)
        self.assertEqual(stateAttrs.get('active'), relatedResource2.active)

        if self._SELF_FIELD_NAME in content:
            self.assertEqual(linkAttrs[self._SELF_FIELD_NAME], self._getAbsoluteDetailURI(relatedResource2))
            self._assertLinksAndModelListEqual(linkAttrs["related_resources_1"], relatedResource2.related_resources_1)
            self.assertEqual(linkAttrs["resource"], self._getAbsoluteDetailURI(relatedResource2.resource))

    def _getUpdateAttributes(self):
        return {"name": "new_name"}

    def _getIncludeFields(self):
        return IncludeFields(["name"], ["resource"], {"related_resources_1": IncludeFields(["name"])})


class ApiRootTest(BaseRestTest):
    def testGetApiRoot(self):
        resp = self.client.get("/")
        print(resp.data)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(resp.data))
        self.assertEqual(2, len(resp.data[drf_hal_json.LINKS_FIELD_NAME]))
        self.assertTrue(len(resp.data[drf_hal_json.LINKS_FIELD_NAME]['viewsets']) > 0)
        self.assertTrue(len(resp.data[drf_hal_json.LINKS_FIELD_NAME]['views']) == 0)
