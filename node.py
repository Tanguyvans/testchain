import socket
import threading
import json
import os
import time
import base64
import random

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

import concurrent.futures
import hashlib
import numpy as np
from block import Block
from blockchain import Blockchain
from flowerclient import FlowerClient
import pickle

from flwr.server.strategy.aggregate import aggregate
from sklearn.model_selection import train_test_split

from protocols.pbft_protocol import PBFTProtocol
from protocols.raft_protocol import RaftProtocol

class Node:
    def __init__(self, id, host, port, consensus_protocol, batch_size, train, test, coef_usefull=1.1):
        self.id = id
        self.host = host
        self.port = port
        self.coef_usefull = coef_usefull

        self.peers = {}
        self.clients = {}
        self.clusters = []
        self.cluster_weights = []

        self.global_params_directory = ""

        private_key_path = f"keys/{id}_private_key.pem"
        public_key_path = f"keys/{id}_public_key.pem"
        self.getKeys(private_key_path, public_key_path)

        X_train, y_train = train
        X_test, y_test = test
        X_train,X_val,y_train,y_val=train_test_split(X_train,y_train,test_size=0.2,random_state=42,stratify=y_train)
        self.flower_client = FlowerClient(batch_size, X_train, X_val ,X_test, y_train, y_val, y_test)

        self.blockchain = Blockchain()
        if consensus_protocol == "pbft": 
            self.consensus_protocol = PBFTProtocol(node=self, blockchain=self.blockchain)
        elif consensus_protocol == "raft": 
            self.consensus_protocol = RaftProtocol(node=self, blockchain=self.blockchain)
            threading.Thread(target=self.consensus_protocol.run).start()

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Node {self.id} listening on {self.host}:{self.port}")

        while True:
            client_socket, addr = server_socket.accept()
            threading.Thread(target=self.handle_message, args=(client_socket,)).start()

    def handle_message(self, client_socket):

        data_length = int.from_bytes(client_socket.recv(4), byteorder='big')
        data = client_socket.recv(data_length)
        
        message = pickle.loads(data)

        message_type = message.get("type")

        if message_type == "frag_weights": 
            message_id = message.get("id")
            weights = pickle.loads(message.get("value"))
            for pos, cluster in enumerate(self.clusters): 
                if message_id in cluster: 
                    if cluster[message_id] == 0: 
                        self.cluster_weights[pos].append(weights)
                        cluster[message_id] = 1
                        cluster["count"] += 1

                    if cluster["count"] == cluster["tot"]:  
                        aggregated_weights = self.aggregation_cluster(pos) 
                        message = self.create_update_request(aggregated_weights)

                        self.consensus_protocol.handle_message(message)
                    
        else: 
            result = self.consensus_protocol.handle_message(message)

            if result == "added":
                block = self.blockchain.blocks[-1] 
                model_type = block.model_type

                if model_type == "update": 
                    nb_updates = 0
                    for block in self.blockchain.blocks[::-1]: 
                        if block.model_type == "update": 
                            nb_updates += 1
                        else: 
                            break 

                elif model_type == "global_model": 
                    self.broadcast_model_to_clients()

        client_socket.close()

    def is_update_usefull(self, model_directory): 
        global_model_directory = ""
        for block in self.blockchain.blocks[::-1]: 
            if block.model_type == "global_model": 
                global_model_directory = block.storage_reference
                break

        if self.evaluateModel(model_directory)[0] <= self.evaluateModel(global_model_directory)[0]*self.coef_usefull: 
            return True
        else: 
            return False

    def is_global_valid(self, proposed_hash):
        params_list = []
        for block in self.blockchain.blocks[::-1]: 
            if block.model_type == "update": 
                loaded_weights_dict = np.load(block.storage_reference)
                loaded_weights = [loaded_weights_dict[f'param_{i}'] for i in range(len(loaded_weights_dict)-1)]

                loaded_weights = (loaded_weights, loaded_weights_dict[f'len_dataset'])
                params_list.append(loaded_weights)
            else: 
                break 

        self.aggregated_params = aggregate(params_list)
        self.flower_client.set_parameters(self.aggregated_params)

        weights_dict = self.flower_client.get_dict_params({})
        weights_dict['len_dataset'] = 10

        filename = f"models/{self.id}temp.npz"

        with open(filename, "wb") as f:
            np.savez(f, **weights_dict)

        if proposed_hash == self.calculate_model_hash(filename): 
            return True 
        else:
            return False

    def evaluateModel(self, model_directory):
        loaded_weights_dict = np.load(model_directory)
        loaded_weights = [loaded_weights_dict[f'param_{i}'] for i in range(len(loaded_weights_dict)-1)]
        loss = self.flower_client.evaluate(loaded_weights, {})[0]
        acc = self.flower_client.evaluate(loaded_weights, {})[2]['accuracy']

        return loss, acc

    def broadcast_model_to_clients(self):
        for block in self.blockchain.blocks[::-1]: 
            if block.model_type == "global_model":
                block_model = block 
                break 

        loaded_weights_dict = np.load(block_model.storage_reference)
        loaded_weights = [loaded_weights_dict[f'param_{i}'] for i in range(len(loaded_weights_dict)-1)]

        for k,v in self.clients.items():
            address = v.get('address')

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(('127.0.0.1', address[1]))

            serialized_data = pickle.dumps(loaded_weights)
            message = {"type": "global_model", "value": serialized_data}

            serialized_message = pickle.dumps(message)

            # Send the length of the message first
            client_socket.send(len(serialized_message).to_bytes(4, byteorder='big'))
            client_socket.send(serialized_message)

            # Fermer le socket après l'envoi
            client_socket.close()

    def broadcast_message(self, message):
        for peer_id in self.peers:
            self.send_message(peer_id, message)

    def send_message(self, peer_id, message):
        if peer_id in self.peers:
            peer_info = self.peers[peer_id]
            peer_address = peer_info["address"]

            signed_message = message.copy()
            signed_message["signature"] = self.sign_message(signed_message)
            signed_message["id"] = self.id

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                    client_socket.connect(peer_address)

                    serialized_message = pickle.dumps(signed_message)

                    # Envoyer la longueur du message en premier
                    client_socket.send(len(serialized_message).to_bytes(4, byteorder='big'))
                    client_socket.send(serialized_message)

            except ConnectionRefusedError:
                pass
            except Exception as e:
                pass
        else:
            print(f"Peer {peer_id} not found.")

    def calculate_model_hash(self, filename): 
        loaded_weights_dict = np.load(filename)
        loaded_weights = [loaded_weights_dict[f'param_{i}'] for i in range(len(loaded_weights_dict)-1)]
        loaded_weights = (loaded_weights, loaded_weights_dict[f'len_dataset'])

        hash_model = hashlib.sha256()
        hash_model.update(str(loaded_weights).encode('utf-8'))
        hash_model = hash_model.hexdigest()

        return hash_model
   
    def create_first_global_model_request(self): 
        old_params = self.flower_client.get_parameters({})
        len_dataset = self.flower_client.fit(old_params, {})[1]

        weights_dict = self.flower_client.get_dict_params({})
        weights_dict['len_dataset'] = len_dataset
        model_type = "global_model"
        
        filename = f"models/m0.npz"
        self.global_params_directory = filename

        with open(filename, "wb") as f:
            np.savez(f, **weights_dict)

        message = {
            "id": self.id,
            "type": "request", 
            "content": {
                "storage_reference": filename,
                "model_type": model_type,
                "calculated_hash": self.calculate_model_hash(filename)
            }
        }

        self.consensus_protocol.handle_message(message)

    def create_global_model(self): 
        params_list = []
        for block in self.blockchain.blocks[::-1]: 
            if block.model_type == "update": 
                loaded_weights_dict = np.load(block.storage_reference)
                loaded_weights = [loaded_weights_dict[f'param_{i}'] for i in range(len(loaded_weights_dict)-1)]

                loaded_weights = (loaded_weights, loaded_weights_dict[f'len_dataset'])
                params_list.append(loaded_weights)
            else: 
                break 

        self.aggregated_params = aggregate(params_list)

        self.flower_client.set_parameters(self.aggregated_params)

        weights_dict = self.flower_client.get_dict_params({})
        weights_dict['len_dataset'] = 10

        model_type = "global_model"

        filename = f"models/{self.id}m{self.blockchain.len_chain}.npz"
        self.global_params_directory = filename

        with open(filename, "wb") as f:
            np.savez(f, **weights_dict)

        message = {
            "id": self.id,
            "type": "request", 
            "content": {
                "storage_reference": filename,
                "model_type": model_type,
                "calculated_hash": self.calculate_model_hash(filename)
            }
        }

        self.consensus_protocol.handle_message(message)

    def create_update_request(self, weights):

        self.flower_client.set_parameters(weights)

        weights_dict = self.flower_client.get_dict_params({})
        weights_dict['len_dataset'] = 10
        model_type = "update"

        filename = f"models/m{self.blockchain.len_chain}.npz"

        with open(filename, "wb") as f:
            np.savez(f, **weights_dict)

        message = {
            "id": self.id,
            "type": "request", 
            "content": {
                "storage_reference": filename,
                "model_type": model_type,
                "calculated_hash": self.calculate_model_hash(filename)
            }
        }

        # self.isModelUpdateUsefull(filename)

        return message

    def aggregation_cluster(self, pos): 
        weights = []
        for i in range(len(self.cluster_weights[pos])): 
            weights.append((self.cluster_weights[pos][i], 20))

        aggregated_weights = aggregate(weights)

        loss = self.flower_client.evaluate(aggregated_weights, {})[0]

        self.cluster_weights[pos] = []
        for k,v in self.clusters[pos].items(): 
            if k != "tot": 
                 self.clusters[pos][k] = 0

        return aggregated_weights

    def getKeys(self, private_key_path, public_key_path): 
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            with open(private_key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )

            with open(public_key_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
        else:
            # Generate new keys
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()

            # Save keys to files
            with open(private_key_path, 'wb') as f:
                f.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            with open(public_key_path, 'wb') as f:
                f.write(self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

    def sign_message(self, message):
        signature = self.private_key.sign(
            json.dumps(message).encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode()

    def verify_signature(self, signature, message, public_key):
        try:
            signature_binary = base64.b64decode(signature)

            public_key.verify(
                signature_binary,
                json.dumps(message).encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

    def add_peer(self, peer_id, peer_address):
        with open(f"keys/{peer_id}_public_key.pem", 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

        self.peers[peer_id] = {"address": peer_address, "public_key": public_key}

    def add_client(self, client_id, client_address):
        with open(f"keys/{client_id}_public_key.pem", 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

        self.clients[client_id] = {"address": client_address, "public_key": public_key}

    def create_cluster(self, clients): 
        self.clusters.append({client: 0 for client in clients})
        self.clusters[-1]["tot"] = len(self.clusters[-1])
        self.clusters[-1]["count"] = 0

        self.cluster_weights.append([])
