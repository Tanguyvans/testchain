# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: node.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\nnode.proto\"\xa0\x01\n\x0c\x42lockMessage\x12\r\n\x05nonce\x18\x01 \x01(\t\x12\x15\n\rprevious_hash\x18\x02 \x01(\t\x12\x0c\n\x04hash\x18\x03 \x01(\t\x12\x17\n\x0f\x63\x61lculated_hash\x18\x04 \x01(\t\x12\x12\n\nmodel_type\x18\x05 \x01(\t\x12\x19\n\x11storage_reference\x18\x06 \x01(\t\x12\x14\n\x0c\x62lock_number\x18\x07 \x01(\x05\"1\n\rBlockResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\" \n\x0f\x42lockValidation\x12\r\n\x05valid\x18\x01 \x01(\x08\"%\n\x12ValidationResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\"I\n\rClientMessage\x12\r\n\x05value\x18\x01 \x01(\x0c\x12\x16\n\x0e\x64\x61taset_number\x18\x02 \x01(\x05\x12\x11\n\tclient_id\x18\x03 \x01(\t\"\x1f\n\x0cNodeResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x32\xb0\x01\n\x0bNodeService\x12\x35\n\x14\x41\x64\x64WeightsFromClient\x12\x0e.ClientMessage\x1a\r.NodeResponse\x12\x30\n\x0f\x41\x64\x64\x42lockRequest\x12\r.BlockMessage\x1a\x0e.BlockResponse\x12\x38\n\x0f\x41\x64\x64\x42lockToChain\x12\x10.BlockValidation\x1a\x13.ValidationResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'node_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_BLOCKMESSAGE']._serialized_start=15
  _globals['_BLOCKMESSAGE']._serialized_end=175
  _globals['_BLOCKRESPONSE']._serialized_start=177
  _globals['_BLOCKRESPONSE']._serialized_end=226
  _globals['_BLOCKVALIDATION']._serialized_start=228
  _globals['_BLOCKVALIDATION']._serialized_end=260
  _globals['_VALIDATIONRESPONSE']._serialized_start=262
  _globals['_VALIDATIONRESPONSE']._serialized_end=299
  _globals['_CLIENTMESSAGE']._serialized_start=301
  _globals['_CLIENTMESSAGE']._serialized_end=374
  _globals['_NODERESPONSE']._serialized_start=376
  _globals['_NODERESPONSE']._serialized_end=407
  _globals['_NODESERVICE']._serialized_start=410
  _globals['_NODESERVICE']._serialized_end=586
# @@protoc_insertion_point(module_scope)
