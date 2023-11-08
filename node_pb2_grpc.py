# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import node_pb2 as node__pb2


class NodeServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.AddWeightsFromClient = channel.unary_unary(
                '/NodeService/AddWeightsFromClient',
                request_serializer=node__pb2.ClientMessage.SerializeToString,
                response_deserializer=node__pb2.NodeResponse.FromString,
                )
        self.AddBlockRequest = channel.unary_unary(
                '/NodeService/AddBlockRequest',
                request_serializer=node__pb2.BlockMessage.SerializeToString,
                response_deserializer=node__pb2.BlockResponse.FromString,
                )
        self.AddBlockToChain = channel.unary_unary(
                '/NodeService/AddBlockToChain',
                request_serializer=node__pb2.BlockValidation.SerializeToString,
                response_deserializer=node__pb2.ValidationResponse.FromString,
                )


class NodeServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def AddWeightsFromClient(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def AddBlockRequest(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def AddBlockToChain(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_NodeServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'AddWeightsFromClient': grpc.unary_unary_rpc_method_handler(
                    servicer.AddWeightsFromClient,
                    request_deserializer=node__pb2.ClientMessage.FromString,
                    response_serializer=node__pb2.NodeResponse.SerializeToString,
            ),
            'AddBlockRequest': grpc.unary_unary_rpc_method_handler(
                    servicer.AddBlockRequest,
                    request_deserializer=node__pb2.BlockMessage.FromString,
                    response_serializer=node__pb2.BlockResponse.SerializeToString,
            ),
            'AddBlockToChain': grpc.unary_unary_rpc_method_handler(
                    servicer.AddBlockToChain,
                    request_deserializer=node__pb2.BlockValidation.FromString,
                    response_serializer=node__pb2.ValidationResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'NodeService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class NodeService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def AddWeightsFromClient(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/NodeService/AddWeightsFromClient',
            node__pb2.ClientMessage.SerializeToString,
            node__pb2.NodeResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def AddBlockRequest(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/NodeService/AddBlockRequest',
            node__pb2.BlockMessage.SerializeToString,
            node__pb2.BlockResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def AddBlockToChain(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/NodeService/AddBlockToChain',
            node__pb2.BlockValidation.SerializeToString,
            node__pb2.ValidationResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
