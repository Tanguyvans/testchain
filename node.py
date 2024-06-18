import socket
import threading
import json
import os
import base64
from math import floor, ceil
import random
import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

import hashlib
import numpy as np
from blockchain import Blockchain
from flowerclient import FlowerClient
import pickle

from flwr.server.strategy.aggregate import aggregate
from sklearn.model_selection import train_test_split

from protocols.pbft_protocol import PBFTProtocol
from protocols.raft_protocol import RaftProtocol
from going_modular.security import aggregate_shamir


# Other functions to handle the communication between the nodes
def get_keys(private_key_path, public_key_path):
    os.makedirs("keys/", exist_ok=True)
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        with open(private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )

        with open(public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

    else:
        # Generate new keys
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        # Save keys to files
        with open(private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(public_key_path, 'wb') as f:
            f.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            )

    return private_key, public_key


def start_server(host, port, handle_message, num_node):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Node {num_node} listening on {host}:{port}")

    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_message, args=(client_socket,)).start()


class Node:
    def __init__(self, id, host, port, consensus_protocol, batch_size, test, coef_usefull=1.01,
                 dp=False, ss_type="additif", m=3,
                 name_dataset="Airline Satisfaction", model_choice="simplenet", choice_loss="cross_entropy",
                 num_classes=10):
        self.id = id
        self.host = host
        self.port = port
        self.coef_usefull = coef_usefull

        self.peers = {}
        self.clients = {}
        self.clusters = []
        self.cluster_weights = []

        self.global_params_directory = ""
        self.nb_updates = 0

        private_key_path = f"keys/{id}_private_key.pem"
        public_key_path = f"keys/{id}_public_key.pem"
        self.get_keys(private_key_path, public_key_path)

        x_test, y_test = test
        #x_test, y_test = [], []  # test
        #[(x_test.append(test[i][0]), y_test.append(test[i][1])) for i in range(len(test))]
        # x_test, y_test, name_dataset="Airline Satisfaction", **kwargs
        self.flower_client = FlowerClient.node(
            x_test=x_test, 
            y_test=y_test,
            batch_size=batch_size,
            model_choice=model_choice,
            diff_privacy=dp,
            delta=1e-5,
            epsilon=0.5,
            max_grad_norm=1.2, 
            name_dataset=name_dataset,
            choice_loss=choice_loss,
            num_classes=num_classes
        )

        self.ss_type = ss_type
        self.secret_shape = None
        self.m = m

        self.blockchain = Blockchain()
        if consensus_protocol == "pbft":
            self.consensus_protocol = PBFTProtocol(node=self, blockchain=self.blockchain)

        elif consensus_protocol == "raft":
            self.consensus_protocol = RaftProtocol(node=self, blockchain=self.blockchain)
            threading.Thread(target=self.consensus_protocol.run).start()

    def start_server(self):
        start_server(self.host, self.port, self.handle_message, self.id)

    def handle_message(self, client_socket):
        # First, read the length of the data
        data_length_bytes = client_socket.recv(4)
        if not data_length_bytes:
            return  # No data received, possibly handle this case as an error or log it
        data_length = int.from_bytes(data_length_bytes, byteorder='big')

        # Now read exactly data_length bytes
        data = b''
        while len(data) < data_length:
            packet = client_socket.recv(data_length - len(data))
            if not packet:
                break  # Connection closed, handle this case if necessary
            data += packet

        if len(data) < data_length:
            # Log this situation as an error or handle it appropriately
            print("Data was truncated or connection was closed prematurely.")
            return

        message = pickle.loads(data)
        message_type = message.get("type")


        if message_type == "frag_weights":
            message_id = message.get("id")
            weights = pickle.loads(message.get("value"))
            self.secret_shape = message.get("list_shapes")

            for pos, cluster in enumerate(self.clusters):
                if message_id in cluster:
                    if cluster[message_id] == 0:
                        self.cluster_weights[pos].append(weights)

                        cluster[message_id] = 1
                        cluster["count"] += 1

                    if cluster["count"] == cluster["tot"]:
                        aggregated_weights = self.aggregation_cluster(pos)

                        participants = [k for k in cluster.keys() if k not in ["count", "tot"]]

                        message = self.create_update_request(aggregated_weights, participants)

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

                    print(f"updating GM {self.global_params_directory}")
                    self.broadcast_model_to_clients()

        client_socket.close()

    def is_update_usefull(self, model_directory, participants): 
        print(f"node: {self.id} cluster GM: {self.global_params_directory}, {model_directory} ")

        update_eval = self.evaluate_model(model_directory, participants)
        gm_eval = self.evaluate_model(self.global_params_directory, participants)

        print(f"{update_eval[0]}, {gm_eval[0]}")
        if update_eval[0] <= gm_eval[0]*self.coef_usefull:
            print(f"usefull {update_eval[0]}, {gm_eval[0]}")
            return True
        else: 
            print("not usefull")
            return False

    def get_weights(self, len_dataset=10):
        params_list = []
        for block in self.blockchain.blocks[::-1]:
            if block.model_type == "update":
                loaded_weights_dict = np.load(block.storage_reference)
                loaded_weights = [loaded_weights_dict[f'param_{i}'] for i in range(len(loaded_weights_dict) - 1)]

                loaded_weights = (loaded_weights, loaded_weights_dict[f'len_dataset'])
                params_list.append(loaded_weights)

            else:
                break

        if len(params_list) == 0:
            return None

        self.aggregated_params = aggregate(params_list)

        self.flower_client.set_parameters(self.aggregated_params)

        weights_dict = self.flower_client.get_dict_params({})
        weights_dict['len_dataset'] = len_dataset
        return weights_dict

    def is_global_valid(self, proposed_hash):
        weights_dict = self.get_weights(len_dataset=10)

        filename = f"models/{self.id}temp.npz"

        with open(filename, "wb") as f:
            np.savez(f, **weights_dict)

        if proposed_hash == self.calculate_model_hash(filename): 
            return True

        else:
            return False

    def evaluate_model(self, model_directory, participants):
        loaded_weights_dict = np.load(model_directory)
        loaded_weights = [loaded_weights_dict[f'param_{i}'] for i in range(len(loaded_weights_dict)-1)]
        loss = self.flower_client.evaluate(loaded_weights, {})[0]
        acc = self.flower_client.evaluate(loaded_weights, {})[2]['accuracy']

        with open('output.txt', 'a') as f:
            f.write(f"node: {self.id} model: {model_directory} cluster: {participants} loss: {loss} acc: {acc} \n")

        return loss, acc

    def broadcast_model_to_clients(self):
        for block in self.blockchain.blocks[::-1]: 
            if block.model_type == "global_model":
                block_model = block 
                break 

        loaded_weights_dict = np.load(block_model.storage_reference)
        loaded_weights = [loaded_weights_dict[f'param_{i}'] for i in range(len(loaded_weights_dict)-1)]

        for k, v in self.clients.items():
            address = v.get('address')

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(('127.0.0.1', address[1]))

            serialized_data = pickle.dumps(loaded_weights)
            message = {"type": "global_model", "value": serialized_data}

            serialized_message = pickle.dumps(message)

            # Send the length of the message first
            client_socket.send(len(serialized_message).to_bytes(4, byteorder='big'))
            client_socket.send(serialized_message)

            # Close the socket after sending
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

                    # Send the length of the message first
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

        weights_dict = self.flower_client.get_dict_params({})
        weights_dict['len_dataset'] = 0
        model_type = "first_global_model"
        
        filename = f"models/m0.npz"
        self.global_params_directory = filename
        os.makedirs("models/", exist_ok=True)
        with open(filename, "wb") as f:
            np.savez(f, **weights_dict)

        message = {
            "id": self.id,
            "type": "request", 
            "content": {
                "storage_reference": filename,
                "model_type": model_type,
                "calculated_hash": self.calculate_model_hash(filename),
                "participants": ["1", "2"]
            }
        }

        time.sleep(10)

        self.consensus_protocol.handle_message(message)

    def create_global_model(self): 
        weights_dict = self.get_weights(len_dataset=10)

        if weights_dict is None:
            print("No weights to save")
            return

        model_type = "global_model"

        filename = f"models/{self.id}m{self.blockchain.len_chain}.npz"
        #self.global_params_directory = filename

        with open(filename, "wb") as f:
            np.savez(f, **weights_dict)

        message = {
            "id": self.id,
            "type": "request", 
            "content": {
                "storage_reference": filename,
                "model_type": model_type,
                "calculated_hash": self.calculate_model_hash(filename), 
                "participants": ["1", "2"]
            }
        }

        self.consensus_protocol.handle_message(message)

    def create_update_request(self, weights, participants):

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
                "calculated_hash": self.calculate_model_hash(filename),
                "participants": participants
            }
        }

        # self.isModelUpdateUsefull(filename)

        return message

    def aggregation_cluster(self, pos):
        if self.ss_type == "additif":
            aggregated_weights = aggregate(
                [(self.cluster_weights[pos][i], 20) for i in range(len(self.cluster_weights[pos]))]
            )
        else:
            # shamir secret sharing
            aggregated_weights = aggregate_shamir(self.cluster_weights[pos], self.secret_shape, self.m)

        loss = self.flower_client.evaluate(aggregated_weights, {})[0]

        with open('output.txt', 'a') as f: 
            f.write(f"cluster {pos} node {self.id} block {self.blockchain.len_chain} loss: {loss} \n")

        self.cluster_weights[pos] = []
        for k, v in self.clusters[pos].items():
            if k != "tot":
                self.clusters[pos][k] = 0

        return aggregated_weights

    def get_keys(self, private_key_path, public_key_path):
        self.private_key, self.public_key = get_keys(private_key_path, public_key_path)

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

    def generate_clusters(self, min_number_of_clients): 
        self.clusters = []
        clients = [k for k in self.clients.keys()]
        random.shuffle(clients)

        number_of_clusters = floor(len(self.clients)/min_number_of_clients)
        max_number_of_clients = ceil(len(self.clients)/number_of_clusters)

        sol = [0]
        n = len(self.clients)
        for i in range(number_of_clusters): 
            if n % min_number_of_clients == 0: 
                sol.append(sol[-1] + min_number_of_clients)
                n -= min_number_of_clients
            else: 
                sol.append(sol[-1] + max_number_of_clients)
                n -= max_number_of_clients

        for i in range(1, len(sol)): 
            self.create_cluster(clients[sol[i-1]: sol[i]])

        print(self.clusters)

    def create_cluster(self, clients): 
        self.clusters.append({client: 0 for client in clients})
        self.clusters[-1]["tot"] = len(self.clusters[-1])
        self.clusters[-1]["count"] = 0

        self.cluster_weights.append([])
