import time
import logging

from block import Block
from protocols.consensus_protocol import ConsensusProtocol

class PBFTProtocol(ConsensusProtocol):
    def __init__(self, node, blockchain):
        self.node = node
        self.node_id = self.node.id

        self.prepare_counts = {}
        self.commit_counts = {}

        self.blockchain = blockchain

    def handle_message(self, message):
        message_type = message.get("type")

        if message_type == "request":
            self.request(message["content"])
            return 

        if message["id"] not in self.node.peers: 
            return  

        public_key = self.node.peers[message["id"]]["public_key"]
        msg = {"type": message["type"], "content": message["content"]}
        is_valid_signature = self.node.verify_signature(message["signature"], msg, public_key)

        if not is_valid_signature: 
            logging.warning("Not valid signature: %s", message)
            return 

        logging.info("Valid signature: %s", is_valid_signature)    

        if message_type == "pre-prepare":
            response = self.pre_prepare(message["content"])
        elif message_type == "prepare":
            response = self.prepare(message["content"])
        elif message_type == "commit":
            response = self.commit(message['id'],message["content"])
        else:
            logging.warning("Unknown message type: %s", message_type)

        return response

    def request(self, content):
        block = self.create_block_from_request(content)
        message = {"type": "pre-prepare", "content": block.to_dict()}
        self.node.broadcast_message(message)

        return "requested"

    def pre_prepare(self, message):
        logging.info("Node %s received pre-prepare for block: \n%s", self.node_id, message)

        block = Block(message["index"], message["model_type"], message["storage_reference"], message["calculated_hash"], message["previous_hash"])

        self.prepare_counts[message["current_hash"]] = 0

        message = {"type": "prepare", "content": block.to_dict()}
        self.node.broadcast_message(message)

        return "pre-prepared"

    def prepare(self, message):
        logging.info("Node %s received prepare for block %s", self.node_id, message)
        block_hash = message["current_hash"]
        if block_hash not in self.prepare_counts: 
            self.prepare_counts[block_hash] = 0
        self.prepare_counts[block_hash] += 1

        if self.is_prepared(block_hash): 
            commit_message = {"type": "commit", "content": message}
            self.node.broadcast_message(commit_message)
            logging.info("Node %s prepared block to %s", self.node_id, self.node.peers)
            return "prepared"
        else:
            logging.info("Node %s waiting for more prepares for block %s", self.node_id, block_hash)
            return "waiting"

    def commit(self, sender, message):
        logging.info("Node %s received commit for block %s", self.node_id, message)
        block_hash = message["current_hash"]

        if block_hash not in self.commit_counts: 
            self.commit_counts[block_hash] = {"count": 0, "senders": []}

        if sender not in self.commit_counts[block_hash]["senders"]: 
            self.commit_counts[block_hash]["count"] += 1
            self.commit_counts[block_hash]["senders"].append(sender)

        if self.can_commit(block_hash):
            logging.info("Node %s committing block %s", self.node_id, block_hash)

            if self.validate_block(message):
                block = Block(
                    message["index"], 
                    message["model_type"],
                    message["storage_reference"], 
                    message["calculated_hash"], 
                    message["previous_hash"]
                )

                self.blockchain.add_block(block)

                logging.info("Node %s committed block %s", self.node_id, block_hash)

                return "added"
            else:
                logging.warning("Invalid block. Discarding commit")
                return "invalid"
        else:
            logging.info("Node %s waiting for more commits for block %s", self.node_id, block_hash)
            return "waiting"

    def validate_block(self, block_data):
        # Vérifiez l'intégrité du bloc
        if "index" not in block_data or "model_type" not in block_data or "storage_reference" not in block_data \
            or "calculated_hash" not in block_data or "previous_hash" not in block_data:
            return False

        # Vérifiez que l'index est correctement incrémenté
        if block_data["index"] != len(self.blockchain.blocks):
            return False

        # Vérifiez la validité du hachage précédent
        previous_block = self.blockchain.blocks[-1] if self.blockchain.blocks else None
        if previous_block and block_data["previous_hash"] != previous_block.current_hash:
            return False
        
        # if block_data["model_type"] == "update": 
        #     return self.node.is_update_usefull(block_data["storage_reference"])
        
        # if block_data["index"] > 2 and block_data["model_type"] == "global_model": 
        #     return self.node.is_global_valid(block_data["calculated_hash"])
        
        return True

    def create_block_from_request(self, content):
        previous_blocks = self.blockchain.blocks
        index_of_new_block = len(previous_blocks)
        model_type = content.get("model_type")
        storage_reference = content.get("storage_reference")
        calculated_hash = content.get("calculated_hash")
        previous_hash_of_last_block = previous_blocks[-1].current_hash

        # Créez un nouveau bloc à partir de la demande du client
        new_block = Block(index_of_new_block, model_type, storage_reference, calculated_hash, previous_hash_of_last_block)

        return new_block
    
    def is_prepared(self, id):
        return self.prepare_counts[id] >= 1

    def can_commit(self, id):
        return self.commit_counts[id]["count"] >= 2

