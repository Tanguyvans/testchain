# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: block.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0b\x62lock.proto\"\x8c\x01\n\x0c\x42lockMessage\x12\r\n\x05nonce\x18\x01 \x01(\t\x12\x15\n\rprevious_hash\x18\x02 \x01(\t\x12\x0c\n\x04hash\x18\x03 \x01(\t\x12\x17\n\x0f\x63\x61lculated_hash\x18\x04 \x01(\t\x12\x19\n\x11storage_reference\x18\x05 \x01(\t\x12\x14\n\x0c\x62lock_number\x18\x06 \x01(\x05\",\n\x08Response\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t23\n\x0bNodeService\x12$\n\x08\x41\x64\x64\x42lock\x12\r.BlockMessage\x1a\t.Responseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'block_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _globals['_BLOCKMESSAGE']._serialized_start=16
  _globals['_BLOCKMESSAGE']._serialized_end=156
  _globals['_RESPONSE']._serialized_start=158
  _globals['_RESPONSE']._serialized_end=202
  _globals['_NODESERVICE']._serialized_start=204
  _globals['_NODESERVICE']._serialized_end=255
# @@protoc_insertion_point(module_scope)