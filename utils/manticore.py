import manticoresearch
from manticoresearch import SearchRequest
from manticoresearch.api import index_api
from manticoresearch.model.insert_document_request import InsertDocumentRequest
from pprint import pprint

configuration = manticoresearch.Configuration(
    host="http://manticore:9308"
)


def search(query, index="*"):
    with manticoresearch.ApiClient(configuration) as api_client:
        api_instance = manticoresearch.SearchApi(api_client)
        search_request = SearchRequest(
            index='posts',
            query={'query_string': query},
            source='post_id',
            highlight={'fields': ['title', 'text']}
        )

        try:
            # Perform a search
            api_response = api_instance.search(search_request)
            pprint(api_response)
        except manticoresearch.ApiException as e:
            print("Exception when calling SearchApi->search: %s\n" % e)


def equals(index, equals):
    with manticoresearch.ApiClient(configuration) as api_client:
        api_instance = manticoresearch.SearchApi(api_client)
        search_request = SearchRequest(
            index,
            query={'equals': equals}
        )

        try:
            # Perform a search
            api_response = api_instance.search(search_request)
            return api_response.hits
        except manticoresearch.ApiException as e:
            print("Exception when calling SearchApi->search: %s\n" % e)


def replace(index, data):
    with manticoresearch.ApiClient(configuration) as api_client:
        api_instance = index_api.IndexApi(api_client)

        try:
            exists = equals(index, type_id(index, data))
            if exists.total > 0:
                api_response = api_instance.replace(InsertDocumentRequest(
                    index=index,
                    id=exists.hits[0]['_id'],
                    doc=to_doc(index, data),
                ))
            else:
                api_response = api_instance.replace(InsertDocumentRequest(
                    index=index,
                    id=0,
                    doc=to_doc(index, data),
                ))

            return api_response

        except manticoresearch.ApiException as e:
            print("Exception when calling manticore: %s\n" % e)


def to_doc(index, data):
    if index == 'posts':
        return {
            'post_id': str(data.id),
            'title': data.title,
            'text': data.text,
        }


def type_id(index, data):
    if index == 'posts':
        return {"post_id": str(data.id)}


search('telegram')
