from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtNetwork import QNetworkReply
from . import blockchain, network, node, tx, wot, ConnectionHandler
from .....tools.exceptions import NoPeerAvailable
import logging
import json
import asyncio
import random

class BmaAccess(QObject):
    '''
    This class is used to access BMA API.
    '''

    __saved_requests = [str(blockchain.Block), str(blockchain.Parameters)]

    def __init__(self, data, network):
        """
        Constructor of a network

        :param dict data: The data present in this cache
        :param cutecoin.core.net.network.Network network: The network used to connect
        """
        super().__init__()
        self._data = data
        self._pending_requests = {}
        self._network = network

    @classmethod
    def create(cls, network):
        '''
        Initialize a new BMAAccess object with empty data.

        :param cutecoin.core.net.network.Network network:
        :return: A new BmaAccess object
        :rtype: cutecoin.core.net.api.bma.access.BmaAccess
        '''
        return cls({}, network)

    @property
    def data(self):
        return self._data.copy()

    def load_from_json(self, json_data):
        '''
        Put data in the cache from json datas.

        :param dict data: The cache in json format
        '''
        data = {}
        for entry in json_data:
            key = entry['key']
            cache_key = (key[0], key[1], key[2], key[3], key[4])
            data[cache_key] = entry['value']
        self._data = data

    def jsonify(self):
        '''
        Get the cache in json format

        :return: The cache as a dict in json format
        '''
        data = {k: self._data[k] for k in self._data.keys()}
        entries = []
        for d in data:
            entries.append({'key': d,
                            'value': data[d]})
        return entries

    @staticmethod
    def _gen_cache_key(request, req_args, get_args):
        return (str(request),
                     str(tuple(frozenset(sorted(req_args.keys())))),
                     str(tuple(frozenset(sorted(req_args.values())))),
                     str(tuple(frozenset(sorted(get_args.keys())))),
                     str(tuple(frozenset(sorted(get_args.values())))))

    def _compare_json(self, first, second):
        """
        Compare two json dicts
        :param first: the first dictionnary
        :param second: the second dictionnary
        :return: True if the json dicts are the same
        :rtype: bool
        """
        if first is not None:
            if not isinstance(first, type(second)):
                return False
        if isinstance(first, dict):
            for key in first:
                if isinstance(second, dict):
                    if second.has_key(key):
                        sec = second[key]
                    else:
                        #  there are key in the first, that is not presented in the second
                        return False
                    # recursive call
                    return self._compare_json(first[key], sec)
                else:
                    # second is not dict
                    return False
        # if object is list, loop over it and check.
        elif isinstance(first, list):
            for (index, item) in enumerate(first):
                # try to get the same index from second
                sec = None
                if second is not None:
                    try:
                        sec = second[index]
                    except (IndexError, KeyError):
                        # goes to difference
                        return False
                # recursive call
                return self._compare_json(first[index], sec)
        # not list, not dict. check for equality
        elif first != second:
                return False
        else:
            return True

    def _get_from_cache(self, request, req_args, get_args):
        """
        Get data from the cache
        :param request: The requested data
        :param cache_key: The key
        :return:
        """
        cache_key = BmaAccess._gen_cache_key(request, req_args, get_args)
        if cache_key in self._data.keys():
            need_reload = False
            if 'metadata' in self._data[cache_key]:
                if str(request) not in BmaAccess.__saved_requests \
                   and self._data[cache_key]['metadata']['block'] < self._network.latest_block:
                    need_reload = True
            else:
                need_reload = True
            ret_data = self._data[cache_key]['value']
        else:
            need_reload = True
            ret_data = request.null_value
        return need_reload, ret_data

    def _update_cache(self, request, req_args, get_args, data):
        """
        Update data in cache and returns True if cached data changed
        :param class request: A bma request class calling for data
        :param dict req_args: Arguments to pass to the request constructor
        :param dict get_args: Arguments to pass to the request __get__ method
        :param dict data: Json data to save in cache
        :return: True if data changed
        :rtype: bool
        """
        cache_key = BmaAccess._gen_cache_key(request, req_args, get_args)
        if cache_key not in self._data:
            self._data[cache_key] = {}

            if 'metadata' not in self._data[cache_key]:
                self._data[cache_key]['metadata'] = {}

            if 'value' not in self._data[cache_key]:
                self._data[cache_key]['value'] = {}
            self._data[cache_key]['metadata']['block'] = self._network.latest_block

            if not self._compare_json(self._data[cache_key]['value'], data):
                self._data[cache_key]['value'] = data
                return True
        return False

    def get(self, caller, request, req_args={}, get_args={}, tries=0):
        """
        Get Json data from the specified URL and emit "inner_data_changed"
        on the caller if the data changed.

        :param PyQt5.QtCore.QObject caller: The objet calling
        :param class request: A bma request class calling for data
        :param dict req_args: Arguments to pass to the request constructor
        :param dict get_args: Arguments to pass to the request __get__ method
        :return: The cached data
        :rtype: dict
        """
        data = self._get_from_cache(request, req_args, get_args)
        need_reload = data[0]
        ret_data = data[1]
        cache_key = BmaAccess._gen_cache_key(request, req_args, get_args)

        if need_reload:
            #Move to network nstead of community
            #after removing qthreads
            if cache_key in self._pending_requests:
                if caller not in self._pending_requests[cache_key]:
                    logging.debug("New caller".format(caller))
                    self._pending_requests[cache_key].append(caller)
                    logging.debug("Callers".format(self._pending_requests[cache_key]))
            else:
                reply = self.simple_request(request, req_args, get_args)
                logging.debug("New pending request {0}, caller {1}".format(cache_key, caller))
                self._pending_requests[cache_key] = [caller]
                reply.finished.connect(lambda: self.handle_reply(request, req_args, get_args, tries))
        return ret_data

    @pyqtSlot(int, dict, dict, int)
    def handle_reply(self, request, req_args, get_args, tries):
        reply = self.sender()
        logging.debug("Handling QtNetworkReply for {0}".format(str(request)))
        cache_key = BmaAccess._gen_cache_key(request, req_args, get_args)

        if reply.error() == QNetworkReply.NoError:
            strdata = bytes(reply.readAll()).decode('utf-8')
            json_data = json.loads(strdata)
            # If data changed, we emit a change signal to all callers
            if self._update_cache(request, req_args, get_args, json_data):
                logging.debug(self._pending_requests.keys())
                for caller in self._pending_requests[cache_key]:
                    logging.debug("Emit change for {0} : {1} ".format(caller, request))
                    caller.inner_data_changed.emit(str(request))
            self._pending_requests.pop(cache_key)
        else:
            logging.debug("Error in reply : {0}".format(reply.error()))
            if tries < 3:
                tries += 1
                try:
                    pending_request = self._pending_requests.pop(cache_key)
                    for caller in pending_request:
                        self.get(caller, request, req_args, get_args, tries=tries)
                except KeyError:
                    logging.debug("{0} is not present anymore in pending requests".format(cache_key))

    def future_request(self, request, req_args={}, get_args={}):
        '''
        Start a request to the network and returns a future.

        :param class request: A bma request class calling for data
        :param dict req_args: Arguments to pass to the request constructor
        :param dict get_args: Arguments to pass to the request __get__ method
        :return: The future data
        :rtype: dict
        '''
        def handle_future_reply(reply):
            if reply.error() == QNetworkReply.NoError:
                strdata = bytes(reply.readAll()).decode('utf-8')
                json_data = json.loads(strdata)
                self._update_cache(request, req_args, get_args, json_data)
                future_data.set_result(json_data)
            else:
                future_data.set_result(request.null_value)

        future_data = asyncio.Future()
        data = self._get_from_cache(request, req_args, get_args)
        need_reload = data[0]

        if need_reload:
            nodes = self._network.synced_nodes
            if len(nodes) > 0:
                node = random.choice(nodes)
                server = node.endpoint.conn_handler().server
                port = node.endpoint.conn_handler().port
                conn_handler = ConnectionHandler(self._network.network_manager, server, port)
                req = request(conn_handler, **req_args)
                reply = req.get(**get_args)
                reply.finished.connect(lambda: handle_future_reply(reply))
            else:
                raise NoPeerAvailable(self.currency, len(nodes))
        else:
            future_data.set_result(data[1])
        return future_data

    def simple_request(self, request, req_args={}, get_args={}):
        '''
        Start a request to the network but don't cache its result.

        :param class request: A bma request class calling for data
        :param dict req_args: Arguments to pass to the request constructor
        :param dict get_args: Arguments to pass to the request __get__ method
        :return: The returned data if cached = True else return the QNetworkReply
        '''
        nodes = self._network.synced_nodes
        if len(nodes) > 0:
            node = random.choice(nodes)
            server = node.endpoint.conn_handler().server
            port = node.endpoint.conn_handler().port
            conn_handler = ConnectionHandler(self._network.network_manager, server, port)
            req = request(conn_handler, **req_args)
            reply = req.get(**get_args)
            return reply
        else:
            raise NoPeerAvailable(self.currency, len(nodes))

    def broadcast(self, request, req_args={}, post_args={}):
        '''
        Broadcast data to a network.
        Sends the data to all knew nodes.

        :param request: A ucoinpy bma request class
        :param req_args: Arguments to pass to the request constructor
        :param post_args: Arguments to pass to the request __post__ method
        :return: All nodes replies
        :rtype: tuple of QNetworkReply

        .. note:: If one node accept the requests (returns 200),
        the broadcast should be considered accepted by the network.
        '''
        nodes = self._network.online_nodes
        replies = []
        for node in nodes:
            logging.debug("Trying to connect to : " + node.pubkey)
            server = node.endpoint.conn_handler().server
            port = node.endpoint.conn_handler().port
            conn_handler = ConnectionHandler(self._network.network_manager, server, port)
            req = request(conn_handler, **req_args)
            reply = req.post(**post_args)
            replies.append(reply)
        return tuple(replies)