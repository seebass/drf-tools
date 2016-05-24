from collections import defaultdict
from datetime import datetime, date, time
import json
import random
from decimal import Decimal

from six.moves.urllib.parse import urlparse, urlencode, unquote, parse_qs
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.error import HTTPError

import logging

from django.core.urlresolvers import reverse
from django.db.models import Model
from django.test import TestCase
from enumfields import Enum

from drf_hal_json import LINKS_FIELD_NAME, EMBEDDED_FIELD_NAME, HAL_JSON_MEDIA_TYPE
import drf_nested_routing
from rest_framework.settings import api_settings

from drf_tools.test.utils import skip_abstract_test
from drf_tools.utils import DATETIME_FORMAT_ISO


class BaseRestTest(TestCase):
    _TESTSERVER_NAME = "testserver"
    _TESTSERVER_BASE_URL = "http://" + _TESTSERVER_NAME
    _COUNT_FIELD_NAME = "count"
    _PAGE_SIZE_FIELD_NAME = "page_size"
    _SELF_FIELD_NAME = api_settings.URL_FIELD_NAME
    _CONTENT_TYPE_HEADER_NAME = "Content-Type"
    _ALLOW_HEADER_NAME = "Allow"
    _LOCATION_HEADER_NAME = "Location"
    _QUERY_PARAM_FIELDS = "fields"
    _PARENT_LOOKUPS_MODEL_FIELD = "parent_lookups"

    def setUp(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        self.client.get("/api")  # hack: has to be called initial for router registration

    def _assertDatetimesEqual(self, datetime1, datetime2):
        if datetime1 and isinstance(datetime1, datetime):
            datetime1 = datetime1.strftime(DATETIME_FORMAT_ISO)
        if datetime2 and isinstance(datetime2, datetime):
            datetime2 = datetime2.strftime(DATETIME_FORMAT_ISO)
        self.assertEqual(datetime1, datetime2)

    def _assertDatesEqual(self, date1, date2):
        if date1 and isinstance(date1, date):
            date1 = date1.strftime('%Y-%m-%d')
        if date2 and isinstance(date2, date):
            date2 = date2.strftime('%Y-%m-%d')
        self.assertEqual(date1, date2)

    def _assertTimesEqual(self, time1, time2):
        if time1 and isinstance(time1, time):
            time1 = time1.strftime("%H:%M:%S")
        if time2 and isinstance(time2, time):
            time2 = time2.strftime("%H:%M:%S")
        self.assertEqual(time1, time2)

    def _doGETDetails(self, modelObj, queryParams=None, **headers):
        resp = self.client.get(self._getRelativeDetailURI(modelObj=modelObj), queryParams, **headers)
        self.assertEqual(resp[self._CONTENT_TYPE_HEADER_NAME], HAL_JSON_MEDIA_TYPE)
        return resp

    def _doGETList(self, modelClass, queryParams=None, parentLookups=None, **headers):
        resp = self.client.get(self._getRelativeListURI(modelClass, parentLookups), queryParams, **headers)
        self.assertEqual(resp[self._CONTENT_TYPE_HEADER_NAME], HAL_JSON_MEDIA_TYPE)
        return resp

    def _doPOST(self, modelClass, content, parentLookups=None, **headers):
        return self.client.post(self._getRelativeListURI(modelClass, parentLookups),
                                self.__contentToJson(content), HAL_JSON_MEDIA_TYPE, **headers)

    def _doPUT(self, modelObj, content, **headers):
        resp = self.client.put(self._getRelativeDetailURI(modelObj), self.__contentToJson(content),
                               HAL_JSON_MEDIA_TYPE, **headers)
        self.assertEqual(resp[self._CONTENT_TYPE_HEADER_NAME], HAL_JSON_MEDIA_TYPE)
        return resp

    def _doPATCH(self, modelObj, content, **headers):
        resp = self.client.patch(self._getRelativeDetailURI(modelObj), self.__contentToJson(content),
                                 HAL_JSON_MEDIA_TYPE, **headers)
        self.assertEqual(resp[self._CONTENT_TYPE_HEADER_NAME], HAL_JSON_MEDIA_TYPE)
        return resp

    def _doDELETE(self, modelObj, **headers):
        return self.client.delete(self._getRelativeDetailURI(modelObj), **headers)

    def _doOPTIONSList(self, modelClass, parentLookups=None, **headers):
        return self.client.options(self._getRelativeListURI(modelClass, parentLookups), **headers)

    def _doOPTIONSDetails(self, modelObj=None, **headers):
        return self.client.options(self._getRelativeDetailURI(modelObj), **headers)

    def _doHEADList(self, modelClass, parentLookups=None, **headers):
        return self.client.head(self._getRelativeListURI(modelClass, parentLookups), **headers)

    def _doHEADDetails(self, modelObj=None, **headers):
        return self.client.head(self._getRelativeDetailURI(modelObj), **headers)

    def _extractIdFromLocationHeader(self, locationHeader):
        return locationHeader.split("/")[-2]

    def _getAbsoluteDetailURI(self, modelObj):
        if not modelObj:
            return None
        return self._TESTSERVER_BASE_URL + self._getRelativeDetailURI(modelObj)

    def _getRelativeDetailURI(self, modelObj):
        if not modelObj:
            return None

        lookup_field = getattr(modelObj, "pk", None)
        kwargs = {"pk": lookup_field}
        parent_lookups = drf_nested_routing.get_parent_query_lookups_by_class(modelObj.__class__)
        if parent_lookups:
            for lookup in parent_lookups:
                lookup_path = lookup.split('__')
                parent_lookup = modelObj
                for part in lookup_path:
                    parent_lookup = getattr(parent_lookup, part)
                parentLookupId = parent_lookup.id if isinstance(parent_lookup, Model) else parent_lookup
                kwargs[drf_nested_routing.PARENT_LOOKUP_NAME_PREFIX + lookup] = parentLookupId

        # Handle unsaved object case
        if lookup_field is None:
            return None

        return reverse(modelObj.__class__.__name__.lower() + '-detail', kwargs=kwargs)

    def _getAbsoluteListURI(self, modelClass, parentLookups=None):
        return self._TESTSERVER_BASE_URL + self._getRelativeListURI(modelClass, parentLookups)

    def _getAbsoluteListURIByBaseViewName(self, baseViewName, parentLookups=None):
        return self._TESTSERVER_BASE_URL + self._getRelativeListURIByBaseViewName(baseViewName, parentLookups)

    def _getRelativeListURI(self, modelClass, parentLookups=None):
        return self._getRelativeListURIByBaseViewName(modelClass.__name__.lower(), parentLookups)

    def _getRelativeListURIByBaseViewName(self, baseViewName, parentLookups=None):
        parent_lookups = drf_nested_routing.get_parent_query_lookups_by_view(baseViewName)
        if parent_lookups and not parentLookups:
            raise ValueError("Please specify parent lookups for '{}'".format(baseViewName))

        composedParentLookups = dict()
        if parent_lookups and parentLookups:
            for lookup in parent_lookups:
                lookupId = parentLookups.get(lookup)
                if not lookupId:
                    continue
                composedParentLookups[drf_nested_routing.PARENT_LOOKUP_NAME_PREFIX + lookup] = lookupId

        return reverse(baseViewName + '-list', kwargs=composedParentLookups)

    def _assertLinksAndModelListEqual(self, linksList, modelList):
        if linksList is not None:
            self.assertEqual(len(linksList), len(modelList))
            for model in modelList:
                self.assertTrue(self._getAbsoluteDetailURI(model) in linksList)
        else:
            self.assertEqual(0, len(modelList))

    def __contentToJson(self, content):
        def decimal_default(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            raise obj

        return json.dumps(content, default=decimal_default)

    def _buildContent(self, stateAttrs, linkAttrs=None, embeddedAttrs=None):
        content = dict(stateAttrs)
        if linkAttrs:
            content[LINKS_FIELD_NAME] = linkAttrs
        if embeddedAttrs:
            content[EMBEDDED_FIELD_NAME] = embeddedAttrs
        return content

    def _splitContent(self, content):
        stateAttrs = {key: value for key, value in content.items() if
                      key not in (LINKS_FIELD_NAME, EMBEDDED_FIELD_NAME)}
        linkAttrs = content.get(LINKS_FIELD_NAME, dict())
        embeddedAttrs = content.get(EMBEDDED_FIELD_NAME, dict())
        return stateAttrs, linkAttrs, embeddedAttrs


class BaseModelViewSetTest(BaseRestTest):
    def _getModelClass(self):
        raise NotImplementedError()

    def _getOrCreateModelInstance(self):
        raise NotImplementedError()

    def _assertModelEqual(self, content, modelObj):
        raise NotImplementedError()

    def _getOrCreateModelList(self, minCount=5, maxCount=15):
        modelList = list()
        for i in range(random.randint(minCount, maxCount)):
            modelList.append(self._getOrCreateModelInstance())
        return modelList

    def _getAllowedListMethods(self):
        return ["OPTIONS"]

    def _getAllowedDetailsMethods(self):
        return ["OPTIONS"]

    @skip_abstract_test
    def testOPTIONSList(self):
        resp = self._doOPTIONSList(self._getModelClass(), self._getWildcardedParentLookups(self._getModelClass()))
        self.assertEqual(200, resp.status_code, resp.content)

        self.assertEqual(resp[self._CONTENT_TYPE_HEADER_NAME], HAL_JSON_MEDIA_TYPE)
        allowedMethods = [allowedMethod.strip() for allowedMethod in resp[self._ALLOW_HEADER_NAME].split(",")]
        for expectedAllowedMethod in self._getAllowedListMethods():
            self.assertTrue(expectedAllowedMethod in allowedMethods)

        self.assertTrue(HAL_JSON_MEDIA_TYPE in resp.data['renders'])
        self.assertTrue(HAL_JSON_MEDIA_TYPE in resp.data['parses'])

    @skip_abstract_test
    def testOPTIONSDetails(self):
        resp = self._doOPTIONSDetails(self._getOrCreateModelInstance())
        self.assertEqual(200, resp.status_code, resp.content)

        self.assertEqual(resp[self._CONTENT_TYPE_HEADER_NAME], HAL_JSON_MEDIA_TYPE)
        allowedMethods = [allowedMethod.strip() for allowedMethod in resp[self._ALLOW_HEADER_NAME].split(",")]
        for expectedAllowedMethod in self._getAllowedDetailsMethods():
            self.assertTrue(expectedAllowedMethod in allowedMethods)

        self.assertTrue(HAL_JSON_MEDIA_TYPE in resp.data['renders'])
        self.assertTrue(HAL_JSON_MEDIA_TYPE in resp.data['parses'])

    @skip_abstract_test
    def testHEADList(self):
        resp = self._doHEADList(self._getModelClass(), self._getWildcardedParentLookups(self._getModelClass()))
        self.assertEqual(405, resp.status_code, resp.content)

    @skip_abstract_test
    def testHEADDetails(self):
        resp = self._doHEADDetails(self._getOrCreateModelInstance())
        self.assertEqual(405, resp.status_code, resp.content)

    @skip_abstract_test
    def testGETList(self):
        resp = self._doGETList(self._getModelClass(), self._getWildcardedParentLookups(self._getModelClass()))
        self.assertEqual(405, resp.status_code, resp.content)

    @skip_abstract_test
    def testGETDetails(self):
        resp = self._doGETDetails(self._getOrCreateModelInstance())
        self.assertEqual(405, resp.status_code, resp.content)

    @skip_abstract_test
    def testPUT(self):
        resp = self._doPUT(self._getOrCreateModelInstance(), {})
        self.assertEqual(405, resp.status_code, resp.content)

    @skip_abstract_test
    def testPATCH(self):
        resp = self._doPATCH(self._getOrCreateModelInstance(), {})
        self.assertEqual(405, resp.status_code, resp.content)

    @skip_abstract_test
    def testPOST(self):
        resp = self._doPOST(self._getModelClass(), {}, parentLookups=self._getWildcardedParentLookups(self._getModelClass()))
        self.assertEqual(405, resp.status_code, resp.content)

    @skip_abstract_test
    def testDELETE(self):
        resp = self._doDELETE(self._getOrCreateModelInstance())
        self.assertEqual(405, resp.status_code, resp.content)

    def _getWildcardedParentLookups(self, modelClass):
        parentLookups = drf_nested_routing.get_parent_query_lookups_by_class(modelClass)
        if not parentLookups:
            return None
        return {parentLookup: "*" for parentLookup in parentLookups}


class CreateModelViewSetTest(BaseModelViewSetTest):
    def _getAllowedListMethods(self):
        return super(CreateModelViewSetTest, self)._getAllowedListMethods() + ["POST"]

    def _createModelAsJson(self):
        raise NotImplementedError()

    @skip_abstract_test
    def testPOST(self):
        content, parentLookups = self._createModelAsJson()
        resp = self._doPOST(self._getModelClass(), content, parentLookups)
        self.assertEqual(201, resp.status_code, resp.content)
        objectFromDb = self._getModelClass().objects.get(
            id=self._extractIdFromLocationHeader(resp[self._LOCATION_HEADER_NAME]))
        self._assertModelEqual(content, objectFromDb)


class ReadModelViewSetTest(BaseModelViewSetTest):
    def _getAllowedListMethods(self):
        return super(ReadModelViewSetTest, self)._getAllowedListMethods() + ["GET", "HEAD"]

    def _getAllowedDetailsMethods(self):
        return super(ReadModelViewSetTest, self)._getAllowedDetailsMethods() + ["GET", "HEAD"]

    @skip_abstract_test
    def testHEADList(self):
        resp = self._doHEADList(self._getModelClass(), self._getWildcardedParentLookups(self._getModelClass()))
        self.assertEqual(200, resp.status_code, resp.content)

    @skip_abstract_test
    def testHEADDetails(self):
        resp = self._doHEADDetails(self._getOrCreateModelInstance())
        self.assertEqual(200, resp.status_code, resp.content)

    @skip_abstract_test
    def testGETList(self):
        modelList = self._getOrCreateModelList()
        modelCount = len(modelList)
        queryParams = {self._PAGE_SIZE_FIELD_NAME: modelCount}
        modelsByUrl = {self._getAbsoluteDetailURI(model): model for model in modelList}
        wildCardedParentLookups = self._getWildcardedParentLookups(self._getModelClass())
        resp = self._doGETList(self._getModelClass(), queryParams, wildCardedParentLookups)
        self.assertEqual(200, resp.status_code, resp.content)
        stateAttrs, linkAttrs, embeddedAttrs = self._splitContent(resp.data)
        self.assertEqual(stateAttrs[self._COUNT_FIELD_NAME], modelCount)
        self.assertEqual(stateAttrs[self._PAGE_SIZE_FIELD_NAME], modelCount)
        self.assertEqual(linkAttrs[self._SELF_FIELD_NAME], "{}?{}={}".format(
            unquote(self._getAbsoluteListURI(self._getModelClass(), wildCardedParentLookups)),
            self._PAGE_SIZE_FIELD_NAME, modelCount))
        self.assertEqual(len(embeddedAttrs), modelCount)
        for embeddedAttr in embeddedAttrs:
            model = modelsByUrl[embeddedAttr[LINKS_FIELD_NAME][self._SELF_FIELD_NAME]]
            self._assertModelEqual(embeddedAttr, model)

    @skip_abstract_test
    def testGETDetails(self):
        modelObj = self._getOrCreateModelInstance()
        resp = self._doGETDetails(modelObj)
        self.assertEqual(200, resp.status_code, resp.content)
        self._assertModelEqual(resp.data, modelObj)


class IncludeFields:
    def __init__(self, stateFields=None, linkFields=None, embeddedFields=None):
        self.__stateFields = stateFields or []
        self.__linkFields = linkFields or []
        self.__embeddedFields = embeddedFields or {}

    def buildQueryParamValue(self):
        fields = self.__stateFields + self.__linkFields
        for embeddedAttr, includeFields in self.__embeddedFields.items():
            fields.append("{}.fields({})".format(embeddedAttr, includeFields.buildQueryParamValue()))
        return ",".join(fields)

    def getResultingStateFields(self):
        return self.__stateFields + ['id']

    def getResultingLinkFields(self):
        return self.__linkFields + ['self']

    def getResultingEmbeddedFields(self):
        return self.__embeddedFields


class AdvancedReadModelViewSetTestMixin(ReadModelViewSetTest):
    def _getIncludeFields(self):
        raise NotImplementedError()

    @skip_abstract_test
    def testGETListPaginated(self):
        def __getPageParams(url):
            pr = urlparse(url)
            params = {k: v[0] for k, v in parse_qs(pr.query).items()}
            location = "{scheme}://{netloc}{path}".format(scheme=pr.scheme, netloc=pr.netloc, path=pr.path)
            pageNumber = int(params['page']) if 'page' in params else 1
            return location, int(params[self._PAGE_SIZE_FIELD_NAME]), pageNumber

        specifiedPageSize = 5
        modelList = self._getOrCreateModelList()

        pageCount = len(modelList) // specifiedPageSize
        rest = len(modelList) % specifiedPageSize
        if rest != 0:
            pageCount += 1

        for i in range(pageCount):
            queryParams = {'page': i + 1, self._PAGE_SIZE_FIELD_NAME: specifiedPageSize}
            wildcardedParentLookups = self._getWildcardedParentLookups(self._getModelClass())
            resp = self._doGETList(self._getModelClass(), queryParams, wildcardedParentLookups)
            path, pageSize, page = __getPageParams(resp.data[LINKS_FIELD_NAME][self._SELF_FIELD_NAME])
            expectedPath = "{}{}".format(self._TESTSERVER_BASE_URL, unquote(
                self._getRelativeListURI(self._getModelClass(), wildcardedParentLookups)))
            self.assertEqual(expectedPath, path)
            self.assertEqual(page, i + 1)
            self.assertEqual(pageSize, 5)
            self.assertEqual(len(modelList), resp.data[self._COUNT_FIELD_NAME])
            self.assertEqual(5, resp.data[self._PAGE_SIZE_FIELD_NAME])
            embeddedCount = pageSize
            if rest != 0 and i == pageCount - 1:
                embeddedCount = rest
            self.assertEqual(embeddedCount, len(resp.data[EMBEDDED_FIELD_NAME]))

            if i != pageCount - 1:
                path, pageSize, page = __getPageParams(resp.data[LINKS_FIELD_NAME]['next'])
                self.assertEqual(expectedPath, path)
                self.assertEqual(5, pageSize)
                self.assertEqual(i + 2, page)
            if i > 0:
                path, pageSize, page = __getPageParams(resp.data[LINKS_FIELD_NAME]['previous'])
                self.assertEqual(expectedPath, path)
                self.assertEqual(5, pageSize)
                self.assertEqual(i, page)

    @skip_abstract_test
    def testGETListIncludeCertainFields(self):
        modelList = self._getOrCreateModelList()
        modelsByUrl = {self._getAbsoluteDetailURI(model): model for model in modelList}
        includeFields = self._getIncludeFields()
        fieldsQueryParamValue = includeFields.buildQueryParamValue()

        modelCount = len(modelList)
        queryParams = {self._PAGE_SIZE_FIELD_NAME: modelCount, self._QUERY_PARAM_FIELDS: fieldsQueryParamValue}
        wildcardedParentLookups = self._getWildcardedParentLookups(self._getModelClass())
        resp = self._doGETList(self._getModelClass(), queryParams, wildcardedParentLookups)
        self.assertEqual(200, resp.status_code, resp.content)
        stateAttrs, linkAttrs, embeddedAttrs = self._splitContent(resp.data)

        self.assertEqual(stateAttrs[self._COUNT_FIELD_NAME], modelCount)
        self.assertEqual(stateAttrs[self._PAGE_SIZE_FIELD_NAME], modelCount)
        selfUrl = unquote(linkAttrs[self._SELF_FIELD_NAME])
        self.assertTrue(
            selfUrl.startswith(unquote(self._getAbsoluteListURI(self._getModelClass(), wildcardedParentLookups))))
        self.assertTrue("{}={}".format(self._QUERY_PARAM_FIELDS, fieldsQueryParamValue) in selfUrl)
        self.assertTrue("{}={}".format(self._PAGE_SIZE_FIELD_NAME, modelCount) in selfUrl)
        self.assertEqual(modelCount, len(embeddedAttrs))

        for embeddedObjectAttrs in embeddedAttrs:
            modelObj = modelsByUrl[embeddedObjectAttrs[LINKS_FIELD_NAME][self._SELF_FIELD_NAME]]
            self.assertIsNotNone(modelObj)
            self.__assertIncludeFieldsContentEqual(includeFields, modelObj, embeddedObjectAttrs)

    @skip_abstract_test
    def testGETDetailsIncludeCertainFields(self):
        modelObj = self._getOrCreateModelInstance()
        includeFields = self._getIncludeFields()
        fieldsQueryParamValue = includeFields.buildQueryParamValue()

        resp = self._doGETDetails(modelObj, {self._QUERY_PARAM_FIELDS: fieldsQueryParamValue})
        self.assertEqual(200, resp.status_code, resp.data)
        self.__assertIncludeFieldsContentEqual(includeFields, modelObj, resp.data)

    def __assertIncludeFieldsContentEqual(self, includeFields, modelObj, content):
        stateAttrs, linkAttrs, embeddedAttrs = self._splitContent(content)

        self.assertEqual(len(includeFields.getResultingStateFields()), len(stateAttrs))
        self.assertEqual(modelObj.id, stateAttrs['id'])
        self.assertEqual(len(includeFields.getResultingLinkFields()), len(linkAttrs))
        self.assertEqual(len(includeFields.getResultingEmbeddedFields()), len(embeddedAttrs))

        for stateField in includeFields.getResultingStateFields():
            if stateField in stateAttrs:
                modelValue = getattr(modelObj, stateField)
                if isinstance(modelValue, Enum):
                    modelValue = modelValue.value
                if isinstance(modelValue, datetime):
                    self._assertDatetimesEqual(modelValue, stateAttrs[stateField])
                    continue
                if isinstance(modelValue, date):
                    self._assertDatesEqual(modelValue, stateAttrs[stateField])
                    continue
                self.assertEqual(modelValue, stateAttrs[stateField])

        for linkField in includeFields.getResultingLinkFields():
            if linkField in linkAttrs:
                if linkField == self._SELF_FIELD_NAME:
                    ref = modelObj
                else:
                    ref = getattr(modelObj, linkField)
                self.assertEqual(self._getAbsoluteDetailURI(ref), linkAttrs[linkField])

        for embeddedField, embeddedIncludeFields in includeFields.getResultingEmbeddedFields().items():
            if embeddedField in embeddedAttrs:
                if isinstance(embeddedAttrs[embeddedField], dict):
                    embeddedObj = getattr(modelObj, embeddedField)
                    self.__assertIncludeFieldsContentEqual(embeddedIncludeFields, embeddedObj,
                                                           embeddedAttrs[embeddedField])
                else:
                    embeddedList = getattr(modelObj, embeddedField).all()
                    modelsByUrl = {self._getAbsoluteDetailURI(model): model for model in embeddedList}
                    for embeddedAttr in embeddedAttrs[embeddedField]:
                        embeddedObj = modelsByUrl[embeddedAttr[LINKS_FIELD_NAME][self._SELF_FIELD_NAME]]
                        self.__assertIncludeFieldsContentEqual(embeddedIncludeFields, embeddedObj, embeddedAttr)


class UpdateModelViewSetTest(BaseModelViewSetTest):
    def _getUpdateAttributes(self):
        raise NotImplementedError()

    def _getAllowedDetailsMethods(self):
        return super(UpdateModelViewSetTest, self)._getAllowedDetailsMethods() + ["PATCH", "PUT"]

    @skip_abstract_test
    def testPUT(self):
        modelObj = self._getOrCreateModelInstance()
        resp = self._doGETDetails(modelObj)
        self.assertEqual(200, resp.status_code, resp.data)
        content = dict(resp.data)

        for changeAttr, value in self._getUpdateAttributes().items():
            if changeAttr in content:
                content[changeAttr] = value
            elif changeAttr in content[LINKS_FIELD_NAME]:
                content[LINKS_FIELD_NAME][changeAttr] = value
            else:
                raise ValueError("Attribute '{}' not available.".format(changeAttr))

        resp = self._doPUT(modelObj, content)
        self.assertEqual(200, resp.status_code, resp.data)
        objectFromDb = modelObj.__class__.objects.get(id=modelObj.id)
        self._assertModelEqual(content, objectFromDb)

    @skip_abstract_test
    def testPATCH(self):
        modelObj = self._getOrCreateModelInstance()
        resp = self._doGETDetails(modelObj)
        self.assertEqual(200, resp.status_code, resp.data)
        content = dict(resp.data)
        patchData = defaultdict(dict)
        for changeAttr, value in self._getUpdateAttributes().items():
            if changeAttr in content:
                content[changeAttr] = value
                patchData[changeAttr] = value
            elif changeAttr in content[LINKS_FIELD_NAME]:
                content[LINKS_FIELD_NAME][changeAttr] = value
                patchData[LINKS_FIELD_NAME][changeAttr] = value
            else:
                raise ValueError("Attribute '{}' not available.".format(changeAttr))

        resp = self._doPATCH(modelObj, patchData)
        self.assertEqual(200, resp.status_code, resp.content)
        objectFromDb = modelObj.__class__.objects.get(id=modelObj.id)
        self._assertModelEqual(content, objectFromDb)


class DeleteModelViewSetTest(BaseModelViewSetTest):
    def _getAllowedDetailsMethods(self):
        return super(DeleteModelViewSetTest, self)._getAllowedDetailsMethods() + ["DELETE"]

    @skip_abstract_test
    def testDELETE(self):
        modelObj = self._getOrCreateModelInstance()
        self.assertTrue(modelObj.__class__.objects.filter(id=modelObj.id).exists())
        resp = self._doDELETE(modelObj)
        self.assertEqual(204, resp.status_code, resp.content)
        self.assertFalse(modelObj.__class__.objects.filter(id=modelObj.id).exists())


class ModelViewSetTest(CreateModelViewSetTest, ReadModelViewSetTest, UpdateModelViewSetTest, DeleteModelViewSetTest,
                       BaseModelViewSetTest):
    pass
